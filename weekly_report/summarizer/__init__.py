"""요약기. 사내 LLM 이 설정돼 있으면 그쪽을, 아니면 규칙 기반을 쓴다.

LLM 이 꺼져 있거나 호출이 실패해도 보고서 생성이 멈추지 않는다. 이 경우 규칙 기반
초안으로 대체하고 그 사실을 화면에 알린다.
"""

from __future__ import annotations

import sys
from typing import Any

from . import inhouse_llm, rule_based


def summarize(cfg: dict, pack: dict, payload: dict, template: str) -> tuple[str, str]:
    """(마크다운, 생성방식) 을 돌려준다."""
    llm_cfg = cfg.get("llm", {})
    if not llm_cfg.get("enabled"):
        return rule_based.render(pack), "규칙 기반"

    try:
        text = inhouse_llm.summarize(llm_cfg, payload, template,
                                     cfg["report"].get("extra_instructions", ""))
        if text.strip():
            return text, f"사내 LLM ({llm_cfg.get('model') or llm_cfg.get('base_url')})"
        raise RuntimeError("응답이 비어 있습니다")
    except Exception as exc:
        print(f"[!] 사내 LLM 호출 실패 → 규칙 기반 초안으로 대체합니다: {exc}",
              file=sys.stderr)
        return rule_based.render(pack), "규칙 기반 (LLM 실패)"
