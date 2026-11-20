"""Appelle le pipeline d'agents (Tâche 2) sur les fichiers d'un job."""
import json
from pathlib import Path

from backend.app.core.config import EXTENSIONS

VALID_MODES = ("rules_only", "hybrid", "llm_only")


def migrate_job(job: dict, job_dir: Path, mode: str, provider: str,
                model, max_iterations: int) -> dict:
    # Imports ici : l'API démarre même si les dépendances des agents manquent
    from agents.graph import run_pipeline
    from agents.llm import get_llm

    if mode not in VALID_MODES:
        raise ValueError(f"Mode inconnu : {mode} ({', '.join(VALID_MODES)})")

    language = job["language"]
    llm = None if mode == "rules_only" else get_llm(provider, model)
    extension = next(e for e, lang in EXTENSIONS.items() if lang == language)

    out_dir = job_dir / "migrated"
    out_dir.mkdir(exist_ok=True)

    files = {}
    for source in sorted(job_dir.glob(f"*{extension}")):
        issues = [i for i in job["issues"]
                  if Path(i.get("file_path", "")).name == source.name]
        state = run_pipeline(source, language, mode, llm, issues=issues,
                             max_iterations=max_iterations)
        (out_dir / source.name).write_text(state["current_code"], encoding="utf-8")
        files[source.name] = {
            "approved": state["approved"],
            "rolled_back": state["rolled_back"],
            "errors": state["errors"],
            "iterations": state["iteration"],
            "llm_calls": state["llm_calls"],
            "tokens_in": state["tokens_in"],
            "tokens_out": state["tokens_out"],
            "log": state["log"],
            "migrated_code": state["current_code"],
        }
    if not files:
        raise ValueError(f"Aucun fichier {extension} à migrer dans ce job.")
    return json.loads(json.dumps({"mode": mode, "files": files}, default=str))