"""Tests de caractérisation (Tâche 3).

Idée : avant de migrer, on fige ce que fait le code ORIGINAL (dans son ancien
environnement : Python 2.7 ou PHP 7.4). Après la migration, on rejoue la même
chose sur le code migré (dans le nouvel environnement : Python 3.12 ou PHP 8.3)
et on compare.

Deux niveaux :
  1. « golden master » : la sortie du programme complet ;
  2. tests unitaires écrits par le LLM (pytest / PHPUnit), gardés seulement
     s'ils PASSENT sur l'original.
"""
import ast
import re
from pathlib import Path

from verification import runner


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def module_name(filename: str) -> str:
    return Path(filename).stem


# Différences purement cosmétiques entre Python 2 et Python 3 dans l'affichage :
# repr(300L) donne '300L' en Python 2 et '300' en Python 3 (le type long a disparu),
# repr(u'a') donne "u'a'" en Python 2 et "'a'" en Python 3.
PY2_LONG = re.compile(r"(?<![\w.])(\d+)L(?!\w)")
PY2_UNICODE = re.compile(r"(?<!\w)u(['\"])")


def python2_artifacts(text: str) -> str:
    """Retire de la sortie de Python 2 ce qui change à coup sûr en Python 3."""
    return PY2_UNICODE.sub(r"\1", PY2_LONG.sub(r"\1", text))


# ------------------------------------------------------------ 1. golden master

def record_golden(language: str, filename: str, original: str, timeout: int = 30) -> dict:
    """Exécute l'original (Python 2.7 / PHP 7.4) et mémorise son comportement."""
    result = runner.run_script(language, "legacy", filename, original, timeout)
    stdout = python2_artifacts(result.stdout) if language == "python" else result.stdout
    return {
        "stdout": normalize(stdout),
        "returncode": result.returncode,
        # False : programme non exécutable seul (base de données, locale...)
        "usable": result.ok,
        "stderr": result.stderr.strip()[-300:],
    }


def compare_with_golden(language: str, filename: str, migrated: str, golden: dict,
                        timeout: int = 30) -> list:
    """Exécute le code migré (Python 3.12 / PHP 8.3) et le compare à l'original."""
    if not golden["usable"]:
        return []  # pas de référence fiable : on ne bloque pas (signalé dans les métriques)
    result = runner.run_script(language, "modern", filename, migrated, timeout)
    if not result.ok:
        reason = "dépassement de temps" if result.timed_out else result.stderr.strip()[-300:]
        return [f"Le code migré ne s'exécute pas : {reason}"]
    got = normalize(result.stdout)
    if got != golden["stdout"]:
        return ["Comportement différent de l'original (même programme, mêmes entrées).\n"
                f"  original (avant migration) : {golden['stdout'][:300]!r}\n"
                f"  migré                      : {got[:300]!r}"]
    return []


# ----------------------------------------------- 2. tests unitaires générés (LLM)

def extract_test_code(text: str) -> str:
    """Récupère le fichier de test dans la réponse du modèle ('' si rien d'utilisable)."""
    from agents.llm_utils import extract_code_block
    block = extract_code_block(text)
    candidate = block if block is not None else text
    if "def test" in candidate or "function test" in candidate:
        return candidate.strip() + "\n"
    return ""

def fix_test_header(tests: str, module: str) -> str:
    """Corrige deux oublis fréquents des petits modèles : `from __future__` doit être
    la première instruction du fichier, et le module testé doit être importé."""
    lines = tests.splitlines()
    futures = list(dict.fromkeys(l for l in lines if l.strip().startswith("from __future__")))
    rest = [l for l in lines if not l.strip().startswith("from __future__")]
    body = "\n".join(rest).strip("\n")
    if not re.search(rf"^\s*(import {module}\b|from {module} import)", body, re.M):
        body = f"from {module} import *\n" + body
    header = futures or ["from __future__ import print_function"]
    return "\n".join(header) + "\n" + body + "\n"

