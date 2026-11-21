"""Petit client HTTP pour l'API FastAPI (backend/)."""
import os
import time

import requests

API_URL = os.environ.get("API_URL", "http://localhost:8000")
TIMEOUT = 30


def _check(response: requests.Response) -> dict:
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"API {response.status_code} : {detail}")
    return response.json()


def create_job(files=None, repo_url=None, language=None) -> dict:
    data = {"language": language} if language else {}
    if repo_url:
        data["repo_url"] = repo_url
    upload = [("files", (f.name, f.getvalue())) for f in (files or [])]
    return _check(requests.post(f"{API_URL}/jobs", data=data, files=upload, timeout=TIMEOUT))


def get_job(job_id: str) -> dict:
    return _check(requests.get(f"{API_URL}/jobs/{job_id}", timeout=TIMEOUT))


def start_migration(job_id: str, mode: str, provider: str, model, max_iterations: int,
                    create_pr: bool = False) -> dict:
    body = {"mode": mode, "provider": provider, "model": model or None,
            "max_iterations": max_iterations, "create_pr": create_pr}
    return _check(requests.post(f"{API_URL}/jobs/{job_id}/migrate", json=body, timeout=TIMEOUT))


def wait_for_job(job_id: str, every: float = 2.0, timeout: float = 1800) -> dict:
    """Interroge l'API jusqu'à ce que le job soit terminé (done ou failed)."""
    start = time.time()
    time.sleep(0.5)                       # laisse le temps au worker de prendre le job
    while time.time() - start < timeout:
        job = get_job(job_id)
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(every)
    raise TimeoutError("Le job met trop de temps.")
