"""수집 기록 → 과제별 활동 항목으로 집계한다.

이 모듈이 도구의 핵심이다. 창 제목만으로는 "열어놨다"와 "작업했다"를 구분할 수 없기
때문에, 아래처럼 신호를 교차시켜 판정한다.

    창 제목의 파일명 == 그 주 수정된 파일 && 수정시각이 세션 안  → 작성·수정 (확정)
    창 세션만 있고 파일 수정 없음                                → 검토·열람 (추정)
    회의 일정                                                    → 회의 참석
    보낸 메일                                                    → 보고·발송
    git 커밋                                                     → 개발 (가장 신뢰도 높음)
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from . import period

# 창 제목에서 파일명을 뽑아낸다. "AXDX_로드맵_v3.pptx - PowerPoint" → AXDX_로드맵_v3.pptx
FILENAME_RE = re.compile(
    r"[^\\/:*?\"<>|\r\n]+?\.(?:pptx?|docx?|xlsx?|hwpx?|pdf|py|md|ipynb|sql|csv|txt)\b",
    re.IGNORECASE,
)

APP_KIND = {
    "powerpnt": "문서", "winword": "문서", "excel": "문서", "hwp": "문서",
    "hword": "문서", "acrord32": "문서", "acrobat": "문서",
    "outlook": "메일",
    "code": "개발", "devenv": "개발", "pycharm64": "개발", "idea64": "개발",
    "python": "개발", "windowsterminal": "개발", "cmd": "개발", "powershell": "개발",
    "teams": "회의", "zoom": "회의", "webex": "회의", "ms-teams": "회의",
    "chrome": "웹", "msedge": "웹", "firefox": "웹", "iexplore": "웹", "whale": "웹",
    "explorer": "탐색",
}

# 창 세션을 이어붙일 때 허용하는 공백 (잠깐 다른 창을 봤다가 돌아온 경우)
MERGE_GAP_SECONDS = 300
# 파일 수정시각이 세션 근처에 있으면 그 세션의 산출물로 본다
FILE_MATCH_BEFORE = timedelta(minutes=5)
FILE_MATCH_AFTER = timedelta(minutes=30)


# --------------------------------------------------------------------------
# 창 제목 해석
# --------------------------------------------------------------------------
def parse_title(app: str, title: str) -> dict[str, str]:
    app_key = (app or "").lower()
    kind = APP_KIND.get(app_key, "기타")

    filename = ""
    match = FILENAME_RE.search(title or "")
    if match:
        filename = match.group(0).strip()

    if filename:
        label = filename
        if kind in ("기타", "웹", "탐색"):
            kind = "개발" if filename.lower().endswith((".py", ".ipynb", ".sql", ".md")) else "문서"
    else:
        # "제목 - 프로그램" 형태에서 앞부분이 내용이다
        head = (title or "").split(" - ")[0].strip()
        label = head or (title or "").strip() or app or "(제목 없음)"

    if kind == "메일" and not filename:
        label = re.sub(r"\s*-\s*메시지.*$", "", label).strip() or label

    return {"label": label[:120], "filename": filename, "kind": kind}


# --------------------------------------------------------------------------
# 과제 분류
# --------------------------------------------------------------------------
class ProjectClassifier:
    """설정의 키워드로 활동을 과제에 배정한다.

    영문 키워드는 단어 경계를 지킨다. 그러지 않으면 'rom' 이 'chrome' 에,
    'ax' 가 'max' 에 걸려서 엉뚱한 과제로 분류된다. 한글은 조사가 붙으므로
    부분 일치를 그대로 쓴다.
    """

    UNCLASSIFIED = "미분류"
    _ASCII = re.compile(r"[a-z0-9][a-z0-9 ./_-]*")

    def __init__(self, rules: list[dict[str, Any]] | None):
        self.rules: list[tuple[str, list[Any]]] = []
        for rule in rules or []:
            name = rule.get("name")
            keywords = [self._prepare(str(k).lower()) for k in rule.get("match", []) if k]
            if name and keywords:
                self.rules.append((name, keywords))

    @classmethod
    def _prepare(cls, keyword: str):
        if cls._ASCII.fullmatch(keyword):
            return re.compile(
                r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
            )
        return keyword

    @staticmethod
    def _hit(keyword: Any, blob: str) -> bool:
        return bool(keyword.search(blob)) if hasattr(keyword, "search") else keyword in blob

    def classify(self, *texts: Any) -> str:
        blob = " ".join(str(t) for t in texts if t).lower()
        for name, keywords in self.rules:
            if any(self._hit(keyword, blob) for keyword in keywords):
                return name
        return self.UNCLASSIFIED


# --------------------------------------------------------------------------
# 세션 병합
# --------------------------------------------------------------------------
def build_sessions(runs: list[dict], min_seconds: int) -> list[dict[str, Any]]:
    parsed = []
    for run in runs:
        start = period.parse_ts(run.get("start", ""))
        end = period.parse_ts(run.get("end", "")) or start
        if not start:
            continue
        info = parse_title(run.get("app", ""), run.get("title", ""))
        parsed.append(
            {
                "start": start,
                "end": end,
                "seconds": int(run.get("seconds", 0) or 0),
                "app": run.get("app", ""),
                "title": run.get("title", ""),
                **info,
            }
        )
    parsed.sort(key=lambda item: item["start"])

    sessions: list[dict[str, Any]] = []
    for item in parsed:
        previous = sessions[-1] if sessions else None
        same = (
            previous
            and previous["label"] == item["label"]
            and previous["kind"] == item["kind"]
            and (item["start"] - previous["end"]).total_seconds() <= MERGE_GAP_SECONDS
        )
        if same:
            previous["end"] = max(previous["end"], item["end"])
            previous["seconds"] += item["seconds"]
        else:
            sessions.append(dict(item))

    return [s for s in sessions if s["seconds"] >= min_seconds]


# --------------------------------------------------------------------------
# 교차검증
# --------------------------------------------------------------------------
def match_files_to_sessions(
    sessions: list[dict], files: list[dict]
) -> dict[int, list[dict]]:
    """세션 index → 그 세션에서 만들어졌다고 볼 수 있는 파일 목록."""
    by_stem: dict[str, list[dict]] = defaultdict(list)
    for record in files:
        stem = str(record.get("stem", "")).lower()
        if stem:
            by_stem[stem].append(record)

    matched: dict[int, list[dict]] = defaultdict(list)
    for index, session in enumerate(sessions):
        if not session["filename"]:
            continue
        stem = session["filename"].rsplit(".", 1)[0].lower()
        for record in by_stem.get(stem, []):
            mtime = period.parse_ts(record.get("time", ""))
            if not mtime:
                continue
            if session["start"] - FILE_MATCH_BEFORE <= mtime <= session["end"] + FILE_MATCH_AFTER:
                matched[index].append(record)
    return matched


# --------------------------------------------------------------------------
# 본 집계
# --------------------------------------------------------------------------
def build(cfg: dict, start: date, end: date, data: dict[str, list[dict]]) -> dict[str, Any]:
    classifier = ProjectClassifier(cfg.get("projects"))
    min_seconds = int(cfg["activity"]["min_session_seconds"])

    activity = data.get("activity", [])
    files = data.get("files", [])
    mail = [m for m in data.get("mail", []) if m.get("kind") == "mail"]
    meetings = [m for m in data.get("mail", []) if m.get("kind") == "meeting"]
    commits = data.get("git", [])

    sessions = build_sessions(activity, min_seconds)
    file_matches = match_files_to_sessions(sessions, files)
    used_files: set[str] = set()

    projects: dict[str, dict[str, Any]] = {}
    day_seconds: dict[str, int] = defaultdict(int)

    def bucket(name: str) -> dict[str, Any]:
        return projects.setdefault(
            name,
            {"name": name, "seconds": 0, "meeting_seconds": 0, "items": {}},
        )

    def add_item(project: str, key: str, **fields) -> dict[str, Any]:
        items = bucket(project)["items"]
        item = items.setdefault(
            key,
            {
                "label": fields.get("label", key),
                "kind": fields.get("kind", "기타"),
                "status": fields.get("status", ""),
                "seconds": 0,
                "days": [],
                "evidence": [],
            },
        )
        return item

    # 1) PC 활동 세션
    for index, session in enumerate(sessions):
        project = classifier.classify(
            session["label"], session["title"], session["app"]
        )
        matched = file_matches.get(index, [])
        if matched:
            status = "작성·수정"
            for record in matched:
                used_files.add(f"{record.get('dir')}/{record.get('name')}")
        else:
            status = "검토·열람"

        item = add_item(project, session["label"], label=session["label"],
                        kind=session["kind"], status=status)
        # 파일 수정이 확인되면 '검토·열람'을 '작성·수정'으로 올린다
        if status == "작성·수정":
            item["status"] = status
        item["seconds"] += session["seconds"]
        bucket(project)["seconds"] += session["seconds"]

        day = period.day_name(session["start"])
        if day and day not in item["days"]:
            item["days"].append(day)
        day_seconds[day] += session["seconds"]

        item["evidence"].append(
            {
                "type": "화면",
                "time": session["start"].isoformat(timespec="minutes"),
                "text": f"{session['title']} ({period.hm(session['seconds'])})",
            }
        )
        for record in matched:
            item["evidence"].append(
                {
                    "type": "파일",
                    "time": record.get("time", ""),
                    "text": f"{record.get('name')} 수정",
                }
            )

    # 2) 세션과 연결되지 않은 수정 파일 (PC 로깅 전에 만든 것 등)
    for record in files:
        key = f"{record.get('dir')}/{record.get('name')}"
        if key in used_files:
            continue
        project = classifier.classify(record.get("name"), record.get("dir"))
        item = add_item(project, str(record.get("name")), label=str(record.get("name")),
                        kind="문서", status="작성·수정")
        day = period.day_name(period.parse_ts(record.get("time", "")))
        if day and day not in item["days"]:
            item["days"].append(day)
        item["evidence"].append(
            {"type": "파일", "time": record.get("time", ""),
             "text": f"{record.get('name')} 수정"}
        )

    # 3) 회의
    for meeting in meetings:
        subject = str(meeting.get("subject") or "(제목 없음)")
        project = classifier.classify(subject, meeting.get("location"))
        seconds = int(meeting.get("seconds", 0) or 0)
        item = add_item(project, f"회의:{subject}", label=subject,
                        kind="회의", status="회의 참석")
        item["seconds"] += seconds
        bucket(project)["meeting_seconds"] += seconds
        day = period.day_name(period.parse_ts(meeting.get("time", "")))
        if day and day not in item["days"]:
            item["days"].append(day)
        item["evidence"].append(
            {"type": "일정", "time": meeting.get("time", ""),
             "text": f"{subject} ({period.hm(seconds)})"}
        )

    # 4) 보낸 메일 = 보고·발송 근거
    for record in mail:
        if record.get("direction") != "sent":
            continue
        subject = str(record.get("subject") or "(제목 없음)")
        project = classifier.classify(subject, record.get("snippet"), record.get("conversation"))
        item = add_item(project, f"메일:{subject}", label=subject,
                        kind="메일", status="보고·발송")
        day = period.day_name(period.parse_ts(record.get("time", "")))
        if day and day not in item["days"]:
            item["days"].append(day)
        item["evidence"].append(
            {"type": "메일", "time": record.get("time", ""),
             "text": f"발신: {subject}"}
        )

    # 5) 커밋
    for commit in commits:
        subject = str(commit.get("subject") or "")
        project = classifier.classify(
            subject, commit.get("repo"), " ".join(commit.get("files", []))
        )
        item = add_item(project, f"개발:{commit.get('repo')}", label=f"{commit.get('repo')} 개발",
                        kind="개발", status="커밋")
        day = period.day_name(period.parse_ts(commit.get("time", "")))
        if day and day not in item["days"]:
            item["days"].append(day)
        item["evidence"].append(
            {"type": "커밋", "time": commit.get("time", ""),
             "text": f"{commit.get('sha')} {subject} (+{commit.get('added', 0)}/-{commit.get('removed', 0)})"}
        )

    # 정리 — 항목을 시간 순으로, 근거는 최대 6개까지
    project_list = []
    for entry in projects.values():
        items = sorted(
            entry["items"].values(),
            key=lambda item: (-item["seconds"], item["label"]),
        )
        for item in items:
            item["evidence"] = item["evidence"][:6]
            item["days"] = _sort_days(item["days"])
            item["hours"] = period.hours(item["seconds"])
        entry["items"] = items
        entry["hours"] = period.hours(entry["seconds"])
        project_list.append(entry)
    project_list.sort(key=lambda entry: (entry["name"] == ProjectClassifier.UNCLASSIFIED,
                                         -entry["seconds"], entry["name"]))

    tracked = sum(s["seconds"] for s in sessions)
    meeting_total = sum(int(m.get("seconds", 0) or 0) for m in meetings)

    unclassified = next(
        (p for p in project_list if p["name"] == ProjectClassifier.UNCLASSIFIED), None
    )
    candidates = [
        {"label": item["label"], "hours": item["hours"]}
        for item in (unclassified["items"][:8] if unclassified else [])
        if item["seconds"] >= 1800
    ]

    return {
        "period": {
            "label": period.label(start, end),
            "slug": period.slug(start),
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "user": cfg.get("user", {}),
        "totals": {
            "tracked_seconds": tracked,
            "tracked_hours": period.hours(tracked),
            "meeting_seconds": meeting_total,
            "meeting_hours": period.hours(meeting_total),
            "by_day": {day: period.hours(sec) for day, sec in
                       sorted(day_seconds.items(),
                              key=lambda pair: period.WEEKDAY_KO.index(pair[0])
                              if pair[0] in period.WEEKDAY_KO else 9)},
            "sessions": len(sessions),
            "files": len(files),
            "sent_mails": sum(1 for m in mail if m.get("direction") == "sent"),
            "meetings": len(meetings),
            "commits": len(commits),
        },
        "projects": project_list,
        "new_project_candidates": candidates,
        "coverage": _coverage(activity, files, mail, meetings, commits),
    }


def _sort_days(days: list[str]) -> list[str]:
    order = {name: index for index, name in enumerate(period.WEEKDAY_KO)}
    return sorted(days, key=lambda day: order.get(day, 9))


def _coverage(activity, files, mail, meetings, commits) -> dict[str, Any]:
    """어떤 소스가 실제로 수집됐는지. 보고서에 한계를 명시하기 위해 쓴다."""
    return {
        "화면 기록": bool(activity),
        "수정 문서": bool(files),
        "메일": bool(mail),
        "회의 일정": bool(meetings),
        "git 커밋": bool(commits),
    }
