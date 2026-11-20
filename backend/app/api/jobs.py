import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.core.config import SUPPORTED_LANGUAGES, WORKSPACE
from backend.app.schemas.jobs import JobCreated, JobStatus, MigrateRequest
from backend.app.services.job_store import get_job, save_job, update_job
from backend.app.services.migration_service import VALID_MODES
from backend.app.services.plugin_selector import detect_language
from backend.app.workers.tasks import analyze_job, migrate_job_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreated)
async def create_job(
    files: list[UploadFile] = File(...),
    language: Optional[str] = Form(None),   # "php", "python" ou vide = auto
):
    names = [f.filename for f in files]
    try:
        lang = language.lower() if language else detect_language(names)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Langage non supporté : {lang}")

    job_id = uuid.uuid4().hex[:12]
    job_dir = WORKSPACE / job_id
    job_dir.mkdir(parents=True)
    for upload in files:
        (job_dir / Path(upload.filename).name).write_bytes(await upload.read())

    save_job({"job_id": job_id, "language": lang, "status": "pending",
              "issues": [], "result": None, "error": None})
    analyze_job.delay(job_id)
    return JobCreated(job_id=job_id, language=lang, status="pending")


@router.get("/{job_id}", response_model=JobStatus)
def read_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job introuvable")
    return job


@router.post("/{job_id}/migrate", response_model=JobStatus)
def migrate(job_id: str, request: MigrateRequest):
    if get_job(job_id) is None:
        raise HTTPException(404, "Job introuvable")
    if request.mode not in VALID_MODES:
        raise HTTPException(400, f"Mode inconnu : {request.mode} ({', '.join(VALID_MODES)})")
    job = update_job(job_id, status="pending", error=None)
    migrate_job_task.delay(job_id, request.mode, request.provider,
                           request.model, request.max_iterations)
    return job