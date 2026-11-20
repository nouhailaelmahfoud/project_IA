import dataclasses
import json
import traceback

from backend.app.core.config import WORKSPACE
from backend.app.services.job_store import get_job, update_job
from backend.app.services.migration_service import migrate_job
from backend.app.services.plugin_selector import get_plugin
from backend.app.workers.celery_app import celery_app


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


@celery_app.task(name="analyze_job")
def analyze_job(job_id: str):
    job = get_job(job_id)
    update_job(job_id, status="running")
    try:
        issues = get_plugin(job["language"]).analyze_project(WORKSPACE / job_id)
        update_job(job_id, status="done", issues=[issue_to_dict(i) for i in issues])
    except Exception as error:
        traceback.print_exc()
        update_job(job_id, status="failed", error=f"{type(error).__name__}: {error}")


@celery_app.task(name="migrate_job")
def migrate_job_task(job_id: str, mode: str, provider: str, model, max_iterations: int):
    job = get_job(job_id)
    update_job(job_id, status="running", error=None)
    try:
        result = migrate_job(job, WORKSPACE / job_id, mode, provider, model, max_iterations)
        update_job(job_id, status="done", result=result)
    except Exception as error:
        traceback.print_exc()
        update_job(job_id, status="failed", error=f"{type(error).__name__}: {error}")