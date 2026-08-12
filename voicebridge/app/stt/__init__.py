from __future__ import annotations

from ..config import Settings
from .base import EngineUnavailable, STTEngine  # noqa: F401

ENGINES = ("faster-whisper",)


def create(settings: Settings) -> STTEngine:
    name = (settings.stt_engine or "faster-whisper").lower()
    if name in ("faster-whisper", "faster_whisper", "whisper"):
        from .faster_whisper_engine import FasterWhisperEngine

        return FasterWhisperEngine(settings)
    raise EngineUnavailable(
        f"알 수 없는 STT 엔진: {settings.stt_engine} (가능: {', '.join(ENGINES)})"
    )


def available(settings: Settings) -> dict[str, bool]:
    """설치 여부만 가볍게 확인 (모델 로딩은 하지 않는다)."""
    import importlib.util

    return {"faster-whisper": importlib.util.find_spec("faster_whisper") is not None}
