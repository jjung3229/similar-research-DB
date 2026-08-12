"""실시간 녹취 입력 어댑터.

설계 의도:
  - 실시간 스트림은 '화면에 바로 보이는 초안' 용도다. 지연을 줄이려고
    beam_size=1 에 짧은 청크로 돌리므로 정확도가 파일 처리보다 낮다.
  - 그래서 원본 오디오를 통째로 wav 에 함께 기록한다. 회의가 끝나면
    그 wav 로 한 번 더 정식 전사를 돌려 최종본을 만든다(finalize).
  - 그 결과 실시간 모드도 결국 같은 pipeline/minutes 로직을 그대로 탄다.
"""
from __future__ import annotations

import queue
import threading
import time
import wave
from pathlib import Path
from typing import Callable

from .config import Settings
from .models import Segment, Transcript

SAMPLE_RATE = 16000
BLOCK_SEC = 0.5

HINT = (
    "실시간 녹취에는 sounddevice 와 numpy 가 필요합니다.\n"
    "  pip install sounddevice numpy\n"
    "Linux 는 libportaudio2 도 필요합니다: sudo apt install libportaudio2"
)


class LiveUnavailable(RuntimeError):
    pass


def list_devices() -> list[dict]:
    try:
        import sounddevice as sd  # type: ignore
    except ImportError as exc:
        raise LiveUnavailable(HINT) from exc
    out = []
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) > 0:
            out.append({
                "index": i,
                "name": d.get("name", "?"),
                "channels": d.get("max_input_channels"),
                "default_samplerate": d.get("default_samplerate"),
            })
    return out


class LiveSession:
    """마이크 → 실시간 초안 텍스트 + 원본 wav 동시 기록."""

    def __init__(
        self,
        settings: Settings,
        out_wav: str | Path,
        *,
        device: int | None = None,
        window_sec: float = 6.0,
        on_text: Callable[[Segment], None] | None = None,
    ):
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore
        except ImportError as exc:
            raise LiveUnavailable(HINT) from exc

        self._np = np
        self._sd = sd
        self.settings = settings
        self.out_wav = Path(out_wav)
        self.out_wav.parent.mkdir(parents=True, exist_ok=True)
        self.device = device
        self.window_sec = window_sec
        self.on_text = on_text

        self.segments: list[Segment] = []
        self._q: queue.Queue = queue.Queue()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._stream = None
        self._wav: wave.Wave_write | None = None
        self._t0 = 0.0
        self._elapsed = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def _callback(self, indata, _frames, _time_info, status):  # pragma: no cover - 하드웨어 의존
        if status:
            pass  # 오버플로는 무시하고 계속 간다
        self._q.put(bytes(indata))

    def _run(self) -> None:  # pragma: no cover - 하드웨어 의존
        from .stt.faster_whisper_engine import FasterWhisperEngine

        engine = FasterWhisperEngine(self.settings)
        buf = b""
        window_bytes = int(SAMPLE_RATE * self.window_sec) * 2  # int16

        # 원본 wav 기록은 오디오 콜백에서 이미 하고 있다. 여기서는 인식만 한다.
        while not self._stop.is_set() or not self._q.empty():
            try:
                buf += self._q.get(timeout=0.2)
            except queue.Empty:
                if self._stop.is_set():
                    break
                continue

            while len(buf) >= window_bytes:
                block, buf = buf[:window_bytes], buf[window_bytes:]
                self._emit(engine, block)

        if buf:
            self._emit(engine, buf)

    def _emit(self, engine, pcm: bytes) -> None:  # pragma: no cover - 하드웨어 의존
        np = self._np
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        offset = self._elapsed
        self._elapsed += len(samples) / SAMPLE_RATE
        try:
            new = engine.transcribe_pcm(samples, offset=offset)
        except Exception:  # noqa: BLE001 - 실시간은 한 블록 실패해도 계속 간다
            return
        with self._lock:
            self.segments.extend(new)
        if self.on_text:
            for seg in new:
                self.on_text(seg)

    # ------------------------------------------------------------------
    def start(self) -> None:  # pragma: no cover - 하드웨어 의존
        self._wav = wave.open(str(self.out_wav), "wb")
        self._wav.setnchannels(1)
        self._wav.setsampwidth(2)
        self._wav.setframerate(SAMPLE_RATE)

        def cb(indata, frames, time_info, status):
            raw = bytes(indata)
            if self._wav is not None:
                self._wav.writeframes(raw)   # 원본은 손실 없이 그대로 저장
            self._q.put(raw)

        self._stream = self._sd.RawInputStream(
            samplerate=SAMPLE_RATE, blocksize=int(SAMPLE_RATE * BLOCK_SEC),
            device=self.device, dtype="int16", channels=1, callback=cb,
        )
        self._stream.start()
        self._t0 = time.time()
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def stop(self) -> Transcript:  # pragma: no cover - 하드웨어 의존
        self._stop.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._worker is not None:
            self._worker.join(timeout=120)
            self._worker = None
        if self._wav is not None:
            self._wav.close()
            self._wav = None

        with self._lock:
            segs = list(self.segments)
        return Transcript(
            segments=segs,
            language=self.settings.language,
            duration=time.time() - self._t0 if self._t0 else self._elapsed,
            source=self.out_wav.name,
            meta={"mode": "live", "draft": True},
        )

    # ------------------------------------------------------------------
    def finalize(self, progress=None) -> Transcript:  # pragma: no cover - 하드웨어 의존
        """녹음된 wav 로 정식 전사를 다시 돌려 최종본을 만든다."""
        from .pipeline import transcribe_file

        return transcribe_file(self.settings, self.out_wav, progress=progress)
