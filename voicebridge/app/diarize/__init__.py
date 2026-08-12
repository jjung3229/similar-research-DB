"""화자 분리(diarization).

pyannote 는 최초 1회 모델 다운로드에 HuggingFace 토큰과 라이선스 동의가 필요하다.
사내 정책상 그마저 곤란하면 diarize_engine="none" 으로 두고,
회의록 단계에서 화자 이름을 수동 매핑하면 된다.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from ..config import Settings
from ..models import Segment, Transcript

ENGINES = ("none", "pyannote")


class DiarizeUnavailable(RuntimeError):
    pass


def available(settings: Settings) -> dict[str, bool]:
    return {
        "none": True,
        "pyannote": importlib.util.find_spec("pyannote") is not None,
    }


def assign_speakers(tr: Transcript, turns: list[tuple[float, float, str]]) -> Transcript:
    """화자 구간(turns)과 STT 세그먼트를 겹친 시간이 가장 긴 쪽으로 매칭한다."""
    if not turns:
        return tr
    for seg in tr.segments:
        best, best_overlap = None, 0.0
        for start, end, label in turns:
            overlap = min(seg.end, end) - max(seg.start, start)
            if overlap > best_overlap:
                best, best_overlap = label, overlap
        seg.speaker = best or seg.speaker
    return tr


def relabel_korean(tr: Transcript) -> Transcript:
    """SPEAKER_00 → 화자1 처럼 읽기 쉬운 이름으로 바꾼다."""
    mapping: dict[str, str] = {}
    for seg in tr.segments:
        if seg.speaker and seg.speaker not in mapping:
            mapping[seg.speaker] = f"화자{len(mapping) + 1}"
    for seg in tr.segments:
        if seg.speaker:
            seg.speaker = mapping[seg.speaker]
    return tr


def run(settings: Settings, wav_path: str | Path, tr: Transcript,
        num_speakers: int | None = None) -> Transcript:
    engine = (settings.diarize_engine or "none").lower()
    if engine in ("none", "off", ""):
        return tr
    if engine != "pyannote":
        raise DiarizeUnavailable(f"알 수 없는 화자분리 엔진: {engine}")

    try:
        from pyannote.audio import Pipeline  # type: ignore
    except ImportError as exc:
        raise DiarizeUnavailable(
            "pyannote.audio 가 설치되어 있지 않습니다.\n  pip install pyannote.audio"
        ) from exc

    cache = Path(settings.model_dir) / "pyannote"
    cache.mkdir(parents=True, exist_ok=True)
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=settings.hf_token or None,
            cache_dir=str(cache),
        )
    except Exception as exc:
        raise DiarizeUnavailable(
            "pyannote 모델을 불러오지 못했습니다. 최초 1회는 인터넷과 "
            "HuggingFace 토큰(VB_HF_TOKEN)이 필요하고, 모델 페이지에서 "
            "라이선스에 동의해야 합니다."
        ) from exc

    kwargs = {"num_speakers": num_speakers} if num_speakers else {}
    annotation = pipeline(str(wav_path), **kwargs)

    turns: list[tuple[float, float, str]] = [
        (float(turn.start), float(turn.end), str(label))
        for turn, _, label in annotation.itertracks(yield_label=True)
    ]
    tr = assign_speakers(tr, turns)
    tr = relabel_korean(tr)
    tr.meta["diarization"] = {"engine": "pyannote", "turns": len(turns)}
    return tr
