"""faster-whisper(CTranslate2) 기반 로컬 STT.

모델 파일을 한 번 내려받아 model_dir 에 두면 이후 네트워크 없이 동작한다.
"""
from __future__ import annotations

from pathlib import Path

from ..config import Settings
from ..models import Segment, Transcript
from .base import EngineUnavailable, ProgressFn, STTEngine

INSTALL_HINT = (
    "faster-whisper 가 설치되어 있지 않습니다.\n"
    "  pip install faster-whisper\n"
    "GPU(NVIDIA)를 쓰려면 CUDA 12 + cuDNN 9 런타임이 함께 필요합니다."
)

# 한국어 인식 품질을 잡아주는 프롬프트. 문장부호와 존댓말 유지를 유도한다.
KO_PROMPT = "다음은 한국어 회의 녹음입니다. 문장부호를 포함해 정확하게 받아 적습니다."


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    try:
        import ctranslate2  # type: ignore

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


def resolve_compute_type(compute_type: str, device: str) -> str:
    if compute_type != "auto":
        return compute_type
    return "float16" if device == "cuda" else "int8"


class FasterWhisperEngine(STTEngine):
    name = "faster-whisper"

    def __init__(self, settings: Settings):
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - 환경 의존
            raise EngineUnavailable(INSTALL_HINT) from exc

        self.settings = settings
        self.device = resolve_device(settings.device)
        self.compute_type = resolve_compute_type(settings.compute_type, self.device)
        root = Path(settings.model_dir) / "whisper"
        root.mkdir(parents=True, exist_ok=True)

        try:
            self.model = WhisperModel(
                settings.stt_model,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(root),
                local_files_only=settings.offline,
            )
        except Exception as exc:  # pragma: no cover - 환경 의존
            if settings.offline:
                raise EngineUnavailable(
                    f"모델 '{settings.stt_model}' 을 로컬에서 찾지 못했습니다 ({root}).\n"
                    "인터넷 되는 PC 에서 `python -m app.cli prefetch` 로 받아 "
                    "vb-models 폴더째 옮기거나, VB_OFFLINE=0 으로 한 번만 실행하세요."
                ) from exc
            raise

    # ------------------------------------------------------------------
    def transcribe(self, wav_path: str | Path, progress: ProgressFn | None = None) -> Transcript:
        s = self.settings
        language = s.language or None

        segments_iter, info = self.model.transcribe(
            str(wav_path),
            language=language,
            beam_size=s.beam_size,
            vad_filter=s.vad_filter,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,  # 반복 환각 억제
            initial_prompt=KO_PROMPT if (language or "ko") == "ko" else None,
        )

        total = float(getattr(info, "duration", 0.0) or 0.0)
        segs: list[Segment] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if text:
                segs.append(Segment(start=float(seg.start), end=float(seg.end), text=text))
            if progress and total > 0:
                progress(min(0.99, float(seg.end) / total), f"전사 중 {int(seg.end)}s / {int(total)}s")

        if progress:
            progress(1.0, "전사 완료")

        return Transcript(
            segments=segs,
            language=getattr(info, "language", language),
            duration=total,
            source=str(wav_path),
            meta={
                "engine": self.name,
                "model": s.stt_model,
                "device": self.device,
                "compute_type": self.compute_type,
            },
        )

    # ------------------------------------------------------------------
    def transcribe_pcm(self, samples, offset: float = 0.0) -> list[Segment]:
        """실시간 모드용. float32 numpy 배열을 바로 받는다."""
        s = self.settings
        segments_iter, _ = self.model.transcribe(
            samples,
            language=s.language or None,
            beam_size=1,               # 실시간은 지연이 우선
            vad_filter=True,
            condition_on_previous_text=False,
        )
        out: list[Segment] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if text:
                out.append(Segment(offset + float(seg.start), offset + float(seg.end), text))
        return out
