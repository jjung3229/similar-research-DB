"""집계 결과 → 검수 가능한 근거 묶음(evidence pack).

여기가 외부(사내 LLM)로 나가는 데이터의 마지막 관문이다. 네트워크로 나가는 내용은
반드시 이 모듈을 거치고, --dry-run 으로 파일에 떨궈 눈으로 확인할 수 있다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .redact import Redactor

MAX_ITEMS_PER_PROJECT = 12
MAX_EVIDENCE_PER_ITEM = 4


def sanitize(value: Any, redactor: Redactor) -> Any:
    """모든 문자열을 마스킹하고, 대외비 키워드가 걸린 덩어리는 통째로 버린다."""
    if isinstance(value, str):
        return redactor.text(value)
    if isinstance(value, list):
        cleaned = []
        for entry in value:
            if isinstance(entry, dict) and redactor.should_drop(*_leaf_strings(entry)):
                continue
            cleaned.append(sanitize(entry, redactor))
        return cleaned
    if isinstance(value, dict):
        return {key: sanitize(item, redactor) for key, item in value.items()}
    return value


def _leaf_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _leaf_strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in _leaf_strings(item)]
    return []


def build_pack(aggregate: dict, redactor: Redactor) -> dict[str, Any]:
    return sanitize(aggregate, redactor)


def to_prompt_payload(pack: dict) -> dict[str, Any]:
    """LLM 입력용으로 줄인 형태. 근거는 항목당 몇 개만 남긴다."""
    projects = []
    for entry in pack.get("projects", []):
        items = []
        for item in entry.get("items", [])[:MAX_ITEMS_PER_PROJECT]:
            items.append(
                {
                    "활동": item["label"],
                    "구분": item["kind"],
                    "판정": item["status"],
                    "시간": item.get("hours", 0),
                    "요일": item.get("days", []),
                    "근거": [
                        f"[{e['type']}] {e['text']}"
                        for e in item.get("evidence", [])[:MAX_EVIDENCE_PER_ITEM]
                    ],
                }
            )
        projects.append(
            {"과제": entry["name"], "총시간": entry.get("hours", 0), "활동목록": items}
        )

    return {
        "기간": pack["period"]["label"],
        "작성자": pack.get("user", {}).get("name", ""),
        "합계": pack.get("totals", {}),
        "과제별_활동": projects,
        "신규_과제_후보": pack.get("new_project_candidates", []),
        "수집된_소스": pack.get("coverage", {}),
    }


def save(pack: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
