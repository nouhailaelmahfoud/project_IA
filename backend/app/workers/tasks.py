import dataclasses
import json
import traceback

from backend.app.core.config import WORKSPACE
from backend.app.services.github_service import clone_repo, open_pull_request
from backend.app.services.job_store import get_job, update_job
from backend.app.services.migration_service import migrate_job
from backend.app.services.plugin_selector import detect_language, get_plugin
from backend.app.workers.celery_app import celery_app
from core.plugin_base import IGNORED_DIRECTORIES


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
        target = WORKSPACE / job_id
        if job.get("repo_url"):
            target = target / "repo"
            clone_repo(job["repo_url"], target)
            if job["language"] == "auto":
                names = [str(p) for p in target.rglob("*") if p.is_file()
                         and not IGNORED_DIRECTORIES.intersection(
                             p.relative_to(target).parts)]
                job = update_job(job_id, language=detect_language(names))
        issues = get_plugin(job["language"]).analyze_project(target)
        update_job(job_id, status="done", issues=[issue_to_dict(i) for i in issues])
    except Exception as error:
        traceback.print_exc()
        update_job(job_id, status="failed", error=f"{type(error).__name__}: {error}")


@celery_app.task(name="migrate_job")
def migrate_job_task(job_id: str, mode: str, provider: str, model,
                     max_iterations: int, create_pr: bool = False):
    job = get_job(job_id)
    update_job(job_id, status="running", error=None)
    try:
        job_dir = WORKSPACE / job_id
        result = migrate_job(job, job_dir, mode, provider, model, max_iterations)
        fields = {"result": result}
        if create_pr:
            fields["pr_url"] = open_pull_request(job, job_dir / "repo", result)
        update_job(job_id, status="done", **fields)
    except Exception as error:
        traceback.print_exc()
        update_job(job_id, status="failed", error=f"{type(error).__name__}: {error}")