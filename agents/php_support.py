"""Support de PHP : règles (Rector), détecteurs fixes et validation (php -l)."""
import os
import re
import subprocess
import tempfile
from pathlib import Path

from agents.rules_engine import RulesResult

ROOT = Path(__file__).resolve().parent.parent
RECTOR = Path(os.environ.get(
    "RECTOR_BIN", ROOT / "tools" / "rector" / "vendor" / "bin" / "rector"))
RECTOR_CONFIG = ROOT / "tools" / "rector" / "rector.php"


def _matching_end(code: str, body_start: int):
    """Position juste après l'accolade fermante qui correspond à celle de body_start."""
    depth, quote, escaped = 1, None, False
    line_comment = block_comment = False
    index = body_start + 1
    while index < len(code):
        char = code[index]
        following = code[index + 1] if index + 1 < len(code) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        elif char == "#" or (char == "/" and following == "/"):
            line_comment = True
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return None


def remove_toplevel_function(code: str, name: str):
    """Retire la déclaration d'une fonction globale (jamais une méthode).

    Seules les déclarations en début de ligne sont retirées. Renvoie
    (nouveau_code, True), ou (code inchangé, False) si rien n'a été retiré.
    """
    declaration = re.search(
        rf"^function\s*&?\s*{re.escape(name)}\s*\(", code,
        re.IGNORECASE | re.MULTILINE)
    if not declaration:
        return code, False
    body_start = code.find("{", declaration.end())
    if body_start < 0:
        return code, False
    end = _matching_end(code, body_start)
    if end is None:
        return code, False
    while end < len(code) and code[end] in " \t":
        end += 1
    if end < len(code) and code[end] == "\n":
        end += 1
    return code[:declaration.start()] + code[end:], True


def remove_native_redeclarations(code: str):
    """Règle : une fonction du programme qui existe déjà en natif en PHP 8
    (str_contains, array_key_last...) doit être retirée : PHP 8 la refuse.

    Renvoie (nouveau_code, noms_retirés).
    """
    removed = []
    for _ in range(10):
        errors = validate_php(code)
        if not errors:
            break
        # « previously declared » = doublon dans le programme : on n'y touche pas
        match = re.search(
            r"Cannot redeclare ([A-Za-z_][A-Za-z0-9_]*)\(\)(?! \(previously)",
            errors[0])
        if not match:
            break
        code, done = remove_toplevel_function(code, match.group(1))
        if not done:
            break
        removed.append(match.group(1))
    return code, removed


def apply_php_rules(source: str) -> RulesResult:
    """Règles automatiques : Rector (each, create_function, {}...) puis la règle
    « fonction déjà native »."""
    code, warnings = source, []

    if RECTOR.exists():
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "code.php"
            path.write_text(source, encoding="utf-8")
            try:
                run = subprocess.run(
                    ["php", str(RECTOR), "process", str(path),
                     "--config", str(RECTOR_CONFIG),
                     "--no-progress-bar", "--no-diffs", "--clear-cache"],
                    capture_output=True, text=True, timeout=180, cwd=folder)
                code = path.read_text(encoding="utf-8")
                output = run.stdout + run.stderr
                if "[ERROR]" in output:
                    warnings.append("Rector a signalé une erreur : "
                                    + " ".join(output.split())[:200])
                elif run.returncode not in (0, 2):
                    warnings.append(f"Rector a échoué (code {run.returncode}) : "
                                    + " ".join(output.split())[:200])
            except subprocess.TimeoutExpired:
                warnings.append("Rector : délai dépassé, règles ignorées")
    else:
        warnings.append("Rector n'est pas installé : règles PHP ignorées "
                        "(voir tools/rector)")

    code, removed = remove_native_redeclarations(code)
    for name in removed:
        warnings.append(f"règle : fonction {name}() supprimée "
                        "(elle existe déjà en natif en PHP 8)")
    return RulesResult(code=code, changed=code != source, warnings=warnings)


def detect_php_risks(code: str, original: str = None) -> list:
    """Pièges PHP 7 -> 8 repérés par le plugin d'analyse de la Tâche 1."""
    from plugins.php_analyzer.php_plugin import PhpPlugin

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "code.php"
        path.write_text(code, encoding="utf-8")
        try:
            issues = PhpPlugin().analyze_file(path)
        except RuntimeError as error:
            raise RuntimeError(
                "Les détecteurs PHP ne fonctionnent pas : "
                f"{str(error)[:300]} (as-tu fait « composer install » dans "
                "plugins/php_analyzer ?)") from error

    risks = []
    for issue in issues:
        if issue.rule_id == "PHP_PARSE_ERROR":
            continue  # la validation (php -l) s'en charge
        risks.append({
            "kind": issue.rule_id,
            "line": issue.line,
            "code": issue.code_snippet or "",
            "description": issue.message,
            "suggestion": issue.recommendation,
            "blocking": issue.severity in ("critical", "high"),
        })
    return risks


def validate_php(code: str) -> list:
    """Vérifie le code avec « php -l » (syntaxe et erreurs de compilation)."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "code.php"
        path.write_text(code, encoding="utf-8")
        run = subprocess.run(
            ["php", "-d", "display_errors=1", "-d", "log_errors=0",
             "-d", "error_reporting=-1", "-l", str(path)],
            capture_output=True, text=True)

    if run.returncode == 0:
        return []
    lines = [line.strip() for line in (run.stdout + run.stderr).splitlines()
             if line.strip() and not line.startswith("Errors parsing")]
    # Les avis « Deprecated » passent après les vraies erreurs
    fatal = [line for line in lines if line.startswith(("Fatal error", "Parse error"))]
    message = (fatal or lines or ["erreur de syntaxe inconnue"])[0]
    return [message.replace(str(path), "code.php")[:300]]
