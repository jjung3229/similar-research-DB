"""로컬 웹 UI. 기본은 127.0.0.1 바인딩이라 외부에서 접근할 수 없다."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from .audio import AUDIO_EXTS, ffmpeg_path
from .config import Settings
from .jobs import JobManager
from .pipeline import PipelineOptions

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings):
    try:
        from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
    except ImportError as exc:  # pragma: no cover - 환경 의존
        raise RuntimeError(
            "웹 UI 에는 fastapi 가 필요합니다.\n  pip install fastapi uvicorn python-multipart"
        ) from exc

    settings.apply_env()
    settings.ensure_dirs()
    manager = JobManager(settings)

    app = FastAPI(title="VoiceBridge", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/api/health")
    def health() -> dict:
        from . import stt, tts
        from .minutes import llm

        llm_ok, llm_detail = (False, "미설정")
        if settings.llm_base_url:
            llm_ok, llm_detail = llm.health(settings.llm_base_url)
        return {
            "ok": True,
            "ffmpeg": bool(ffmpeg_path()),
            "stt": stt.available(settings),
            "tts": tts.available(settings),
            "llm": {"configured": bool(settings.llm_base_url),
                    "reachable": llm_ok, "detail": llm_detail},
            "settings": settings.to_dict(),
        }

    @app.post("/api/jobs")
    async def create_job(
        file: UploadFile = File(...),
        make_minutes: bool = Form(True),
        make_tts: bool = Form(False),
        drop_fillers: bool = Form(True),
        num_speakers: int = Form(0),
        title: str = Form(""),
    ) -> dict:
        name = Path(file.filename or "audio").name
        if Path(name).suffix.lower() not in AUDIO_EXTS:
            raise HTTPException(400, f"지원하지 않는 확장자입니다: {Path(name).suffix}")

        dst = Path(settings.uploads_dir) / f"{uuid.uuid4().hex[:8]}_{name}"
        dst.parent.mkdir(parents=True, exist_ok=True)
        limit = settings.max_upload_mb * 1024 * 1024
        written = 0
        with dst.open("wb") as fh:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > limit:
                    fh.close()
                    dst.unlink(missing_ok=True)
                    raise HTTPException(
                        413, f"파일이 너무 큽니다 (최대 {settings.max_upload_mb}MB)"
                    )
                fh.write(chunk)

        manager.purge_expired()
        options = PipelineOptions(
            make_minutes=make_minutes,
            make_tts=make_tts,
            drop_fillers=drop_fillers,
            num_speakers=num_speakers or None,
            title=title,
        )
        return manager.submit(dst, options).to_dict()

    @app.get("/api/jobs")
    def list_jobs() -> list[dict]:
        return [j.to_dict() for j in manager.list()]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = manager.get(job_id)
        if not job:
            raise HTTPException(404, "작업을 찾을 수 없습니다.")
        return job.to_dict()

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str) -> dict:
        return {"canceled": manager.cancel(job_id)}

    @app.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str) -> dict:
        return {"deleted": manager.delete(job_id)}

    @app.get("/api/jobs/{job_id}/file/{key}")
    def download(job_id: str, key: str):
        path = manager.file_path(job_id, key)
        if not path:
            raise HTTPException(404, "파일을 찾을 수 없습니다.")
        return FileResponse(path, filename=path.name,
                            media_type="application/octet-stream")

    @app.post("/api/tts")
    def synth(payload: dict = Body(...)):
        from . import tts

        text = (payload.get("text") or "").strip()
        if not text:
            raise HTTPException(400, "text 가 비어 있습니다.")
        out = Path(settings.outputs_dir) / "tts" / f"{uuid.uuid4().hex[:8]}.wav"
        try:
            tts.speak(settings, text, out)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(500, str(exc)) from exc
        return FileResponse(out, filename=out.name, media_type="audio/wav")

    @app.on_event("shutdown")
    def _shutdown() -> None:
        manager.shutdown()
        shutil.rmtree(settings.uploads_dir, ignore_errors=True)

    return app


def serve(settings: Settings) -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pip install uvicorn 이 필요합니다.") from exc

    app = create_app(settings)
    print(f"\n  VoiceBridge → http://{settings.host}:{settings.port}\n")
    if settings.host not in ("127.0.0.1", "localhost"):
        print("  ⚠ 로컬호스트 외부에 바인딩되었습니다. 사내망 노출 범위를 확인하세요.\n")
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
