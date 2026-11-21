"""Calculs du tableau de bord : fonctions simples, sans Streamlit, faciles à tester."""
from pathlib import Path

# Hypothèses du calcul de temps gagné (modifiables dans l'interface)
MIN_PER_ISSUE_MANUAL = 10   # minutes pour corriger à la main un problème
MIN_REVIEW_PER_FILE = 3     # minutes pour relire un fichier migré automatiquement


def file_status(info: dict) -> str:
    """Résume l'état d'un fichier migré en un mot."""
    if info["rolled_back"]:
        return "retour arrière"
    if info["errors"]:
        return "erreurs"
    return "ok" if info["approved"] else "non approuvé"


def issues_for_file(issues: list, relative_path: str) -> list:
    """Problèmes de la Tâche 1 qui concernent ce fichier (comparaison par fin de chemin)."""
    name = Path(relative_path).as_posix()
    return [i for i in issues if Path(i.get("file_path", "")).as_posix().endswith(name)]


def dashboard(job: dict, min_per_issue: float = MIN_PER_ISSUE_MANUAL,
              min_review: float = MIN_REVIEW_PER_FILE) -> dict:
    """Chiffres du tableau de bord à partir d'un job terminé."""
    files = (job.get("result") or {}).get("files", {})
    issues = job.get("issues", [])
    rows, fixed, remaining = [], 0, 0
    for name, info in files.items():
        status = file_status(info)
        found = len(issues_for_file(issues, name))
        blocking = len(info["errors"])
        ok = status == "ok"
        fixed += found if ok else 0
        remaining += blocking
        rows.append({"Fichier": name, "État": status, "Problèmes détectés": found,
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
        "minutes_automated": automated,
        "minutes_saved": max(manual - automated, 0),
    }
