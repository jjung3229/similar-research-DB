from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSUnavailable(RuntimeError):
    pass


class TTSEngine(ABC):
    name: str = "base"

    @abstractmethod
    def synth_chunk(self, text: str, out_wav: str | Path) -> Path:
        """텍스트 한 덩어리를 wav 하나로 합성."""

    def voices(self) -> list[str]:
        return []

    def close(self) -> None:  # pragma: no cover
        pass
