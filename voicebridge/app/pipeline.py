"""입력 → 전사 → 회의록(→ 선택적 음성 재생성) 전체 흐름.

입력 어댑터가 Transcript 를 만들어 주기만 하면 뒷단은 동일하다.
그래서 '녹음 파일' 이든 '실시간 마이크' 든 같은 회의록 로직을 탄다.
"""
from __future__ import annotations

import datetime as _dt
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import diarize, exporters, minutes as minutes_mod, stt, tts
from .audio import AUDIO_EXTS, probe_duration, to_wav16k
from .config import Settings
from .models import Transcript
from .text.postprocess import clean_transcript, merge_by_speaker

ProgressFn = Callable[[float, str], None]


@dataclass
class PipelineOptions:
    make_minutes: bool = True
    make_tts: bool = False
    drop_fillers: bool = True
    num_speakers: int | None = None
    title: str = ""
    date: str = ""
    formats: tuple[str, ...] = ("txt", "md", "srt", "json")


@dataclass
class PipelineResult:
    transcript: Transcript
    files: dict[str, Path] = field(default_factory=dict)
    minutes: object | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "transcript": self.transcript.to_dict(),
            "files": {k: str(v) for k, v in self.files.items()},
            "minutes": self.minutes.to_dict() if self.minutes is not None else None,
            "warnings": self.warnings,
        }


def _noop(_pct: float, _msg: str) -> None:
    pass


def _scaled(progress: ProgressFn, lo: float, hi: float) -> ProgressFn:
    """하위 단계의 0~1 진행률을 전체 구간(lo~hi)으로 매핑."""
    def inner(pct: float, msg: str) -> None:
        progress(lo + (hi - lo) * max(0.0, min(1.0, pct)), msg)

    return inner


def transcribe_file(
    settings: Settings,
    src: str | Path,
    *,
    progress: ProgressFn | None = None,
    engine: stt.STTEngine | None = None,
    num_speakers: int | None = None,
    drop_fillers: bool = True,
) -> Transcript:
    """오디오/영상 파일 하나를 Transcript 로."""
    progress = progress or _noop
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {src}")
    if src.suffix.lower() not in AUDIO_EXTS:
        raise ValueError(
            f"지원하지 않는 확장자: {src.suffix} "
            f"(가능: {', '.join(sorted(AUDIO_EXTS))})"
        )

    with tempfile.TemporaryDirectory(prefix="vb-in-") as tmp:
        progress(0.02, "오디오 변환 중 (16kHz 모노)")
        wav = to_wav16k(src, Path(tmp) / "input.wav")

        progress(0.05, "모델 로딩 중")
        eng = engine or stt.create(settings)

        tr = eng.transcribe(wav, progress=_scaled(progress, 0.05, 0.80))
        tr.source = src.name
        if not tr.duration:
            tr.duration = probe_duration(wav)

        if (settings.diarize_engine or "none").lower() != "none":
            progress(0.82, "화자 분리 중")
            try:
                tr = diarize.run(settings, wav, tr, num_speakers=num_speakers)
            except diarize.DiarizeUnavailable as exc:
                tr.meta["diarize_error"] = str(exc)

    progress(0.90, "텍스트 정리 중")
    tr = clean_transcript(tr, drop_fillers=drop_fillers)
    if tr.speakers:
        tr = merge_by_speaker(tr)
    return tr


