"""OS 내장 음성 합성(Windows SAPI / macOS say / Linux espeak).

설치·다운로드가 0 이고 네트워크를 전혀 쓰지 않으므로,
사내 PC 에서 반입 심사 없이 바로 돌려볼 수 있는 최후의 보루다.
품질은 Piper/Melo 보다 확실히 떨어진다.
"""
from __future__ import annotations

from pathlib import Path

from ..config import Settings
from .base import TTSEngine, TTSUnavailable

HINT = (
    "pyttsx3 가 설치되어 있지 않습니다.\n"
    "  pip install pyttsx3\n"
    "Windows 는 [설정 > 시간 및 언어 > 음성]에서 한국어 음성(Heami 등)이 "
    "설치되어 있어야 합니다."
)


class SystemEngine(TTSEngine):
    name = "system"

    def __init__(self, settings: Settings):
        try:
            import pyttsx3  # type: ignore
        except ImportError as exc:
            raise TTSUnavailable(HINT) from exc

        try:
            self.engine = pyttsx3.init()
        except Exception as exc:  # pragma: no cover - 환경 의존
            raise TTSUnavailable(f"OS 음성 엔진 초기화 실패: {exc}") from exc

        self._voices = list(self.engine.getProperty("voices") or [])
        target = settings.tts_voice
        if not target:
            # 한국어 음성을 자동으로 고른다.
            for v in self._voices:
                blob = f"{getattr(v, 'id', '')} {getattr(v, 'name', '')}".lower()
                if "korean" in blob or "ko_kr" in blob or "ko-kr" in blob or "heami" in blob:
                    target = v.id
                    break
        if target:
            self.engine.setProperty("voice", target)

        base_rate = self.engine.getProperty("rate") or 200
        self.engine.setProperty("rate", int(base_rate * settings.tts_speed))

    def voices(self) -> list[str]:
        return [f"{getattr(v, 'name', '?')} :: {getattr(v, 'id', '')}" for v in self._voices]

    def synth_chunk(self, text: str, out_wav: str | Path) -> Path:
        out_wav = Path(out_wav)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        self.engine.save_to_file(text, str(out_wav))
        self.engine.runAndWait()
        if not out_wav.exists():
            raise TTSUnavailable(
                "OS 음성 엔진이 파일을 만들지 못했습니다. "
                "Linux 라면 espeak-ng 설치가 필요할 수 있습니다."
            )
        return out_wav
