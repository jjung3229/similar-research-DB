"""MeloTTS. MIT 라이선스이고 한국어 품질이 Piper 보다 자연스럽다.

대신 torch 를 끌고 오므로 설치 용량이 크다(수 GB).
"""
from __future__ import annotations

from pathlib import Path

from ..config import Settings
from .base import TTSEngine, TTSUnavailable

HINT = (
    "MeloTTS 가 설치되어 있지 않습니다.\n"
    "  pip install melotts\n"
    "  python -m unidic download   # 일부 환경에서 필요\n"
    "torch 를 포함해 수 GB 를 내려받습니다. 용량이 부담되면 piper 를 쓰세요."
)


class MeloEngine(TTSEngine):
    name = "melo"

    def __init__(self, settings: Settings):
        try:
            from melo.api import TTS  # type: ignore
        except ImportError as exc:
            raise TTSUnavailable(HINT) from exc

        from ..stt.faster_whisper_engine import resolve_device

        device = resolve_device(settings.device)
        try:
            self.model = TTS(language="KR", device=device)
        except Exception as exc:  # pragma: no cover - 환경 의존
            raise TTSUnavailable(f"MeloTTS 모델 로딩 실패: {exc}") from exc

        self.speaker_ids = self.model.hps.data.spk2id
        want = settings.tts_voice or next(iter(self.speaker_ids))
        if want not in self.speaker_ids:
            raise TTSUnavailable(
                f"화자 '{want}' 가 없습니다. 사용 가능: {', '.join(self.speaker_ids)}"
            )
        self.speaker = want
        self.speed = settings.tts_speed

    def voices(self) -> list[str]:
        return list(self.speaker_ids)

    def synth_chunk(self, text: str, out_wav: str | Path) -> Path:
        out_wav = Path(out_wav)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        self.model.tts_to_file(
            text, self.speaker_ids[self.speaker], str(out_wav), speed=self.speed
        )
        if not out_wav.exists():
            raise TTSUnavailable("MeloTTS 가 파일을 만들지 못했습니다.")
        return out_wav