def run_file(
    settings: Settings,
    src: str | Path,
    out_dir: str | Path,
    options: PipelineOptions | None = None,
    progress: ProgressFn | None = None,
) -> PipelineResult:
    """파일 하나에 대해 전 과정을 돌리고 산출물을 out_dir 에 떨군다."""
    opt = options or PipelineOptions()
    progress = progress or _noop
    src = Path(src)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem
    result_warnings: list[str] = []

    tr = transcribe_file(
        settings, src,
        progress=_scaled(progress, 0.0, 0.70 if opt.make_minutes else 0.90),
        num_speakers=opt.num_speakers,
        drop_fillers=opt.drop_fillers,
    )
    if tr.meta.get("diarize_error"):
        result_warnings.append(f"화자 분리 실패: {tr.meta['diarize_error']}")

    files = exporters.save_all(tr, out_dir, stem, formats=opt.formats)

    mins = None
    if opt.make_minutes:
        progress(0.72, "회의록 작성 중")
        title = opt.title or f"{stem} 회의록"
        date = opt.date or _dt.date.fromtimestamp(src.stat().st_mtime).isoformat()
        try:
            mins = minutes_mod.build(
                settings, tr, title=title, date=date,
                progress=_scaled(progress, 0.72, 0.92),
            )
        except Exception as exc:  # noqa: BLE001 - 회의록 실패로 전사까지 버리지 않는다
            result_warnings.append(f"회의록 생성 실패: {exc}")
        if mins is not None:
            files["minutes_md"] = out_dir / f"{stem}.회의록.md"
            files["minutes_md"].write_text(mins.to_markdown(), encoding="utf-8")
            files["minutes_txt"] = out_dir / f"{stem}.회의록.txt"
            files["minutes_txt"].write_text(mins.to_txt(), encoding="utf-8")
            files["minutes_json"] = out_dir / f"{stem}.회의록.json"
            files["minutes_json"].write_text(mins.to_json(), encoding="utf-8")

    if opt.make_tts:
        progress(0.93, "음성 재생성 중")
        try:
            body = mins.to_txt() if mins is not None else tr.text
            files["tts_wav"] = tts.speak(
                settings, body, out_dir / f"{stem}.tts.wav",
                progress=_scaled(progress, 0.93, 0.99),
            )
        except Exception as exc:  # noqa: BLE001
            result_warnings.append(f"음성 합성 실패: {exc}")

    progress(1.0, "완료")
    return PipelineResult(transcript=tr, files=files, minutes=mins,
                          warnings=result_warnings)


def run_batch(
    settings: Settings,
    sources: list[str | Path],
    out_dir: str | Path,
    options: PipelineOptions | None = None,
    progress: ProgressFn | None = None,
) -> list[PipelineResult]:
    """여러 파일을 한 번의 모델 로딩으로 처리한다."""
    progress = progress or _noop
    opt = options or PipelineOptions()
    out_dir = Path(out_dir)
    engine = stt.create(settings)          # 모델은 한 번만 올린다
    results: list[PipelineResult] = []

    total = len(sources) or 1
    for i, src in enumerate(sources):
        lo, hi = i / total, (i + 1) / total
        step = _scaled(progress, lo, hi)
        src = Path(src)
        try:
            tr = transcribe_file(
                settings, src, progress=_scaled(step, 0.0, 0.7),
                engine=engine, num_speakers=opt.num_speakers,
                drop_fillers=opt.drop_fillers,
            )
        except Exception as exc:  # noqa: BLE001 - 한 파일 실패로 배치를 멈추지 않는다
            step(1.0, f"실패: {src.name} ({exc})")
            results.append(PipelineResult(
                transcript=Transcript(source=src.name),
                warnings=[f"{src.name}: {exc}"],
            ))
            continue

        target = out_dir / src.stem
        target.mkdir(parents=True, exist_ok=True)
        files = exporters.save_all(tr, target, src.stem, formats=opt.formats)

        mins = None
        warnings: list[str] = []
        if opt.make_minutes:
            try:
                mins = minutes_mod.build(
                    settings, tr,
                    title=opt.title or f"{src.stem} 회의록",
                    date=opt.date,
                    progress=_scaled(step, 0.7, 0.95),
                )
                if mins is not None:
                    files["minutes_md"] = target / f"{src.stem}.회의록.md"
                    files["minutes_md"].write_text(mins.to_markdown(), encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"회의록 생성 실패: {exc}")

        step(1.0, f"완료: {src.name}")
        results.append(PipelineResult(transcript=tr, files=files,
                                      minutes=mins, warnings=warnings))
    return results


def collect_sources(paths: list[str | Path], recursive: bool = True) -> list[Path]:
    """파일/폴더 인자를 실제 미디어 파일 목록으로 펼친다."""
    out: list[Path] = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            out.extend(sorted(f for f in it
                              if f.is_file() and f.suffix.lower() in AUDIO_EXTS))
        elif p.is_file():
            out.append(p)
    # 중복 제거(순서 유지)
    seen: set[Path] = set()
    uniq: list[Path] = []
    for f in out:
        rp = f.resolve()
        if rp not in seen:
            seen.add(rp)
            uniq.append(f)
    return uniq


def purge_old(directory: str | Path, hours: int) -> int:
    """보존 기간이 지난 작업 폴더를 지운다. 지운 개수 반환."""
    if hours <= 0:
        return 0
    directory = Path(directory)
    if not directory.is_dir():
        return 0
    cutoff = _dt.datetime.now().timestamp() - hours * 3600
    removed = 0
    for child in directory.iterdir():
        try:
            if child.stat().st_mtime < cutoff:
                shutil.rmtree(child) if child.is_dir() else child.unlink()
                removed += 1
        except OSError:
            continue
    return removed
