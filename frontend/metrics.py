"""Calculs du tableau de bord : fonctions simples, sans Streamlit, faciles à tester."""
from pathlib import Path

# Hypothèses du calcul de temps gagné (modifiables dans l'interface)
MIN_PER_ISSUE_MANUAL = 10   # minutes pour corriger à la main un problème
MIN_REVIEW_PER_FILE = 3     # minutes pour relire un fichier migré automatiquement


def file_status(info: dict, mode: str = "") -> str:
    """Résume l'état d'un fichier migré en un mot."""
    if info["rolled_back"]:
        return "retour arrière"
    if info["errors"]:
        return "erreurs"
    if info["approved"]:
        return "ok"
    # rules_only : aucun relecteur n'est lancé, le fichier est seulement validé (syntaxe)
    return "validé (syntaxe), non relu" if mode == "rules_only" else "non approuvé"


def issues_for_file(issues: list, relative_path: str) -> list:
    """Problèmes de la Tâche 1 qui concernent ce fichier (comparaison par fin de chemin)."""
    name = Path(relative_path).as_posix()
    return [i for i in issues if Path(i.get("file_path", "")).as_posix().endswith(name)]


def fixed_issues(info: dict, status: str, found: int) -> int:
    """Problèmes réellement corrigés : détecteurs relancés avant/après la migration.

    Si cette mesure n'existe pas (analyse impossible), on retombe sur l'ancienne règle :
    tout est compté seulement si le fichier est approuvé.
    """
    before, after = info.get("issues_before"), info.get("issues_after")
    if before is not None and after is not None:
        if status in ("erreurs", "retour arrière"):
            return 0
        return max(before - after, 0)
    return found if status == "ok" else 0


def dashboard(job: dict, min_per_issue: float = MIN_PER_ISSUE_MANUAL,
              min_review: float = MIN_REVIEW_PER_FILE) -> dict:
    """Chiffres du tableau de bord à partir d'un job terminé."""
    files = (job.get("result") or {}).get("files", {})
    issues = job.get("issues", [])
    rows, fixed, remaining = [], 0, 0
    for name, info in files.items():
        status = file_status(info, (job.get("result") or {}).get("mode", ""))
        found = len(issues_for_file(issues, name))
        blocking = len(info["errors"])
        file_fixed = fixed_issues(info, status, found)
        fixed += file_fixed
        remaining += blocking
        left = info.get("issues_after")
        rows.append({"Fichier": name, "État": status, "Problèmes détectés": found,
                     "Problèmes corrigés": file_fixed,
                     "Problèmes restants": "?" if left is None else left,
                     "Erreurs restantes": blocking, "Itérations": info["iterations"],
                     "Appels LLM": info["llm_calls"]})
    manual = fixed * min_per_issue
    automated = len(files) * min_review
    return {
        "rows": rows,
        "files_total": len(files),
        "files_ok": sum(r["État"] == "ok" for r in rows),
        "issues_total": len(issues),
        "issues_fixed": fixed,
        "errors_remaining": remaining,
        "minutes_manual": manual,
        "minutes_saved": max(manual - automated, 0),
        "minutes_automated": automated,
    }