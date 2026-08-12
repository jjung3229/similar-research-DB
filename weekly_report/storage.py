"""수집 데이터 저장소. 날짜별 JSONL 파일로 append 한다.

  <data_dir>/activity/2026-08-10.jsonl
  <data_dir>/mail/2026-08-10.jsonl
  ...

텍스트 한 줄 = 기록 하나라서 메모장으로 열어 직접 지울 수 있다.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Iterator


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _file(self, kind: str, day: date) -> Path:
        d = self.root / kind
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{day.isoformat()}.jsonl"

    def append(self, kind: str, record: dict[str, Any], day: date | None = None) -> None:
        day = day or _record_day(record) or date.today()
        with self._file(kind, day).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def extend(self, kind: str, records: Iterable[dict[str, Any]]) -> int:
        count = 0
        for record in records:
            self.append(kind, record)
            count += 1
        return count

    def replace_range(self, kind: str, start: date, end: date, records: Iterable[dict]) -> int:
        """해당 기간 파일을 지우고 새로 쓴다 (메일·커밋처럼 재수집 가능한 종류용)."""
        for day in _days(start, end):
            path = self._file(kind, day)
            if path.exists():
                path.unlink()
        return self.extend(kind, records)

    def read_range(self, kind: str, start: date, end: date) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for day in _days(start, end):
            path = self._file(kind, day)
            if not path.exists():
                continue
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return out


def _days(start: date, end: date) -> Iterator[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _record_day(record: dict) -> date | None:
    for key in ("start", "ts", "date", "time"):
        value = record.get(key)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                continue
    return None
