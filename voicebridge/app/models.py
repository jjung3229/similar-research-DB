"""파이프라인 전체에서 오가는 데이터 구조."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Segment:
    """STT가 뽑아낸 발화 한 토막."""
    start: float
    end: float
    text: str
    speaker: str | None = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Segment":
        return Segment(
            start=float(d["start"]),
            end=float(d["end"]),
            text=str(d.get("text", "")),
            speaker=d.get("speaker"),
        )


@dataclass
class Transcript:
    segments: list[Segment] = field(default_factory=list)
    language: str | None = None
    duration: float = 0.0
    source: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments if s.text.strip())

    @property
    def speakers(self) -> list[str]:
        seen: list[str] = []
        for s in self.segments:
            if s.speaker and s.speaker not in seen:
                seen.append(s.speaker)
        return seen

    def to_dict(self) -> dict:
        return {
            "segments": [s.to_dict() for s in self.segments],
            "language": self.language,
            "duration": self.duration,
            "source": self.source,
            "meta": self.meta,
        }

    @staticmethod
    def from_dict(d: dict) -> "Transcript":
        return Transcript(
            segments=[Segment.from_dict(x) for x in d.get("segments", [])],
            language=d.get("language"),
            duration=float(d.get("duration", 0.0)),
            source=d.get("source", ""),
            meta=d.get("meta", {}),
        )
