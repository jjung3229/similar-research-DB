"""OpenAI 호환 엔드포인트로 회의록을 만든다.

외부 SaaS 를 부르라는 뜻이 아니다. base_url 로 아래 중 하나를 가리키면 된다.
  - 내 PC 의 Ollama          : http://localhost:11434/v1
  - 사내 GPU 서버의 vLLM     : http://10.x.x.x:8000/v1
  - 사내에서 이미 승인된 게이트웨이
표준 라이브러리(urllib)만 쓰므로 openai 패키지 설치가 필요 없다.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from ..models import Transcript
from ..text.postprocess import chunk_for_llm, fmt_clock
from .schema import ActionItem, Minutes, Topic

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)

CHUNK_SYSTEM = (
    "너는 한국 기업의 회의록 작성 담당자다. 주어진 녹취 일부를 읽고 사실만 추출한다. "
    "녹취에 없는 내용을 지어내지 않는다. 확실하지 않으면 비워 둔다. "
    "반드시 JSON 객체 하나만 출력한다."
)

CHUNK_TEMPLATE = """다음은 회의 녹취의 {idx}/{total} 번째 구간이다.

<녹취>
{body}
</녹취>

아래 JSON 스키마로만 답하라. 설명 문장을 덧붙이지 마라.
{{
  "topics":   [{{"title": "안건명(10자 내외)", "points": ["논의된 사실 1문장", "..."]}}],
  "decisions": ["확정된 결정사항 1문장", "..."],
  "actions":  [{{"task": "해야 할 일", "owner": "담당자(모르면 미정)", "due": "기한(모르면 미정)"}}],
  "open_issues": ["결론 안 난 사항", "..."]
}}

규칙:
- 결정사항은 실제로 '하기로 함/확정/승인' 된 것만. 단순 제안·의견은 제외.
- 액션 아이템은 누가 무엇을 하는지가 드러나는 것만.
- 담당자는 녹취에 나온 이름/직함 그대로. 추측 금지.
- 해당 항목이 없으면 빈 배열."""

MERGE_SYSTEM = (
    "너는 회의록 편집자다. 구간별로 추출된 항목들을 하나의 회의록으로 합친다. "
    "중복은 합치고, 서로 모순되면 뒤에 나온 것을 우선한다. "
    "새로운 사실을 추가하지 않는다. JSON 객체 하나만 출력한다."
)

MERGE_TEMPLATE = """회의 전체 길이: {duration}
참석(화자): {attendees}

구간별 추출 결과(JSON 배열):
{parts}

아래 스키마의 JSON 하나로 통합하라.
{{
  "summary": "회의 전체를 3문장 이내로 요약",
  "topics":   [{{"title": "안건명", "points": ["...", "..."]}}],
  "decisions": ["...", "..."],
  "actions":  [{{"task": "...", "owner": "...", "due": "..."}}],
  "open_issues": ["...", "..."]
}}

