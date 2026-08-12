"""사내 LLM 호출.

표준 라이브러리(urllib)만 사용한다. 사내 주소는 보통 프록시를 타면 안 되므로
bypass_proxy 가 켜져 있으면 프록시를 쓰지 않는 opener 로 요청한다.

  api_style: openai  →  POST {base_url}/chat/completions  (대부분의 사내 포털이 이 형식)
  api_style: custom  →  config 의 request_template / response_path 를 그대로 사용
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any

SYSTEM_PROMPT = """당신은 한국 기업의 실무자가 쓰는 주간업무보고 초안을 다듬는 도우미입니다.

지켜야 할 규칙:
1. 입력으로 주어진 활동 기록에 없는 내용은 절대 지어내지 마십시오. 근거가 부족하면
   해당 항목 옆에 "(확인 필요)"라고 표시하십시오.
2. 시간은 입력에 있는 숫자를 그대로 쓰십시오. 임의로 반올림하거나 늘리지 마십시오.
3. "판정" 필드를 존중하십시오. '검토·열람'은 문서를 열어본 것이지 작성한 것이 아닙니다.
   '작성·수정'과 '커밋'만 실적으로 단정해서 쓰십시오.
4. 회사 보고서 문체로 쓰십시오. 간결한 개조식('~함', '~완료', '~진행 중')을 사용하고,
   과장이나 수식어를 넣지 마십시오.
5. '차주 계획'은 기록으로 알 수 없으므로, 미완료로 보이는 항목만 후보로 제시하고
   확정적으로 쓰지 마십시오.
6. 출력은 주어진 형식의 마크다운만 내보내고, 설명이나 인사말을 덧붙이지 마십시오.
"""


def _build_prompt(payload: dict, template: str, extra: str) -> str:
    parts = [
        "다음은 한 주 동안 자동 수집된 업무 활동 기록입니다.",
        "",
        "```json",
        json.dumps(payload, ensure_ascii=False, indent=2),
        "```",
        "",
        "위 기록을 바탕으로 아래 형식의 주간업무보고 초안을 작성하십시오.",
        "",
        "```markdown",
        template.strip(),
        "```",
    ]
    if extra.strip():
        parts += ["", "추가 지시사항:", extra.strip()]
    return "\n".join(parts)


def _opener(cfg: dict):
    handlers: list[Any] = []
    if cfg.get("bypass_proxy", True):
        handlers.append(urllib.request.ProxyHandler({}))
    if not cfg.get("verify_ssl", True):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        handlers.append(urllib.request.HTTPSHandler(context=context))
    return urllib.request.build_opener(*handlers)


def _dig(data: Any, path: str) -> Any:
    """'choices.0.message.content' 같은 경로로 응답에서 값을 꺼낸다."""
    current = data
    for token in path.split("."):
        if current is None:
            return None
        if token.isdigit() and isinstance(current, list):
            index = int(token)
            current = current[index] if index < len(current) else None
        elif isinstance(current, dict):
            current = current.get(token)
        else:
            return None
    return current


def _fill(template: Any, prompt: str, system: str) -> Any:
    if isinstance(template, str):
        return template.replace("{{PROMPT}}", prompt).replace("{{SYSTEM}}", system)
    if isinstance(template, list):
        return [_fill(item, prompt, system) for item in template]
    if isinstance(template, dict):
        return {key: _fill(value, prompt, system) for key, value in template.items()}
    return template


def build_request(cfg: dict, prompt: str) -> tuple[str, dict, dict]:
    base = str(cfg.get("base_url", "")).rstrip("/")
    if not base:
        raise RuntimeError("llm.base_url 이 설정되지 않았습니다.")

    headers = {"Content-Type": "application/json"}
    headers.update(cfg.get("headers") or {})
    key_env = cfg.get("api_key_env") or ""
    if key_env:
        key = os.environ.get(key_env, "")
        if not key:
            raise RuntimeError(f"환경변수 {key_env} 에 API 키가 없습니다.")
        headers.setdefault("Authorization", f"Bearer {key}")

    if cfg.get("api_style", "openai") == "custom":
        template = cfg.get("request_template") or {}
        if not template:
            raise RuntimeError("api_style 이 custom 이면 llm.request_template 이 필요합니다.")
        return base, headers, _fill(template, prompt, SYSTEM_PROMPT)

    url = base if base.endswith("/chat/completions") else base + "/chat/completions"
    body = {
        "model": cfg.get("model", ""),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": int(cfg.get("max_tokens", 4000)),
        "stream": False,
    }
    return url, headers, body


def call(cfg: dict, prompt: str) -> str:
    url, headers, body = build_request(cfg, prompt)
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    timeout = int(cfg.get("timeout_seconds", 120))
    try:
        with _opener(cfg).open(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"연결 실패: {exc.reason}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw

    path = cfg.get("response_path") or "choices.0.message.content"
    value = _dig(data, path)
    if value is None:
        raise RuntimeError(
            f"응답에서 '{path}' 를 찾지 못했습니다. 응답 앞부분: {raw[:300]}"
        )
    return str(value)


def summarize(cfg: dict, payload: dict, template: str, extra: str = "") -> str:
    return call(cfg, _build_prompt(payload, template, extra))


def check(cfg: dict) -> str:
    """연결 확인용. 짧은 프롬프트를 보내 응답 형식을 확인한다."""
    return call(cfg, "연결 확인용 요청입니다. '정상'이라고만 답하십시오.")
