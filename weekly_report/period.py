"""주 단위 기간 계산. 월요일 시작, 일요일 끝(ISO 기준)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

_ISO_WEEK = re.compile(r"^(\d{4})-?[Ww](\d{1,2})$")


def week_bounds(day: date) -> tuple[date, date]:
    monday = day - timedelta(days=day.weekday())
    return monday, monday + timedelta(days=6)


def resolve(spec: str | None, today: date | None = None) -> tuple[date, date]:
    """'this' | 'last' | '2026-W33' | '2026-08-12' → (시작일, 종료일)."""
    today = today or date.today()
    spec = (spec or "this").strip().lower()

    if spec in ("this", "current", "이번주", "금주"):
        return week_bounds(today)
    if spec in ("last", "prev", "previous", "지난주", "전주"):
        return week_bounds(today - timedelta(days=7))

    match = _ISO_WEEK.match(spec)
    if match:
        year, week = int(match.group(1)), int(match.group(2))
        monday = date.fromisocalendar(year, week, 1)
        return monday, monday + timedelta(days=6)

    try:
        return week_bounds(datetime.strptime(spec, "%Y-%m-%d").date())
    except ValueError as exc:
        raise ValueError(
            f"기간을 이해하지 못했습니다: {spec!r} "
            "(사용 가능: this, last, 2026-W33, 2026-08-12)"
        ) from exc


def label(start: date, end: date) -> str:
    year, week, _ = start.isocalendar()
    return f"{year}-W{week:02d} ({start.isoformat()} ~ {end.isoformat()})"


def slug(start: date) -> str:
    year, week, _ = start.isocalendar()
    return f"{year}-W{week:02d}"


def parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                    "%m/%d/%Y %I:%M %p", "%Y/%m/%d %H:%M"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return parsed.replace(tzinfo=None)


def day_name(value: datetime | None) -> str:
    return WEEKDAY_KO[value.weekday()] if value else ""


def hm(seconds: float) -> str:
    """9000 → '2시간 30분'"""
    total = int(round(seconds / 60.0))
    hours, minutes = divmod(total, 60)
    if hours and minutes:
        return f"{hours}시간 {minutes}분"
    if hours:
        return f"{hours}시간"
    return f"{minutes}분"


def hours(seconds: float) -> float:
    return round(seconds / 3600.0, 1)
