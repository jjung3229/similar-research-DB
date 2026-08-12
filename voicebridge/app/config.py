"""실행 설정. 환경변수 > config.json > 기본값 순으로 적용된다."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

# 오프라인 모드에서 각 라이브러리가 원격 호출을 시도하지 않도록 미리 막아둔다.
# import 시점에 세팅해야 huggingface_hub 등이 값을 읽는다.
_OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_HUB_DISABLE_TELEMETRY": "1",
    "DO_NOT_TRACK": "1",
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    # --- 경로 ---
    work_dir: Path = Path("./vb-data")
    model_dir: Path = Path("./vb-models")

    # --- STT ---
    stt_engine: str = "faster-whisper"
    stt_model: str = "large-v3"       # 저사양이면 small / medium 권장
    device: str = "auto"              # auto | cpu | cuda
    compute_type: str = "auto"        # auto | int8 | int8_float16 | float16 | float32
    language: str = "ko"              # None 이면 자동 감지
    beam_size: int = 5
    vad_filter: bool = True

    # --- 화자 분리 ---
    diarize_engine: str = "none"      # none | pyannote
    hf_token: str = ""                # pyannote 최초 1회 다운로드에만 사용

    # --- 회의록 ---
    minutes_backend: str = "auto"     # auto | llm | rules | none
    llm_base_url: str = ""            # 예: http://localhost:11434/v1
    llm_model: str = ""               # 예: qwen3:14b
    llm_api_key: str = ""
    llm_timeout: int = 300
    llm_chunk_chars: int = 6000

    # --- TTS (선택) ---
    tts_engine: str = "piper"         # piper | melo | system
    tts_voice: str = ""               # 엔진별 음성 식별자(비우면 엔진 기본값)
    tts_speed: float = 1.0
    tts_chunk_chars: int = 220        # 한 번에 합성할 최대 글자 수
    tts_gap_ms: int = 180             # 청크 사이 무음 길이

    # --- 서버 ---
    host: str = "127.0.0.1"
    port: int = 7860
    max_upload_mb: int = 1024
    retention_hours: int = 24         # 작업 결과 자동 삭제 시간 (0=삭제 안 함)
    max_workers: int = 1

    # --- 보안 ---
    offline: bool = True              # True면 모든 원격 호출 차단

    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, config_path: str | os.PathLike | None = None) -> "Settings":
        data: dict = {}
        path = Path(config_path) if config_path else Path("vb-config.json")
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))

        s = cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
        s.work_dir = Path(os.environ.get("VB_WORK_DIR", data.get("work_dir", s.work_dir)))
        s.model_dir = Path(os.environ.get("VB_MODEL_DIR", data.get("model_dir", s.model_dir)))
        s.stt_engine = os.environ.get("VB_STT_ENGINE", s.stt_engine)
        s.stt_model = os.environ.get("VB_STT_MODEL", s.stt_model)
        s.device = os.environ.get("VB_DEVICE", s.device)
        s.compute_type = os.environ.get("VB_COMPUTE_TYPE", s.compute_type)
        s.language = os.environ.get("VB_LANGUAGE", s.language)
        s.diarize_engine = os.environ.get("VB_DIARIZE_ENGINE", s.diarize_engine)
        s.hf_token = os.environ.get("VB_HF_TOKEN", s.hf_token)
        s.minutes_backend = os.environ.get("VB_MINUTES_BACKEND", s.minutes_backend)
        s.llm_base_url = os.environ.get("VB_LLM_BASE_URL", s.llm_base_url)
        s.llm_model = os.environ.get("VB_LLM_MODEL", s.llm_model)
        s.llm_api_key = os.environ.get("VB_LLM_API_KEY", s.llm_api_key)
        s.llm_timeout = _env_int("VB_LLM_TIMEOUT", s.llm_timeout)
        s.tts_engine = os.environ.get("VB_TTS_ENGINE", s.tts_engine)
        s.tts_voice = os.environ.get("VB_TTS_VOICE", s.tts_voice)
        s.host = os.environ.get("VB_HOST", s.host)
        s.port = _env_int("VB_PORT", s.port)
        s.retention_hours = _env_int("VB_RETENTION_HOURS", s.retention_hours)
        s.max_workers = _env_int("VB_MAX_WORKERS", s.max_workers)
        s.offline = _env_bool("VB_OFFLINE", s.offline)
        return s

    # ------------------------------------------------------------------
    def apply_env(self) -> None:
        """오프라인 모드일 때 프로세스 환경변수를 잠근다."""
        os.environ.setdefault("HF_HOME", str(self.model_dir / "hf"))
        os.environ.setdefault("XDG_CACHE_HOME", str(self.model_dir / "cache"))
        if self.offline:
            for k, v in _OFFLINE_ENV.items():
                os.environ[k] = v
        else:
            for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
                os.environ.pop(k, None)

    def ensure_dirs(self) -> None:
        for p in (self.work_dir, self.model_dir, self.uploads_dir, self.outputs_dir):
            p.mkdir(parents=True, exist_ok=True)

    @property
    def uploads_dir(self) -> Path:
        return self.work_dir / "uploads"

    @property
    def outputs_dir(self) -> Path:
        return self.work_dir / "outputs"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["work_dir"] = str(self.work_dir)
        d["model_dir"] = str(self.model_dir)
        d.pop("hf_token", None)  # 토큰은 절대 응답에 싣지 않는다
        d.pop("llm_api_key", None)
        return d
