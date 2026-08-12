"""전사 결과를 각종 파일 포맷으로 내보낸다."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from .models import Transcript
from .text.postprocess import fmt_clock

FORMATS = ("txt", "md", "srt", "vtt", "json", "csv")


def _ts(seconds: float, comma: bool = True) -> str:
    seconds = max(0.0, seconds)
    ms = int(round((seconds - int(seconds)) * 1000))
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    sep = "," if comma else "."
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_txt(tr: Transcript, timestamps: bool = True) -> str:
    lines: list[str] = []
    for s in tr.segments:
        prefix = ""
        if timestamps:
            prefix += f"[{fmt_clock(s.start)}] "
        if s.speaker:
            prefix += f"{s.speaker}: "
        lines.append(f"{prefix}{s.text}")
    return "\n".join(lines) + ("\n" if lines else "")


def to_md(tr: Transcript, title: str = "녹취록") -> str:
    out = io.StringIO()
    out.write(f"# {title}\n\n")
    out.write(f"- 원본: `{tr.source or '-'}`\n")
    out.write(f"- 길이: {fmt_clock(tr.duration)}\n")
    out.write(f"- 언어: {tr.language or '-'}\n")
    if tr.speakers:
        out.write(f"- 화자: {', '.join(tr.speakers)}\n")
    out.write("\n---\n\n")
    for s in tr.segments:
        who = f"**{s.speaker}** " if s.speaker else ""
        out.write(f"`{fmt_clock(s.start)}` {who}{s.text}\n\n")
    return out.getvalue()


def to_srt(tr: Transcript) -> str:
    out = io.StringIO()
    for i, s in enumerate(tr.segments, start=1):
        text = f"{s.speaker}: {s.text}" if s.speaker else s.text
        out.write(f"{i}\n{_ts(s.start)} --> {_ts(s.end)}\n{text}\n\n")
    return out.getvalue()


def to_vtt(tr: Transcript) -> str:
    out = io.StringIO()
    out.write("WEBVTT\n\n")
    for s in tr.segments:
        text = f"{s.speaker}: {s.text}" if s.speaker else s.text
        out.write(f"{_ts(s.start, comma=False)} --> {_ts(s.end, comma=False)}\n{text}\n\n")
    return out.getvalue()


def to_json(tr: Transcript) -> str:
    return json.dumps(tr.to_dict(), ensure_ascii=False, indent=2)


def to_csv(tr: Transcript) -> str:
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["start", "end", "start_hms", "speaker", "text"])
    for s in tr.segments:
        w.writerow([f"{s.start:.3f}", f"{s.end:.3f}", fmt_clock(s.start),
                    s.speaker or "", s.text])
    return out.getvalue()


def render(tr: Transcript, fmt: str, **kwargs) -> str:
    fmt = fmt.lower().lstrip(".")
    if fmt == "txt":
        return to_txt(tr, **kwargs)
    if fmt in ("md", "markdown"):
        return to_md(tr, **kwargs)
    if fmt == "srt":
        return to_srt(tr)
    if fmt == "vtt":
        return to_vtt(tr)
    if fmt == "json":
        return to_json(tr)
    if fmt == "csv":
        return to_csv(tr)
    raise ValueError(f"지원하지 않는 포맷: {fmt} (가능: {', '.join(FORMATS)})")


def save(tr: Transcript, path: str | Path, fmt: str | None = None, **kwargs) -> Path:
    path = Path(path)
    fmt = fmt or path.suffix
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(tr, fmt, **kwargs), encoding="utf-8")
    return path


def save_all(tr: Transcript, out_dir: str | Path, stem: str,
             formats: tuple[str, ...] = FORMATS) -> dict[str, Path]:
    out_dir = Path(out_dir)
    written: dict[str, Path] = {}
    for fmt in formats:
        ext = "md" if fmt == "markdown" else fmt
        written[fmt] = save(tr, out_dir / f"{stem}.{ext}", fmt)
    return written
