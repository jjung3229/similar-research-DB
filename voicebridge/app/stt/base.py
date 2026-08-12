from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from ..models import Transcript

ProgressFn = Callable[[float, str], None]


class EngineUnavailable(RuntimeError):
    """엔진 의존 패키지/모델이 준비되지 않았을 때."""


class STTEngine(ABC):
    name: str = "base"

    @abstractmethod
    def transcribe(
        self,
        wav_path: str | Path,
        progress: ProgressFn | None = None,
    ) -> Transcript:
        ...

    def close(self) -> None:  # pragma: no cover - 엔진별 선택 구현
        pass
