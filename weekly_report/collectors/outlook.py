"""Outlook 메일·일정 수집기 (Windows 전용).

이미 로그인되어 있는 내 Outlook 을 COM(MAPI)으로 읽는다. 계정 정보를 따로 넣지 않고,
서버에 직접 접속하지도 않는다.

사내 보안정책(GPO/백신)이 '프로그래밍 방식 액세스'를 막으면 실패할 수 있다. 그때는
메일 수집만 건너뛰고 나머지 수집은 정상 진행되며, 수동으로 내보낸 CSV 를
import_mail_csv() 로 넣을 수 있다.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from typing import Any, Iterator

OL_FOLDER_INBOX = 6
OL_FOLDER_SENT = 5
OL_FOLDER_CALENDAR = 9


class OutlookUnavailable(RuntimeError):
    pass


def _connect():
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise OutlookUnavailable(
            "pywin32 가 없어 Outlook 수집을 건너뜁니다. (pip install pywin32)"
        ) from exc
    try:
        return win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    except Exception as exc:  # pragma: no cover - 환경 의존
        raise OutlookUnavailable(
            f"Outlook 에 접근하지 못했습니다 ({exc}). 사내 보안정책으로 막혀 있을 수 있습니다."
        ) from exc


def _restrict_range(field: str, start: date, end: date) -> str:
    """Outlook Restrict 문자열. 미국식 날짜 형식을 요구한다."""
    begin = datetime.combine(start, dtime.min).strftime("%m/%d/%Y %I:%M %p")
    finish = datetime.combine(end + timedelta(days=1), dtime.min).strftime("%m/%d/%Y %I:%M %p")
    return f"[{field}] >= '{begin}' AND [{field}] < '{finish}'"


def _as_iso(value: Any) -> str:
    try:
        return datetime.fromtimestamp(value.timestamp()).isoformat(timespec="seconds")
    except Exception:
        try:
            return str(value)
        except Exception:
            return ""


def _clean_body(text: Any, limit: int) -> str:
    if not text:
        return ""
    body = " ".join(str(text).split())
    return body[:limit]


def _domain(address: str) -> str:
    return address.rsplit("@", 1)[-1].strip().lower() if "@" in str(address) else ""


def collect(cfg: dict, start: date, end: date) -> Iterator[dict[str, Any]]:
    """기간 내 보낸메일·받은메일·회의를 기록으로 만들어 내보낸다."""
    ocfg = cfg["outlook"]
    if not ocfg.get("enabled", True):
        return
    limit = int(ocfg.get("max_body_chars", 700))
    namespace = _connect()

    if ocfg.get("include_sent", True):
        yield from _mail_items(
            namespace, OL_FOLDER_SENT, "sent", "SentOn", start, end, limit, cfg
        )
    if ocfg.get("include_received", True):
        yield from _mail_items(
            namespace, OL_FOLDER_INBOX, "received", "ReceivedTime", start, end, limit, cfg
        )
    if ocfg.get("include_calendar", True):
        yield from _calendar_items(namespace, start, end)


def _mail_items(namespace, folder_id, direction, date_field, start, end, limit, cfg):
    domains = [d.lower() for d in cfg["outlook"].get("received_from_domains", []) if d]
    try:
        items = namespace.GetDefaultFolder(folder_id).Items
        items.Sort(f"[{date_field}]", True)
        items = items.Restrict(_restrict_range(date_field, start, end))
    except Exception as exc:  # pragma: no cover - 환경 의존
        raise OutlookUnavailable(f"{direction} 폴더를 읽지 못했습니다: {exc}") from exc

    for item in items:
        try:
            if getattr(item, "Class", 43) != 43:      # 43 = MailItem
                continue
            sender = str(getattr(item, "SenderEmailAddress", "") or "")
            if direction == "received" and domains and _domain(sender) not in domains:
                continue
            yield {
                "kind": "mail",
                "direction": direction,
                "time": _as_iso(getattr(item, date_field)),
                "subject": str(getattr(item, "Subject", "") or ""),
                "counterpart": str(getattr(item, "To", "") or "")
                if direction == "sent"
                else str(getattr(item, "SenderName", "") or ""),
                "counterpart_domain": _domain(sender),
                "conversation": str(getattr(item, "ConversationTopic", "") or ""),
                "categories": str(getattr(item, "Categories", "") or ""),
                "snippet": _clean_body(getattr(item, "Body", ""), limit),
            }
        except Exception:
            continue          # 손상된 항목 하나 때문에 전체가 멈추지 않게


def _calendar_items(namespace, start: date, end: date):
    try:
        items = namespace.GetDefaultFolder(OL_FOLDER_CALENDAR).Items
        items.IncludeRecurrences = True         # 반복 회의도 개별 발생으로 펼친다
        items.Sort("[Start]")
        items = items.Restrict(_restrict_range("Start", start, end))
    except Exception as exc:  # pragma: no cover - 환경 의존
        raise OutlookUnavailable(f"일정을 읽지 못했습니다: {exc}") from exc

    for item in items:
        try:
            duration = int(getattr(item, "Duration", 0) or 0)     # 분 단위
            yield {
                "kind": "meeting",
                "time": _as_iso(getattr(item, "Start")),
                "end": _as_iso(getattr(item, "End")),
                "seconds": duration * 60,
                "subject": str(getattr(item, "Subject", "") or ""),
                "organizer": str(getattr(item, "Organizer", "") or ""),
                "location": str(getattr(item, "Location", "") or ""),
                "required": str(getattr(item, "RequiredAttendees", "") or "")[:300],
            }
        except Exception:
            continue


def import_mail_csv(path: str | Path) -> Iterator[dict[str, Any]]:
    """Outlook 에서 수동으로 내보낸 CSV 를 읽는다 (COM 이 막혔을 때의 대안).

    Outlook: 파일 > 열기/내보내기 > 가져오기/내보내기 > 파일로 내보내기 > CSV
    제목/보낸 날짜 열만 있으면 동작한다.
    """
    subject_keys = ("Subject", "제목")
    date_keys = ("Sent", "Date", "보낸 날짜", "받은 시간", "날짜")
    to_keys = ("To", "받는 사람", "보낸 사람", "From")

    with Path(path).expanduser().open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            def pick(keys):
                for key in keys:
                    if row.get(key):
                        return str(row[key]).strip()
                return ""

            subject = pick(subject_keys)
            if not subject:
                continue
            yield {
                "kind": "mail",
                "direction": "sent",
                "time": pick(date_keys),
                "subject": subject,
                "counterpart": pick(to_keys),
                "counterpart_domain": "",
                "conversation": subject,
                "categories": "",
                "snippet": "",
                "source": "csv",
            }
