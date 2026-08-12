"""회의록 데이터 구조와 마크다운 렌더러."""
from __future__ import annotations

import io
import json
from dataclasses import asdict, dataclass, field

from ..text.postprocess import fmt_clock


@dataclass
class ActionItem:
    task: str
    owner: str = "미정"
    due: str = "미정"
    source_time: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "ActionItem":
        return ActionItem(
            task=str(d.get("task", "")).strip(),
            owner=str(d.get("owner") or "미정").strip(),
            due=str(d.get("due") or "미정").strip(),
            source_time=d.get("source_time"),
        )


@dataclass
class Topic:
    title: str
    points: list[str] = field(default_factory=list)
    start: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Topic":
        return Topic(
            title=str(d.get("title", "")).strip(),
            points=[str(p).strip() for p in d.get("points", []) if str(p).strip()],
            start=d.get("start"),
        )


@dataclass
class Minutes:
    title: str = "회의록"
    date: str = ""
    duration: float = 0.0
    attendees: list[str] = field(default_factory=list)
    summary: str = ""
    topics: list[Topic] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    actions: list[ActionItem] = field(default_factory=list)
    open_issues: list[str] = field(default_factory=list)
    backend: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["topics"] = [t.to_dict() for t in self.topics]
        d["actions"] = [a.to_dict() for a in self.actions]
        return d

    @staticmethod
    def from_dict(d: dict) -> "Minutes":
        return Minutes(
            title=str(d.get("title") or "회의록"),
            date=str(d.get("date") or ""),
            duration=float(d.get("duration") or 0.0),
            attendees=[str(a) for a in d.get("attendees", [])],
            summary=str(d.get("summary") or ""),
            topics=[Topic.from_dict(t) for t in d.get("topics", [])],
            decisions=[str(x).strip() for x in d.get("decisions", []) if str(x).strip()],
            actions=[ActionItem.from_dict(a) for a in d.get("actions", [])],
            open_issues=[str(x).strip() for x in d.get("open_issues", []) if str(x).strip()],
            backend=str(d.get("backend") or ""),
            warnings=[str(w) for w in d.get("warnings", [])],
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    def to_markdown(self) -> str:
        out = io.StringIO()
        out.write(f"# {self.title}\n\n")

        out.write("| 항목 | 내용 |\n|---|---|\n")
        out.write(f"| 일시 | {self.date or '-'} |\n")
        out.write(f"| 소요 | {fmt_clock(self.duration)} |\n")
        out.write(f"| 참석 | {', '.join(self.attendees) if self.attendees else '-'} |\n")
        out.write("\n")

        if self.summary:
            out.write("## 한 줄 요약\n\n")
            out.write(f"{self.summary}\n\n")

        if self.topics:
            out.write("## 안건별 논의\n\n")
            for i, t in enumerate(self.topics, start=1):
                stamp = f" `{fmt_clock(t.start)}`" if t.start is not None else ""
                out.write(f"### {i}. {t.title}{stamp}\n\n")
                for p in t.points:
                    out.write(f"- {p}\n")
                out.write("\n")

        out.write("## 결정사항\n\n")
        if self.decisions:
            for d in self.decisions:
                out.write(f"- {d}\n")
        else:
            out.write("- (명시적 결정사항 없음)\n")
        out.write("\n")

        out.write("## 액션 아이템\n\n")
        if self.actions:
            out.write("| # | 할 일 | 담당 | 기한 |\n|---|---|---|---|\n")
            for i, a in enumerate(self.actions, start=1):
                task = a.task.replace("|", "\\|")
                out.write(f"| {i} | {task} | {a.owner} | {a.due} |\n")
        else:
            out.write("- (도출된 액션 아이템 없음)\n")
        out.write("\n")

        if self.open_issues:
            out.write("## 미결 / 후속 확인\n\n")
            for x in self.open_issues:
                out.write(f"- {x}\n")
            out.write("\n")

        out.write("---\n\n")
        out.write(f"_자동 생성 ({self.backend or 'unknown'}). 배포 전 사실관계 확인 필요._\n")
        if self.warnings:
            for w in self.warnings:
                out.write(f"\n> ⚠ {w}\n")
        return out.getvalue()

    def to_txt(self) -> str:
        """마크다운 문법 없이 사내 메일/메신저에 그대로 붙일 수 있는 형태."""
        out = io.StringIO()
        out.write(f"[{self.title}]\n")
        out.write(f"일시: {self.date or '-'} / 소요: {fmt_clock(self.duration)}\n")
        out.write(f"참석: {', '.join(self.attendees) if self.attendees else '-'}\n\n")
        if self.summary:
            out.write(f"■ 요약\n{self.summary}\n\n")
        if self.topics:
            out.write("■ 논의 내용\n")
            for i, t in enumerate(self.topics, start=1):
                out.write(f" {i}) {t.title}\n")
                for p in t.points:
                    out.write(f"    - {p}\n")
            out.write("\n")
        out.write("■ 결정사항\n")
        for d in self.decisions or ["(없음)"]:
            out.write(f" - {d}\n")
        out.write("\n■ 액션 아이템\n")
        if self.actions:
            for a in self.actions:
                out.write(f" - {a.task} (담당: {a.owner}, 기한: {a.due})\n")
        else:
            out.write(" - (없음)\n")
        if self.open_issues:
            out.write("\n■ 미결\n")
            for x in self.open_issues:
                out.write(f" - {x}\n")
        return out.getvalue()