def keep_php_tests(tests: str, report: str) -> str:
    """Version PHPUnit : retire les méthodes de test en échec ou en erreur."""
    failed = set(re.findall(r"^\d+\) \w+::(\w+)", report, re.M))
    if not failed:
        return ""
    for name in failed:
        match = re.search(rf"[ \t]*public function {name}\s*\(", tests)
        if not match:
            return ""
        depth, i = 0, tests.find("{", match.end())
        if i < 0:
            return ""
        while i < len(tests):
            if tests[i] == "{":
                depth += 1
            elif tests[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        tests = tests[:match.start()] + tests[i + 1:]
    if not re.search(r"function test\w*\(", tests):
        return ""
    return tests

def keep_passing_tests(tests: str, report: str, language: str = "python") -> str:
    if language == "php":
        return keep_php_tests(tests, report)
    """Retire les fonctions de test qui échouent sur l'original (leur valeur attendue
    est fausse) et garde les autres. Renvoie '' s'il ne reste aucun test."""
    failed = set(re.findall(r"^(?:FAILED|FAIL)\s+\S+::(\w+)", report, re.M))
    if not failed:
        return ""
    try:
        tree = ast.parse(tests)
    except SyntaxError:
        return ""
    tree.body = [node for node in tree.body
                 if not (isinstance(node, ast.FunctionDef) and node.name in failed)]
    if not any(isinstance(n, ast.FunctionDef) and n.name.startswith("test")
               for n in tree.body):
        return ""
    return ast.unparse(tree) + "\n"


def generate_tests(llm, language: str, filename: str, original: str, feedback: str = ""):
    """Demande au LLM des tests qui décrivent le comportement de l'ORIGINAL.
    Renvoie (code des tests, tokens entrée, tokens sortie)."""
    from agents.llm_utils import ask_llm
    from agents.prompt_loader import load_prompt
    folder = "tests/py2_to_3" if language == "python" else "tests/php7_to_8"
    prompt = load_prompt(folder, "test_writer", code=original, filename=filename,
                         module=module_name(filename), feedback=feedback)
    text, tokens_in, tokens_out = ask_llm(llm, prompt, "générateur de tests")
    tests = extract_test_code(text)
    if tests and language == "python":
        tests = fix_test_header(tests, module_name(filename))
    return tests, tokens_in, tokens_out


def run_tests(language: str, side: str, filename: str, code: str, tests: str,
              timeout: int = 90):
    """Lance les tests sur `code` dans l'environnement `side`. Renvoie un RunResult."""
    if language == "python":
        files = {filename: code, "test_generated.py": tests}
        command = ["python", "-m", "pytest", "-q", "-rf", "-p", "no:cacheprovider"]
        if side == "modern":
            command += [f"--cov={module_name(filename)}", "--cov-report=term"]
        command.append("test_generated.py")
    else:
        files = {f"src/{filename}": code, "GeneratedTest.php": tests}
        command = ["phpunit", "GeneratedTest.php"]
    return runner.run_in_docker(language, side, files, command, timeout=timeout)


def php_coverage(filename: str, code: str, tests: str):
    """Couverture PHP (pcov dans l'image PHP 8.3). Essai « au mieux » : None si échec."""
    result = runner.run_in_docker(
        "php", "modern", {f"src/{filename}": code, "GeneratedTest.php": tests},
        ["phpunit", "--coverage-text", "--coverage-filter=/work/src", "GeneratedTest.php"],
        timeout=90)
    return parse_coverage("php", filename, result.stdout)


def parse_coverage(language: str, filename: str, output: str):
    """Extrait le pourcentage de couverture de la sortie de pytest-cov ou PHPUnit."""
    if language == "php":
        match = re.search(r"Lines:\s+([\d.]+)%", output)
        return float(match.group(1)) if match else None
    wanted = module_name(filename) + ".py"
    total = None
    for line in output.splitlines():
        match = re.match(r"^(\S+)\s+\d+\s+\d+\s+(?:\d+\s+\d+\s+)?(\d+)%", line)
        if match:
            if match.group(1) == wanted:
                return int(match.group(2))
            if match.group(1) == "TOTAL":
                total = int(match.group(2))
    return total