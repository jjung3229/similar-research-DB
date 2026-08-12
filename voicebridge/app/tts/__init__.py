from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

from ..audio import concat_wavs
from ..config import Settings
from ..text.postprocess import chunk_for_tts
from .base import TTSEngine, TTSUnavailable  # noqa: F401

ENGINES = ("piper", "melo", "system")


def create(settings: Settings) -> TTSEngine:
    name = (settings.tts_engine or "piper").lower()
    if name == "piper":
        from .piper_engine import PiperEngine

        return PiperEngine(settings)
    if name in ("melo", "melotts"):
        from .melo_engine import MeloEngine

        return MeloEngine(settings)
    if name in ("system", "pyttsx3", "os"):
        from .system_engine import SystemEngine

        return SystemEngine(settings)
    raise TTSUnavailable(f"알 수 없는 TTS 엔진: {settings.tts_engine} (가능: {', '.join(ENGINES)})")


def available(settings: Settings) -> dict[str, bool]:
    piper_ok = bool(shutil.which("piper")) or importlib.util.find_spec("piper") is not None
    return {
        "piper": piper_ok,
        "melo": importlib.util.find_spec("melo") is not None,
        "system": importlib.util.find_spec("pyttsx3") is not None,
    }


def speak(settings: Settings, text: str, out_wav: str | Path,
          engine: TTSEngine | None = None, progress=None) -> Path:
    """긴 텍스트를 청크로 나눠 합성한 뒤 하나의 wav 로 이어붙인다."""
    text = (text or "").strip()
    if not text:
        raise TTSUnavailable("합성할 텍스트가 비어 있습니다.")

    eng = engine or create(settings)
    chunks = chunk_for_tts(text, max_chars=settings.tts_chunk_chars)
    out_wav = Path(out_wav)

    with tempfile.TemporaryDirectory(prefix="vb-tts-") as tmp:
        parts: list[Path] = []
        for i, chunk in enumerate(chunks):
            part = Path(tmp) / f"part_{i:05d}.wav"
            eng.synth_chunk(chunk, part)
            parts.append(part)
            if progress:
                progress((i + 1) / len(chunks), f"음성 합성 {i + 1}/{len(chunks)}")
        if len(parts) == 1:
            out_wav.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(parts[0], out_wav)
        else:
            concat_wavs(parts, out_wav, gap_ms=settings.tts_gap_ms)
    return out_wav
