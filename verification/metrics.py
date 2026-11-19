"""Métriques de la Tâche 3 : taux de réussite, couverture, nombre d'itérations."""
import json
from datetime import datetime
from pathlib import Path


def record_from_state(state: dict) -> dict:
    """Transforme l'état final du pipeline en une ligne de métriques."""
    verification = state.get("verification") or {}
    metrics = verification.get("metrics", {})
    return {
        "fichier": Path(state["file_path"]).name,
        "langage": state["language"],
        "mode": state["mode"],
        "reussi": not state["errors"],
        "iterations": state["iteration"],
        "retour_arriere": state["rolled_back"],
        "verification_ignoree": bool(metrics.get("skipped", not verification)),
        "comportement_identique": metrics.get("behaviour_ok"),
        "tests_ecrits": metrics.get("tests_run", False),
        "tests_reussis": metrics.get("tests_passed"),
        "couverture": metrics.get("coverage"),
        "erreurs_statiques": metrics.get("static_errors", 0),
        "avertissements": len(verification.get("warnings", [])),
        "duree_verification_s": metrics.get("duration_s"),
    }


def summarize(records: list) -> dict:
    """Résumé global d'une liste de lignes de métriques."""
    total = len(records)
    if total == 0:
        return {"fichiers": 0}
    coverages = [r["couverture"] for r in records if r.get("couverture") is not None]
    return {
        "fichiers": total,
        "reussis": sum(1 for r in records if r["reussi"]),
        "taux_reussite_pct": round(100 * sum(1 for r in records if r["reussi"]) / total, 1),
        "iterations_moyennes": round(sum(r["iterations"] for r in records) / total, 2),
        "couverture_moyenne_pct": round(sum(coverages) / len(coverages), 1) if coverages else None,
        "retours_arriere": sum(1 for r in records if r["retour_arriere"]),
        "verifications_ignorees": sum(1 for r in records if r["verification_ignoree"]),
        "avertissements": sum(r["avertissements"] for r in records),
    }


def save_report(records: list, folder="eval/results", stamp: str = None):
    """Écrit verification_<date>.json et .md. Renvoie (chemin json, chemin md)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = summarize(records)

    json_path = folder / f"verification_{stamp}.json"
    json_path.write_text(
        json.dumps({"resume": summary, "fichiers": records}, indent=2,
                   ensure_ascii=False), encoding="utf-8")

    def cell(value):
        return "-" if value is None else ("oui" if value is True else
                                          "non" if value is False else str(value))

    lines = ["# Rapport de vérification (Tâche 3)", "",
             f"- Fichiers : {summary['fichiers']}",
             f"- Taux de réussite : {summary.get('taux_reussite_pct', '-')} %",
             f"- Itérations moyennes : {summary.get('iterations_moyennes', '-')}",
             f"- Couverture moyenne : {cell(summary.get('couverture_moyenne_pct'))} %", "",
             "| Fichier | Mode | Réussi | Itérations | Même comportement | Tests OK "
             "| Couverture | Erreurs statiques | Retour arrière |",
             "|" + "---|" * 9]
    for r in records:
        lines.append(
            f"| {r['fichier']} | {r['mode']} | {cell(r['reussi'])} | {r['iterations']} "
            f"| {cell(r['comportement_identique'])} | {cell(r['tests_reussis'])} "
            f"| {cell(r['couverture'])} | {r['erreurs_statiques']} "
            f"| {cell(r['retour_arriere'])} |")
    md_path = folder / f"verification_{stamp}.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path