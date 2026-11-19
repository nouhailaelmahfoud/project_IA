"""Analyse statique du code migré (Tâche 3).

Python : ruff (bloquant), pylint -E et mypy (avertissements).
PHP    : `php -l` (bloquant), PHPStan et Psalm (bloquants seulement pour les
         fonctions disparues, comme mysql_*, sinon avertissements).
"""
import re

from verification import runner

# Un message PHPStan qui prouve que le code plante sous PHP 8
PHP_BLOCKING = re.compile(r"undefined function|Function \S+ not found|Class \S+ not found"
                          r"|Syntax error", re.IGNORECASE)


def _lines(result, tool, limit=10):
    output = (result.stdout + "\n" + result.stderr).strip()
    return [f"{tool} : {line.strip()}" for line in output.splitlines()
            if line.strip() and not line.strip().startswith(("Found ", "*****"))][:limit]


def analyze(language: str, code: str, filename: str) -> dict:
    """Renvoie {"errors": [...bloquantes], "warnings": [...]}."""
    errors, warnings = [], []
    files = {filename: code}

    def run(command, timeout=120):
        return runner.run_in_docker(language, "modern", files, command,
                                    timeout=timeout, memory="512m")

    if language == "python":
        # Erreurs graves : syntaxe, noms non définis, constructions supprimées
        result = run(["ruff", "check", "--select", "E9,F63,F7,F82",
                      "--output-format", "concise", "--no-cache", filename])
        if not result.ok:
            errors += _lines(result, "ruff")
        result = run(["pylint", "-E", "--disable=import-error", filename])
        if not result.ok:
            warnings += _lines(result, "pylint")
        result = run(["mypy", "--ignore-missing-imports", "--no-error-summary",
                      "--cache-dir=/tmp/mypy", filename])
        if not result.ok:
            warnings += _lines(result, "mypy")
    else:
        result = run(["php", "-l", filename])
        if not result.ok:
            errors += _lines(result, "php -l")
        result = run(["phpstan", "analyse", "--level=0", "--no-progress",
                      "--memory-limit=512M", "--error-format=raw", filename])
        if not result.ok:
            for line in _lines(result, "phpstan"):
                (errors if PHP_BLOCKING.search(line) else warnings).append(line)
        
    return {"errors": errors, "warnings": warnings}