규칙:
- 안건은 중요도 순으로 최대 7개.
- 같은 액션 아이템이 여러 구간에 나오면 하나로 합치고 가장 구체적인 담당/기한을 쓴다.
- 빈 항목은 빈 배열."""


class LLMError(RuntimeError):
    pass


def chat(base_url: str, model: str, messages: list[dict], *, api_key: str = "",
         timeout: int = 300, temperature: float = 0.2,
         max_tokens: int = 4096) -> str:
    """OpenAI 호환 /chat/completions 호출."""
    url = base_url.rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        # 로컬/사내 엔드포인트이므로 시스템 프록시를 타지 않도록 한다.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise LLMError(f"LLM 서버 오류 {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(
            f"LLM 서버에 연결하지 못했습니다: {url}\n  ({exc.reason})\n"
            "Ollama 라면 `ollama serve` 가 떠 있는지, 모델이 받아져 있는지 확인하세요."
        ) from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError(f"예상과 다른 응답 형식: {str(data)[:300]}") from exc


def parse_json_object(raw: str) -> dict[str, Any]:
    """코드펜스·앞뒤 잡담을 걷어내고 JSON 객체를 꺼낸다."""
    text = _FENCE.sub("", raw).strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start == -1:
        return {}
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(text[start : i + 1])
                    return obj if isinstance(obj, dict) else {}
                except json.JSONDecodeError:
                    return {}
    return {}


def _as_list(obj: dict, key: str) -> list:
    v = obj.get(key)
    return v if isinstance(v, list) else []


def build(tr: Transcript, *, base_url: str, model: str, api_key: str = "",
          timeout: int = 300, chunk_chars: int = 6000,
          title: str = "회의록", date: str = "",
          progress=None) -> Minutes:
    chunks = chunk_for_llm(tr, max_chars=chunk_chars)
    if not chunks:
        raise LLMError("전사 결과가 비어 있어 회의록을 만들 수 없습니다.")

    partials: list[dict] = []
    for i, body in enumerate(chunks, start=1):
        if progress:
            progress(i / (len(chunks) + 1), f"회의록 초안 {i}/{len(chunks)}")
        raw = chat(
            base_url, model,
            [
                {"role": "system", "content": CHUNK_SYSTEM},
                {"role": "user", "content": CHUNK_TEMPLATE.format(
                    idx=i, total=len(chunks), body=body)},
            ],
            api_key=api_key, timeout=timeout,
        )
        partials.append(parse_json_object(raw))

    if len(partials) == 1:
        merged = dict(partials[0])
        merged.setdefault("summary", "")
        if not merged.get("summary"):
            # 구간이 하나뿐이면 요약만 따로 한 번 더 받는다.
            merged["summary"] = chat(
                base_url, model,
                [
                    {"role": "system", "content": "회의 요약가. 3문장 이내 한국어 평문으로만 답한다."},
                    {"role": "user", "content": f"다음 회의를 3문장 이내로 요약하라.\n\n{chunks[0]}"},
                ],
                api_key=api_key, timeout=timeout, max_tokens=512,
            ).strip()
    else:
        if progress:
            progress(0.95, "구간 통합 중")
        raw = chat(
            base_url, model,
            [
                {"role": "system", "content": MERGE_SYSTEM},
                {"role": "user", "content": MERGE_TEMPLATE.format(
                    duration=fmt_clock(tr.duration),
                    attendees=", ".join(tr.speakers) or "미상",
                    parts=json.dumps(partials, ensure_ascii=False),
                )},
            ],
            api_key=api_key, timeout=timeout, max_tokens=6144,
        )
        merged = parse_json_object(raw)
        if not merged:
            raise LLMError("통합 단계 응답을 JSON 으로 해석하지 못했습니다.")

    return Minutes(
        title=title,
        date=date,
        duration=tr.duration,
        attendees=tr.speakers,
        summary=str(merged.get("summary") or "").strip(),
        topics=[Topic.from_dict(t) for t in _as_list(merged, "topics") if isinstance(t, dict)],
        decisions=[str(d).strip() for d in _as_list(merged, "decisions") if str(d).strip()],
        actions=[ActionItem.from_dict(a) for a in _as_list(merged, "actions") if isinstance(a, dict)],
        open_issues=[str(x).strip() for x in _as_list(merged, "open_issues") if str(x).strip()],
        backend=f"llm:{model}",
        warnings=["LLM 자동 생성 초안입니다. 결정사항과 담당/기한은 반드시 사람이 확인하세요."],
    )


def health(base_url: str, timeout: int = 5) -> tuple[bool, str]:
    """서버가 살아 있는지 가볍게 확인."""
    url = base_url.rstrip("/")
    url = url[: -len("/chat/completions")] if url.endswith("/chat/completions") else url
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"{url}/models", timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        names = [m.get("id", "?") for m in data.get("data", [])][:20]
        return True, ", ".join(names) or "(모델 목록 비어 있음)"
    except Exception as exc:  # noqa: BLE001 - 진단용이라 원인 문자열이면 충분
        return False, str(exc)
