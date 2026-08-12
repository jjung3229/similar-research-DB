"""설정 로딩.

폐쇄망을 고려해 PyYAML 이 없어도 동작한다.
  config.yaml (PyYAML 설치 시)  →  config.json  →  내장 기본값
순서로 찾는다.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - 폐쇄망에서 PyYAML 이 없을 수 있다
    yaml = None

DEFAULTS: dict[str, Any] = {
    "data_dir": "~/weekly_report_data",
    "user": {"name": "", "team": "", "email": ""},
    "activity": {
        "sample_seconds": 15,
        "idle_threshold_seconds": 180,
        "flush_seconds": 600,
        "min_session_seconds": 60,
        # 창 제목에 이 문자열이 들어가면 아예 기록하지 않는다.
        "ignore_titles": [],
    },
    "outlook": {
        "enabled": True,
        "include_sent": True,
        "include_received": True,
        "include_calendar": True,
        "max_body_chars": 700,
        # 받은 메일이 너무 많을 때: 이 도메인에서 온 것만 담는다. 비우면 전부.
        "received_from_domains": [],
    },
    "git": {"enabled": True, "repo_roots": [], "max_depth": 3},
    "files": {
        "enabled": True,
        "watch_dirs": [],
        "extensions": [
            ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls",
            ".hwp", ".hwpx", ".pdf",
            ".py", ".md", ".ipynb", ".sql", ".csv", ".txt",
        ],
        "ignore_dirs": [
            ".git", "node_modules", "__pycache__", ".venv", "venv",
            "AppData", "Temp", ".cache",
        ],
        "max_files": 200,
        "max_depth": 6,
    },
    "redact": {
        "enabled": True,
        # 이 단어가 들어간 기록은 통째로 버린다 (대외비 과제명 등).
        "drop_keywords": [],
        # 추가 정규식 → 마스킹
        "extra_patterns": [],
    },
    # 활동을 과제 단위로 묶는 규칙. 위에서부터 먼저 맞는 것으로 분류한다.
    "projects": [],
    "llm": {
        "enabled": False,
        "api_style": "openai",       # openai | custom
        "base_url": "",
        "model": "",
        "api_key_env": "",           # 키가 필요 없으면 비워둔다
        "timeout_seconds": 120,
        "bypass_proxy": True,        # 사내 주소는 프록시를 타지 않게
        "max_tokens": 4000,
        "verify_ssl": True,
        # api_style: custom 일 때만 사용
        "request_template": {},      # {{PROMPT}} 자리에 프롬프트가 들어간다
        "response_path": "choices.0.message.content",
        "headers": {},
    },
    "report": {
        "out_dir": "report",
        "template": "",              # 비우면 templates/weekly_ko.md
        "extra_instructions": "",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def find_config_path() -> Path | None:
    env = os.environ.get("WEEKLY_REPORT_CONFIG")
    if env:
        path = Path(env).expanduser()
        return path if path.exists() else None
    here = Path(__file__).resolve().parent
    for name in ("config.yaml", "config.yml", "config.json"):
        candidate = here / name
        if candidate.exists():
            return candidate
    return None


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg_path = Path(path).expanduser() if path else find_config_path()
    if cfg_path is None or not cfg_path.exists():
        return copy.deepcopy(DEFAULTS)

    text = cfg_path.read_text(encoding="utf-8")
    if cfg_path.suffix == ".json":
        user_cfg = json.loads(text) or {}
    elif yaml is not None:
        user_cfg = yaml.safe_load(text) or {}
    else:
        raise RuntimeError(
            f"{cfg_path.name} 을 읽으려면 PyYAML 이 필요합니다.\n"
            "설치가 어려우면 같은 내용을 config.json 으로 저장하세요."
        )
    merged = _deep_merge(DEFAULTS, user_cfg)
    merged["_config_path"] = str(cfg_path)
    return merged


def data_dir(cfg: dict) -> Path:
    path = Path(cfg["data_dir"]).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def report_dir(cfg: dict) -> Path:
    out = Path(cfg["report"]["out_dir"]).expanduser()
    if not out.is_absolute():
        out = data_dir(cfg) / out
    out.mkdir(parents=True, exist_ok=True)
    return out
