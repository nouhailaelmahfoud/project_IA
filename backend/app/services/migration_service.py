"""Appelle le pipeline d'agents (Tâche 2) sur les fichiers d'un job."""
import json
from pathlib import Path

from backend.app.core.config import EXTENSIONS
from core.plugin_base import IGNORED_DIRECTORIES

VALID_MODES = ("rules_only", "hybrid", "llm_only")
MAX_FILES = 50


def migrate_job(job: dict, job_dir: Path, mode: str, provider: str,
                model, max_iterations: int, verify: bool = False) -> dict:
    # Imports ici : l'API démarre même si les dépendances des agents manquent
    from agents.graph import run_pipeline
    from agents.llm import get_llm

    if mode not in VALID_MODES:
        raise ValueError(f"Mode inconnu : {mode} ({', '.join(VALID_MODES)})")

    language = job["language"]
    llm = None if mode == "rules_only" else get_llm(provider, model)
    extension = next(e for e, lang in EXTENSIONS.items() if lang == language)

    repo_dir = job_dir / "repo"
    in_repo = repo_dir.is_dir()
    if in_repo:
        root = out_root = repo_dir
        sources = [p for p in sorted(root.rglob(f"*{extension}"))
                   if not IGNORED_DIRECTORIES.intersection(
                       p.relative_to(root).parts)]
    else:
        root = job_dir
        out_root = job_dir / "migrated"
        out_root.mkdir(exist_ok=True)
        sources = sorted(root.glob(f"*{extension}"))

    if not sources:
        raise ValueError(f"Aucun fichier {extension} à migrer dans ce job.")
    if len(sources) > MAX_FILES:
        raise ValueError(f"Trop de fichiers ({len(sources)} > {MAX_FILES}).")

    files = {}
    for source in sources:
        relative = source.relative_to(root)
        issues = [i for i in job["issues"]
                  if Path(i.get("file_path", "")) == source]
        # Lu avant le pipeline : dans un dépôt, le fichier est ensuite écrasé
        original_code = source.read_text(encoding="utf-8")
        state = run_pipeline(source, language, mode, llm, issues=issues,
                             max_iterations=max_iterations, verify=verify)
        # Dans un dépôt, on n'écrit que le code qui passe la validation
        written = not (in_repo and state["errors"])
        if written:
            target = out_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(state["current_code"], encoding="utf-8")
        files[relative.as_posix()] = {
            "written": written,
            "approved": state["approved"],
            "rolled_back": state["rolled_back"],
            "errors": state["errors"],
            "iterations": state["iteration"],
            "llm_calls": state["llm_calls"],
            "tokens_in": state["tokens_in"],
            "tokens_out": state["tokens_out"],
            "log": state["log"],
            "verification": state["verification"],
            "original_code": original_code,
            "migrated_code": state["current_code"],
        }
    return json.loads(json.dumps({"mode": mode, "files": files}, default=str))