"""Moteur de vérification de la Tâche 3 : verify() contrôle un fichier migré.

Étapes :
  1. analyse statique du code migré (nouvel environnement) ;
  2. comportement : l'original (ancien environnement) et le migré (nouvel
     environnement) doivent produire la même sortie ;
  3. tests générés avant migration (facultatif) : ils doivent passer sur le migré.

Les erreurs renvoyées repartent au Migrateur (boucle de validation du pipeline).
"""
import time
from pathlib import Path

from verification import characterization as char
from verification import runner
from verification.static_analysis import analyze


def default_filename(language: str, file_path: str) -> str:
    name = Path(file_path).name
    if name and "." in name:
        return name
    return "code.py" if language == "python" else "code.php"


def verify(language: str, original: str, migrated: str, file_path: str = "code",
           tests: str = "") -> dict:
    """Renvoie {"errors": [...], "warnings": [...], "metrics": {...}}."""
    if not runner.docker_available():
        return {
            "errors": [],
            "warnings": ["Docker indisponible : tests non exécutés"],
            "metrics": {"skipped": True},
        }

    filename = default_filename(language, file_path)
    started = time.time()
    errors, warnings = [], []
    metrics = {"skipped": False}

    # 1. Analyse statique
    static = analyze(language, migrated, filename)
    errors += static["errors"]
    warnings += static["warnings"]
    metrics["static_errors"] = len(static["errors"])
    metrics["static_warnings"] = len(static["warnings"])

    if not static["errors"]:
        # 2. Comportement : original (legacy) contre migré (modern)
        golden = char.record_golden(language, filename, original)
        metrics["golden_usable"] = golden["usable"]
        if not golden["usable"]:
            warnings.append("Programme d'origine non exécutable seul : "
                            "comportement non comparé")
        behaviour = char.compare_with_golden(language, filename, migrated, golden)
        errors += behaviour
        metrics["behaviour_ok"] = None if not golden["usable"] else not behaviour

        # 3. Tests écrits avant la migration
        metrics["tests_run"] = bool(tests)
        if tests:
            result = char.run_tests(language, "modern", filename, migrated, tests)
            metrics["tests_passed"] = result.ok
            if not result.ok:
                errors.append("Tests de caractérisation en échec sur le code migré :\n"
                              + (result.stdout + result.stderr).strip()[-600:])
            if language == "python":
                metrics["coverage"] = char.parse_coverage(language, filename, result.stdout)
            else:
                metrics["coverage"] = char.php_coverage(filename, migrated, tests)

    metrics["duration_s"] = round(time.time() - started, 1)
    return {"errors": errors, "warnings": warnings, "metrics": metrics}


def prepare_tests(llm, language: str, file_path: str, original: str,
                  attempts: int = 2) -> dict:
    """À lancer AVANT la migration : le LLM écrit des tests, gardés seulement s'ils
    passent sur le code ORIGINAL (sinon c'est le test qui est faux)."""
    filename = default_filename(language, file_path)
    tests, feedback, log = "", "", []
    calls = tokens_in = tokens_out = 0
    for attempt in range(1, attempts + 1):
        candidate, t_in, t_out = char.generate_tests(llm, language, filename,
                                                     original, feedback)
        calls += 1
        tokens_in += t_in
        tokens_out += t_out
        if not candidate:
            feedback = "Ta réponse précédente ne contenait pas de fichier de test valide."
            log.append(f"tests (essai {attempt}) : réponse inutilisable")
            continue
        result = char.run_tests(language, "legacy", filename, original, candidate)
        if result.ok:
            tests = candidate
            log.append(f"tests (essai {attempt}) : validés sur le code original")
            break
        kept = char.keep_passing_tests(candidate, result.stdout + result.stderr, language)
        if kept:
            recheck = char.run_tests(language, "legacy", filename, original, kept)
            if recheck.ok:
                tests = kept
                log.append(f"tests (essai {attempt}) : tests faux retirés, "
                           "le reste est validé sur le code original")
                break
        feedback = ("Tes tests précédents échouent sur le code ORIGINAL, corrige-les :\n"
                    + (result.stdout + result.stderr).strip()[-800:])
        log.append(f"tests (essai {attempt}) : échec sur le code original")
    if not tests:
        log.append("tests : aucun jeu de tests valide, seul le comportement est comparé")
    return {"tests": tests, "log": log, "llm_calls": calls,
            "tokens_in": tokens_in, "tokens_out": tokens_out}