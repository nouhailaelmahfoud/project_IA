"""Appelle le pipeline d'agents (Tâche 2) sur les fichiers d'un job."""
import ast
import json
import tempfile
from pathlib import Path

from backend.app.core.config import EXTENSIONS
from backend.app.services.plugin_selector import get_plugin
from core.plugin_base import IGNORED_DIRECTORIES

VALID_MODES = ("rules_only", "hybrid", "llm_only")
MAX_FILES = 50


# Éléments de Python 2 supprimés en Python 3 : s'ils restent dans le code migré, ils plantent
PY2_NAMES = {"xrange", "raw_input", "unicode", "long", "basestring"}
PY2_ATTRIBUTES = {"has_key", "iteritems", "itervalues", "iterkeys"}


def python2_leftovers(code: str):
    """Nombre de constructions Python 2 qui restent dans du code censé être en Python 3.

    On ne relance pas le détecteur de la Tâche 1 ici : il repose sur 2to3, qui signale encore
    du Python 3 correct (ex. print("a", b) ou input()). On lit donc le code comme du Python 3 :
    syntaxe invalide => None (inconnu), sinon on compte les noms supprimés encore utilisés.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    return sum(
        (isinstance(node, ast.Name) and node.id in PY2_NAMES)
        or (isinstance(node, ast.Attribute) and node.attr in PY2_ATTRIBUTES)
        for node in ast.walk(tree))


def count_issues(plugin, language: str, extension: str, original: str, migrated: str):
    """Problèmes avant et après la migration : (avant, après), None si inconnu.

    Avant : détecteurs de la Tâche 1 sur le code original.
    Après : Python = constructions Python 2 restantes ; autres langages = détecteurs relancés.
    """
    if plugin is None:
        return None, None
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"check{extension}"

        def detect(code: str):
            path.write_text(code, encoding="utf-8")
            try:
                return len(plugin.analyze_file(path))
            except Exception:  # noqa: BLE001 - une analyse ratée ne doit pas faire échouer la migration
                return None

        before = detect(original)
        after = python2_leftovers(migrated) if language == "python" else detect(migrated)
    return before, after


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

    try:
        plugin = get_plugin(language)
    except Exception:  # noqa: BLE001
        plugin = None

    files = {}
    for source in sources:
        relative = source.relative_to(root)
        issues = [i for i in job["issues"]
                  if Path(i.get("file_path", "")) == source]
        # Lu avant le pipeline : dans un dépôt, le fichier est ensuite écrasé
        original_code = source.read_text(encoding="utf-8")
        state = run_pipeline(source, language, mode, llm, issues=issues,
                             max_iterations=max_iterations, verify=verify)
        # Mesure réelle : problèmes avant / après la migration
        issues_before, issues_after = count_issues(
            plugin, language, extension, original_code, state["current_code"])
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
            "issues_before": issues_before,
            "issues_after": issues_after,
            "original_code": original_code,
            "migrated_code": state["current_code"],
        }
    return json.loads(json.dumps({"mode": mode, "files": files}, default=str))