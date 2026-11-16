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


def remove_redeclared_php_function(code: str, error: str):
    """Retire une définition globale dont PHP signale la redéclaration.

    Renvoie le code inchangé et None si le diagnostic ou la fonction est absent.
    """
    match = re.search(r"Cannot redeclare\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", error)
    if not match:
        return code, None

    name = match.group(1)
    declaration = re.search(
        rf"\bfunction\s*&?\s*{re.escape(name)}\s*\(", code, re.IGNORECASE)
    if not declaration:
        return code, None

    # Find the end of the parameter list while respecting quoted defaults.
    opening_paren = code.find("(", declaration.start(), declaration.end())
    depth, quote, escaped = 0, None, False
    close_paren = None
    for index in range(opening_paren, len(code)):
        char = code[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"', "`"):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                close_paren = index
                break
    if close_paren is None:
        return code, None

    body_start = code.find("{", close_paren)
    if body_start < 0:
        return code, None

    # Match the body braces, ignoring quoted strings and PHP comments.
    depth, quote, escaped, line_comment, block_comment = 1, None, False, False, False
    index = body_start + 1
    while index < len(code):
        char = code[index]
        next_char = code[index + 1] if index + 1 < len(code) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in ("'", '"', "`"):
            quote = char
        elif char == "/" and next_char == "/" or char == "#":
            line_comment = True
            if char == "/":
                index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                while end < len(code) and code[end] in " \t":
                    end += 1
                if end < len(code) and code[end] == "\n":
                    end += 1
                start = code.rfind("\n", 0, declaration.start()) + 1
                return code[:start] + code[end:], name
        index += 1
    return code, None


def apply_php_rules(source: str) -> RulesResult:
    """Convertit ce que Rector sait convertir (each, create_function, {}...)."""
    if not RECTOR.exists():
        return RulesResult(
            code=source, changed=False,
            warnings=["Rector n'est pas installé : règles PHP ignorées "
                      "(voir tools/rector)"])

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "code.php"
        path.write_text(source, encoding="utf-8")
        try:
            run = subprocess.run(
                ["php", str(RECTOR), "process", str(path),
                 "--config", str(RECTOR_CONFIG),
                 "--no-progress-bar", "--no-diffs", "--clear-cache"],
                capture_output=True, text=True, timeout=180, cwd=folder)
        except subprocess.TimeoutExpired:
            return RulesResult(source, False, ["Rector : délai dépassé, règles ignorées"])
        new_code = path.read_text(encoding="utf-8")

    warnings = []
    output = run.stdout + run.stderr
    if "[ERROR]" in output:
        warnings.append("Rector a signalé une erreur : " + " ".join(output.split())[:200])
    elif run.returncode not in (0, 2):
        warnings.append(f"Rector a échoué (code {run.returncode}) : "
                        + " ".join(output.split())[:200])
    return RulesResult(code=new_code, changed=new_code != source, warnings=warnings)


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
