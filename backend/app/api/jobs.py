import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.core.config import SUPPORTED_LANGUAGES, WORKSPACE
from backend.app.schemas.jobs import JobCreated, JobStatus, MigrateRequest
from backend.app.services.github_service import parse_repo_url
from backend.app.services.job_store import get_job, save_job, update_job
from backend.app.services.migration_service import VALID_MODES
from backend.app.services.plugin_selector import detect_language
from backend.app.workers.tasks import analyze_job, migrate_job_task

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreated)
async def create_job(
    files: list[UploadFile] | None = File(None),
    language: str | None = Form(None),    # "php", "python" ou vide = auto
    repo_url: str | None = Form(None),    # https://github.com/proprietaire/depot
):
    uploads = [f for f in (files or []) if f.filename]
    repo_url = (repo_url or "").strip() or None
    if bool(uploads) == bool(repo_url):
        raise HTTPException(400, "Fournis soit des fichiers, soit repo_url.")

    lang = language.lower() if language and language != "string" else None
    if lang and lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, f"Langage non supporté : {lang}")

    try:
        if repo_url:
            parse_repo_url(repo_url)
            lang = lang or "auto"          # détecté après le clonage
        else:
            lang = lang or detect_language([f.filename for f in uploads])
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

    job_id = uuid.uuid4().hex[:12]
    job_dir = WORKSPACE / job_id
    job_dir.mkdir(parents=True)
    for upload in uploads:
        (job_dir / Path(upload.filename).name).write_bytes(await upload.read())

    save_job({"job_id": job_id, "language": lang, "status": "pending",
              "issues": [], "result": None, "error": None,
              "repo_url": repo_url, "pr_url": None})
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
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job introuvable")
    if request.mode not in VALID_MODES:
        raise HTTPException(400, f"Mode inconnu : {request.mode}")
    if request.create_pr and not job.get("repo_url"):
        raise HTTPException(400, "create_pr exige un job créé avec repo_url.")
    job = update_job(job_id, status="pending", error=None)
    migrate_job_task.delay(job_id, request.mode, request.provider,
                           request.model, request.max_iterations,
                           request.create_pr)
    if job.get("pr_url"):
        raise HTTPException(
            409, "Une Pull Request existe déjà pour ce job : "
            f"{job['pr_url']}. Crée un nouveau job pour relancer.")
    return job