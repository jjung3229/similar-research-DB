"""민감정보 마스킹.

수집 단계와 보고서 생성 직전 두 번 적용된다. 외부(Claude API)로 나가는 텍스트는
반드시 이 모듈을 거친다.
"""

from __future__ import annotations

import re
from typing import Any

# (정규식, 치환문자열)
BUILTIN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b"), "[주민번호]"),
    (re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"), "[카드번호]"),
    (re.compile(r"\b01[016-9][-\s]?\d{3,4}[-\s]?\d{4}\b"), "[휴대전화]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[이메일]"),
    (re.compile(r"\b(?:sk-ant-|sk-|ghp_|github_pat_|AKIA)[A-Za-z0-9_\-]{12,}\b"), "[비밀키]"),
    (
        re.compile(r"(?i)\b(password|passwd|비밀번호|암호)\s*[:=]\s*\S+"),
        r"\1: [삭제됨]",
    ),
]


class Redactor:
    def __init__(self, cfg: dict[str, Any] | None = None):
        cfg = cfg or {}
        self.enabled = cfg.get("enabled", True)
        self.drop_keywords = [k.lower() for k in cfg.get("drop_keywords", []) if k]
        self.patterns = list(BUILTIN_PATTERNS)
        for raw in cfg.get("extra_patterns", []) or []:
            if isinstance(raw, str):
                self.patterns.append((re.compile(raw), "[삭제됨]"))
            elif isinstance(raw, dict) and raw.get("pattern"):
                self.patterns.append(
                    (re.compile(raw["pattern"]), raw.get("replace", "[삭제됨]"))
                )

    def text(self, value: str) -> str:
        if not self.enabled or not value:
            return value
        out = value
        for pattern, replace in self.patterns:
            out = pattern.sub(replace, out)
        return out

    def should_drop(self, *values: Any) -> bool:
        """대외비 키워드가 들어간 기록인지 판단."""
        if not self.drop_keywords:
            return False
        blob = " ".join(str(v) for v in values if v).lower()
        return any(keyword in blob for keyword in self.drop_keywords)

    def record(self, record: dict[str, Any]) -> dict[str, Any] | None:
        """기록 전체를 마스킹. 버려야 하면 None 을 반환한다."""
        if self.should_drop(*record.values()):
            return None
        return {k: (self.text(v) if isinstance(v, str) else v) for k, v in record.items()}

    def records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for record in records:
            cleaned = self.record(record)
            if cleaned is not None:
                out.append(cleaned)
        return out
