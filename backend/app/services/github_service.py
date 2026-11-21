"""Clone d'un dépôt GitHub, branche, push et Pull Request."""
import base64
import os
import re
import subprocess
from pathlib import Path

import requests

REPO_RE = re.compile(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def parse_repo_url(url: str) -> tuple[str, str]:
    match = REPO_RE.match(url.strip())
    if not match:
        raise ValueError(
            "URL invalide : format attendu https://github.com/proprietaire/depot")
    return match.group(1), match.group(2)


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or None


def _git(args: list[str], cwd=None, use_token: bool = False) -> str:
    token = _token() if use_token else None
    command = ["git"]
    if token:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        command += ["-c", f"http.extraheader=AUTHORIZATION: basic {basic}"]
    command += args
    result = subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, timeout=300,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    if result.returncode != 0:
        message = result.stderr.strip()
        if token:
            message = message.replace(token, "***")
        raise RuntimeError(f"git {args[0]} a échoué : {message}")
    return result.stdout


def clone_repo(url: str, destination: Path) -> str:
    """Clone le dépôt (copie légère) et renvoie sa branche par défaut."""
    parse_repo_url(url)
    _git(["clone", "--depth", "1", url, str(destination)], use_token=True)
    return _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=destination).strip()


def open_pull_request(job: dict, repo_dir: Path, result: dict) -> str:
    """Crée la branche, commite les fichiers migrés, pousse et ouvre la PR."""
    if not _token():
        raise RuntimeError("GITHUB_TOKEN absent : ajoute-le dans .env")
    owner, repo = parse_repo_url(job["repo_url"])
    base = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir).strip()
    branch = f"migration/{job['job_id']}"

    _git(["checkout", "-b", branch], cwd=repo_dir)
    _git(["add", "-A"], cwd=repo_dir)
    if not _git(["status", "--porcelain"], cwd=repo_dir).strip():
        raise ValueError("Aucun fichier modifié : pas de Pull Request créée.")
    _git(["-c", "user.name=Migration Agent",
          "-c", "user.email=migration-agent@users.noreply.github.com",
          "commit", "-m", f"Migration automatique ({job['language']})"],
         cwd=repo_dir)
    _git(["push", "origin", branch], cwd=repo_dir, use_token=True)

    files = result.get("files", {})
    done = [name for name, info in files.items() if info.get("written")]
    skipped = [name for name, info in files.items() if not info.get("written")]
    body = "Migration automatique.\n\n**Fichiers migrés :**\n"
    body += "\n".join(f"- `{name}`" for name in done) or "- aucun"
    if skipped:
        body += "\n\n**Non migrés (erreurs de validation) :**\n"
        body += "\n".join(f"- `{name}`" for name in skipped)

    response = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        headers={"Authorization": f"Bearer {_token()}",
                 "Accept": "application/vnd.github+json"},
        json={"title": f"Migration automatique ({job['language']})",
              "head": branch, "base": base, "body": body},
        timeout=30)
    if response.status_code != 201:
        raise RuntimeError(
            f"GitHub {response.status_code} : {response.json().get('message')}")
    return response.json()["html_url"]