"""백그라운드 작업 큐. 웹 UI 가 업로드 후 진행률을 폴링하는 데 쓴다."""
from __future__ import annotations

import shutil
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .pipeline import PipelineOptions, run_file

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_ERROR = "error"
STATUS_CANCELED = "canceled"


@dataclass
class Job:
    id: str
    filename: str
    status: str = STATUS_QUEUED
    progress: float = 0.0
    message: str = "대기 중"
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    preview: str = ""
    minutes_md: str = ""
    duration: float = 0.0
    speakers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "progress": round(self.progress, 4),
            "message": self.message,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "elapsed": round((self.finished_at or time.time()) - self.created_at, 1),
            "error": self.error,
            "warnings": self.warnings,
            "files": sorted(self.files.keys()),
            "preview": self.preview,
            "minutes_md": self.minutes_md,
            "duration": self.duration,
            "speakers": self.speakers,
        }


class JobManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(
            max_workers=max(1, settings.max_workers), thread_name_prefix="vb-job"
        )
        self._canceled: set[str] = set()

    # ------------------------------------------------------------------
    def submit(self, src: Path, options: PipelineOptions) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], filename=src.name)
        with self._lock:
            self._jobs[job.id] = job
        self._pool.submit(self._run, job, src, options)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def cancel(self, job_id: str) -> bool:
        """아직 시작 전이면 취소한다. 실행 중이면 다음 진행률 보고에서 멈춘다."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status in (STATUS_DONE, STATUS_ERROR, STATUS_CANCELED):
                return False
            self._canceled.add(job_id)
            return True

    def out_dir(self, job_id: str) -> Path:
        return Path(self.settings.outputs_dir) / job_id

    def file_path(self, job_id: str, key: str) -> Path | None:
        job = self.get(job_id)
        if not job:
            return None
        raw = job.files.get(key)
        if not raw:
            return None
        path = Path(raw).resolve()
        # 경로 이탈 방지: 반드시 해당 작업 폴더 안이어야 한다.
        root = self.out_dir(job_id).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return None
        return path if path.is_file() else None

    def delete(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.pop(job_id, None)
            self._canceled.discard(job_id)
        if not job:
            return False
        shutil.rmtree(self.out_dir(job_id), ignore_errors=True)
        return True

    def purge_expired(self) -> int:
        hours = self.settings.retention_hours
        if hours <= 0:
            return 0
        cutoff = time.time() - hours * 3600
        stale = [j.id for j in self.list() if j.created_at < cutoff]
        for jid in stale:
            self.delete(jid)
        return len(stale)

    # ------------------------------------------------------------------
    def _run(self, job: Job, src: Path, options: PipelineOptions) -> None:
        class Canceled(Exception):
            pass

        def progress(pct: float, msg: str) -> None:
            if job.id in self._canceled:
                raise Canceled()
            job.progress = pct
            job.message = msg

        job.status = STATUS_RUNNING
        job.message = "시작"
        out = self.out_dir(job.id)
        try:
            result = run_file(self.settings, src, out, options, progress=progress)
            job.files = {k: str(v) for k, v in result.files.items()}
            job.warnings = result.warnings
            job.duration = result.transcript.duration
            job.speakers = result.transcript.speakers
            job.preview = result.transcript.text[:2000]
            if result.minutes is not None:
                job.minutes_md = result.minutes.to_markdown()
            job.status = STATUS_DONE
            job.progress = 1.0
            job.message = "완료"
        except Canceled:
            job.status = STATUS_CANCELED
            job.message = "취소됨"
            shutil.rmtree(out, ignore_errors=True)
        except Exception as exc:  # noqa: BLE001 - 어떤 실패든 UI 로 보여준다
            job.status = STATUS_ERROR
            job.error = f"{type(exc).__name__}: {exc}"
            job.message = "실패"
            traceback.print_exc()
        finally:
            job.finished_at = time.time()
            self._canceled.discard(job.id)
            # 업로드 원본은 처리 후 즉시 삭제 (디스크에 음성이 남지 않게)
            try:
                src.unlink(missing_ok=True)
            except OSError:
                pass

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
