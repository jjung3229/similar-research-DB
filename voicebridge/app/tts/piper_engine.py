"""Piper TTS. MIT 라이선스, 완전 오프라인, CPU 로도 실시간보다 빠르다.

음성 모델은 .onnx + .onnx.json 두 파일 한 쌍이다.
vb-models/piper/ 에 넣어두면 자동으로 찾는다.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..config import Settings
from .base import TTSEngine, TTSUnavailable

HINT = (
    "Piper 를 찾을 수 없습니다.\n"
    "  1) pip install piper-tts   (또는 github.com/rhasspy/piper 릴리스 바이너리)\n"
    "  2) 한국어 음성 모델(.onnx + .onnx.json)을 vb-models/piper/ 에 저장\n"
    "     예: ko_KR-*.onnx\n"
    "  3) VB_TTS_VOICE 로 파일명을 지정 (비우면 폴더에서 첫 번째를 사용)"
)


def _find_binary() -> list[str] | None:
    exe = shutil.which("piper")
    if exe:
        return [exe]
    # pip 로 설치한 경우 모듈 실행이 가능하다.
    try:
        import piper  # type: ignore  # noqa: F401

        import sys

        return [sys.executable, "-m", "piper"]
    except ImportError:
        return None


class PiperEngine(TTSEngine):
    name = "piper"

    def __init__(self, settings: Settings):
        cmd = _find_binary()
        if not cmd:
            raise TTSUnavailable(HINT)
        self.cmd = cmd
        self.voice_dir = Path(settings.model_dir) / "piper"
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.model = self._resolve_voice(settings.tts_voice)
        self.speed = settings.tts_speed

    def _resolve_voice(self, voice: str) -> Path:
        if voice:
            cand = Path(voice)
            if cand.is_file():
                return cand
            cand = self.voice_dir / voice
            if cand.is_file():
                return cand
            if not str(cand).endswith(".onnx"):
                cand = self.voice_dir / f"{voice}.onnx"
                if cand.is_file():
                    return cand
            raise TTSUnavailable(f"Piper 음성 모델을 찾지 못했습니다: {voice}\n{HINT}")

        found = sorted(self.voice_dir.glob("*.onnx"))
        if not found:
            raise TTSUnavailable(f"{self.voice_dir} 에 .onnx 음성 모델이 없습니다.\n{HINT}")
        # 한국어 모델이 있으면 우선한다.
        ko = [p for p in found if p.name.lower().startswith("ko")]
        return (ko or found)[0]

    def voices(self) -> list[str]:
        return [p.name for p in sorted(self.voice_dir.glob("*.onnx"))]

    def synth_chunk(self, text: str, out_wav: str | Path) -> Path:
        out_wav = Path(out_wav)
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        # piper 의 length_scale 은 값이 클수록 느려진다.
        length_scale = 1.0 / max(0.1, self.speed)
        cmd = [
            *self.cmd,
            "--model", str(self.model),
            "--output_file", str(out_wav),
            "--length_scale", f"{length_scale:.3f}",
        ]
        proc = subprocess.run(
            cmd, input=text, capture_output=True, text=True, timeout=600
        )
        if proc.returncode != 0 or not out_wav.exists():
            raise TTSUnavailable(f"Piper 합성 실패:\n{proc.stderr[-500:]}")
        return out_wav
