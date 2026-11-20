import traceback
from backend.app.schemas.jobs import MigrateRequest
from backend.app.services.migration_service import migrate_job
import dataclasses
import uuid
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.core.config import SUPPORTED_LANGUAGES, WORKSPACE
from backend.app.schemas.jobs import JobCreated, JobStatus
from backend.app.services.job_store import JOBS
from backend.app.services.plugin_selector import detect_language, get_plugin

router = APIRouter(prefix="/jobs", tags=["jobs"])


def issue_to_dict(issue) -> dict:
    if isinstance(issue, dict):
        data = issue
    elif hasattr(issue, "model_dump"):
        data = issue.model_dump()
    elif dataclasses.is_dataclass(issue):
        data = dataclasses.asdict(issue)
    else:
        data = dict(vars(issue))
    return json.loads(json.dumps(data, default=str))


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

    JOBS[job_id] = {"job_id": job_id, "language": lang, "status": "running",
                    "issues": [], "result": None, "error": None}
    try:  # analyse synchrone pour l'instant ; elle ira dans Celery ensuite
        issues = get_plugin(lang).analyze_project(job_dir)
        JOBS[job_id]["issues"] = [issue_to_dict(i) for i in issues]
        JOBS[job_id]["status"] = "done"
    except Exception as error:
        JOBS[job_id].update(status="failed", error=str(error))
    return JobCreated(job_id=job_id, language=lang, status=JOBS[job_id]["status"])


@router.get("/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job introuvable")
    return JOBS[job_id]

@router.post("/{job_id}/migrate", response_model=JobStatus)
def migrate(job_id: str, request: MigrateRequest):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Job introuvable")
    job.update(status="running", error=None)
    try:  # synchrone pour l'instant ; ira dans Celery à l'étape suivante
        job["result"] = migrate_job(job, WORKSPACE / job_id, request.mode,
                                    request.provider, request.model,
                                    request.max_iterations)
        job["status"] = "done"
    except Exception as error:
        traceback.print_exc()
        job.update(status="failed", error=f"{type(error).__name__}: {error}")
    return job