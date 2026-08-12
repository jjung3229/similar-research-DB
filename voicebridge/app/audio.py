"""오디오 입출력 유틸. ffmpeg 의존은 여기서만 쓴다."""
from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
import wave
from pathlib import Path

AUDIO_EXTS = {
    ".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus",
    ".wma", ".amr", ".3gp", ".mp4", ".mov", ".mkv", ".avi", ".webm",
}


class AudioError(RuntimeError):
    pass


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def ffprobe_path() -> str | None:
    return shutil.which("ffprobe")


def require_ffmpeg() -> str:
    p = ffmpeg_path()
    if not p:
        raise AudioError(
            "ffmpeg 를 찾을 수 없습니다.\n"
            "  Windows : winget install Gyan.FFmpeg  (또는 ffmpeg.exe 를 PATH 에 추가)\n"
            "  macOS   : brew install ffmpeg\n"
            "  Ubuntu  : sudo apt install ffmpeg"
        )
    return p


def probe_duration(path: str | Path) -> float:
    """미디어 길이(초). ffprobe 가 없으면 wav 헤더로라도 재본다."""
    path = Path(path)
    probe = ffprobe_path()
    if probe:
        try:
            out = subprocess.run(
                [probe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "json", str(path)],
                capture_output=True, text=True, timeout=60, check=True,
            ).stdout
            return float(json.loads(out)["format"]["duration"])
        except (subprocess.SubprocessError, KeyError, ValueError, json.JSONDecodeError):
            pass
    if path.suffix.lower() == ".wav":
        with contextlib.suppress(wave.Error, OSError, EOFError):
            with wave.open(str(path), "rb") as w:
                return w.getnframes() / float(w.getframerate() or 1)
    return 0.0


def to_wav16k(src: str | Path, dst: str | Path) -> Path:
    """어떤 포맷이든 16kHz 모노 PCM wav 로 변환한다. STT 입력 표준 포맷."""
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        require_ffmpeg(), "-nostdin", "-y", "-i", str(src),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dst.exists():
        tail = "\n".join(proc.stderr.strip().splitlines()[-8:])
        raise AudioError(f"오디오 변환 실패: {src.name}\n{tail}")
    return dst


def wav_params(path: str | Path) -> tuple[int, int, int]:
    """(채널수, 샘플폭, 샘플레이트)"""
    with wave.open(str(path), "rb") as w:
        return w.getnchannels(), w.getsampwidth(), w.getframerate()


def silence_frames(params: tuple[int, int, int], ms: int) -> bytes:
    channels, width, rate = params
    return b"\x00" * int(rate * ms / 1000) * channels * width


def concat_wavs(parts: list[str | Path], dst: str | Path, gap_ms: int = 0) -> Path:
    """같은 파라미터의 wav 들을 이어붙인다. ffmpeg 없이 표준 라이브러리만 사용."""
    parts = [Path(p) for p in parts if Path(p).exists()]
    if not parts:
        raise AudioError("이어붙일 wav 조각이 없습니다.")
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    base = wav_params(parts[0])
    gap = silence_frames(base, gap_ms) if gap_ms > 0 else b""

    with wave.open(str(dst), "wb") as out:
        out.setnchannels(base[0])
        out.setsampwidth(base[1])
        out.setframerate(base[2])
        for i, part in enumerate(parts):
            if wav_params(part) != base:
                raise AudioError(
                    f"wav 파라미터가 서로 다릅니다: {part.name} "
                    f"({wav_params(part)} != {base})"
                )
            with wave.open(str(part), "rb") as w:
                out.writeframes(w.readframes(w.getnframes()))
            if gap and i < len(parts) - 1:
                out.writeframes(gap)
    return dst


def wav_to_mp3(src: str | Path, dst: str | Path, bitrate: str = "128k") -> Path:
    src, dst = Path(src), Path(dst)
    cmd = [require_ffmpeg(), "-nostdin", "-y", "-i", str(src), "-b:a", bitrate, str(dst)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AudioError(f"mp3 변환 실패:\n{proc.stderr[-500:]}")
    return dst


def write_wav(path: str | Path, pcm: bytes, rate: int = 16000,
              channels: int = 1, width: int = 2) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(pcm)
    return path
