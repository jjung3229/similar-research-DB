from __future__ import annotations

import datetime as _dt

from ..config import Settings
from ..models import Transcript
from . import llm, rules
from .schema import ActionItem, Minutes, Topic  # noqa: F401

BACKENDS = ("auto", "llm", "rules", "none")


def build(settings: Settings, tr: Transcript, *, title: str = "회의록",
          date: str = "", progress=None) -> Minutes | None:
    """설정된 백엔드로 회의록을 생성한다.

    auto : LLM 서버가 응답하면 LLM, 아니면 규칙 기반으로 자동 강등.
    """
    backend = (settings.minutes_backend or "auto").lower()
    if backend == "none":
        return None

    date = date or _dt.date.today().isoformat()

    def _rules() -> Minutes:
        if progress:
            progress(0.5, "규칙 기반 회의록 작성 중")
        return rules.build(tr, title=title, date=date)

    if backend == "rules":
        return _rules()

    if not settings.llm_base_url or not settings.llm_model:
        if backend == "llm":
            raise llm.LLMError(
                "LLM 백엔드를 쓰려면 VB_LLM_BASE_URL 과 VB_LLM_MODEL 을 설정해야 합니다.\n"
                "  예) VB_LLM_BASE_URL=http://localhost:11434/v1  VB_LLM_MODEL=qwen3:14b"
            )
        m = _rules()
        m.warnings.append("LLM 엔드포인트가 설정되지 않아 규칙 기반으로 작성했습니다.")
        return m

    try:
        return llm.build(
            tr,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout,
            chunk_chars=settings.llm_chunk_chars,
            title=title,
            date=date,
            progress=progress,
        )
    except llm.LLMError:
        if backend == "llm":
            raise
        m = _rules()
        m.warnings.append("LLM 호출에 실패해 규칙 기반으로 대체했습니다.")
        return m
