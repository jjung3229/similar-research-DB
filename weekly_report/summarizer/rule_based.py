"""LLM 없이 만드는 초안.

문장을 지어내지 않는다. 수집된 사실을 과제별로 정렬해서 보여줄 뿐이고, 다듬는 것은
사람이 한다. 그래도 "이번 주에 뭘 했더라"를 떠올리는 시간은 없어진다.
"""

from __future__ import annotations

from .. import period

STATUS_ORDER = {"작성·수정": 0, "커밋": 1, "보고·발송": 2, "회의 참석": 3, "검토·열람": 4}


def render(pack: dict) -> str:
    lines: list[str] = []
    info = pack["period"]
    user = pack.get("user", {})
    totals = pack.get("totals", {})

    title = f"# 주간업무보고 — {info['label']}"
    lines.append(title)
    who = " / ".join(x for x in (user.get("team"), user.get("name")) if x)
    if who:
        lines.append(f"\n**{who}**")
    lines.append(
        "\n> 수집된 기록으로 만든 **초안**입니다. 사실 확인 후 문장을 다듬어 사용하세요.\n"
    )

    # 1. 금주 실적
    lines.append("## 1. 금주 실적\n")
    work_projects = [p for p in pack.get("projects", []) if p["name"] != "미분류"]
    if not work_projects:
        lines.append("- (분류된 과제가 없습니다. config 의 projects 규칙을 설정해 주세요.)\n")

    for project in work_projects:
        lines.append(f"### {project['name']} — {period.hm(project['seconds'])}\n")
        for item in _sorted_items(project["items"]):
            if item["status"] == "회의 참석":
                continue                       # 회의는 2번 항목에서 따로 정리
            days = f"({'/'.join(item['days'])})" if item["days"] else ""
            spent = f", {period.hm(item['seconds'])}" if item["seconds"] else ""
            lines.append(f"- **{item['label']}** — {item['status']}{spent} {days}".rstrip())
            for record in item["evidence"][:2]:
                lines.append(f"    - 근거: [{record['type']}] {record['text']}")
        lines.append("")

    # 2. 회의·협의
    meetings = [
        (project["name"], item)
        for project in pack.get("projects", [])
        for item in project["items"]
        if item["status"] == "회의 참석"
    ]
    lines.append("## 2. 회의·협의\n")
    if meetings:
        for name, item in meetings:
            days = f"({'/'.join(item['days'])})" if item["days"] else ""
            lines.append(f"- {item['label']} — {period.hm(item['seconds'])} {days} · {name}".rstrip())
    else:
        lines.append("- (수집된 회의 일정이 없습니다.)")
    lines.append("")

    # 3. 차주 계획
    lines.append("## 3. 차주 계획\n")
    lines.append("<!-- 자동으로 알 수 없는 항목입니다. 직접 작성하세요. -->")
    carry_over = [
        (project["name"], item["label"])
        for project in work_projects
        for item in project["items"][:2]
        if item["status"] in ("작성·수정", "커밋")
    ][:5]
    for name, label in carry_over:
        lines.append(f"- [ ] {name}: {label} 후속 진행")
    lines.append("")

    # 4. 시간 배분
    lines.append("## 4. 시간 배분\n")
    lines.append("| 과제 | PC 활동 | 회의 | 합계 | 비중 |")
    lines.append("|---|---:|---:|---:|---:|")
    grand = sum(
        p["seconds"] + p.get("meeting_seconds", 0) for p in pack.get("projects", [])
    ) or 1
    for project in pack.get("projects", []):
        meeting = project.get("meeting_seconds", 0)
        combined = project["seconds"] + meeting
        lines.append(
            f"| {project['name']} | {period.hm(project['seconds'])} | "
            f"{period.hm(meeting) if meeting else '-'} | {period.hm(combined)} | "
            f"{combined / grand * 100:.0f}% |"
        )
    lines.append("")
    lines.append(
        "<!-- PC 활동은 창 사용 시간 기준이라 실제 업무시간과 다를 수 있습니다. -->"
    )
    by_day = totals.get("by_day", {})
    if by_day:
        lines.append(
            "일별 PC 활동: "
            + ", ".join(f"{day} {value}h" for day, value in by_day.items())
        )
        lines.append("")

    # 신규 과제 후보
    candidates = pack.get("new_project_candidates", [])
    if candidates:
        lines.append("## 5. 분류되지 않은 활동 (과제 규칙 추가 검토)\n")
        for candidate in candidates:
            lines.append(f"- {candidate['label']} — {candidate['hours']}시간")
        lines.append("")

    # 부록
    lines.append("---\n")
    lines.append(
        f"수집 요약: PC 활동 {totals.get('tracked_hours', 0)}시간 · "
        f"회의 {totals.get('meeting_hours', 0)}시간 · "
        f"수정 문서 {totals.get('files', 0)}건 · "
        f"보낸 메일 {totals.get('sent_mails', 0)}건 · "
        f"커밋 {totals.get('commits', 0)}건"
    )
    missing = [name for name, ok in pack.get("coverage", {}).items() if not ok]
    if missing:
        lines.append(f"\n※ 수집되지 않은 소스: {', '.join(missing)} — 그만큼 누락이 있을 수 있습니다.")

    return "\n".join(lines) + "\n"


def _sorted_items(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (STATUS_ORDER.get(item["status"], 5), -item["seconds"]),
    )
