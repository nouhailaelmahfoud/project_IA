"""Compare les approches de migration sur le corpus (Python 2 ou PHP 7).

Exemples :
    python3 -m eval.run_benchmark --modes rules_only
    python3 -m eval.run_benchmark --modes hybrid --files bank --provider openrouter
    python3 -m eval.run_benchmark --language php --modes rules_only hybrid --provider openrouter
"""
import argparse
import ast
import csv
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

from agents import llm_utils
from agents.detectors import detect_python_risks
from agents.graph import run_pipeline
from agents.llm import get_llm
from agents.php_support import detect_php_risks, validate_php

CORPORA = {
    "python": {
        "inventory": "samples/py2_corpus/inventory/inventory.py",
        "textstats": "samples/py2_corpus/textstats/textstats.py",
        "bank": "samples/py2_corpus/bank/bank.py",
    },
    "php": {
        "shop": "samples/php7_corpus/shop/cart.php",
        "blog": "samples/php7_corpus/blog/blog.php",
        "legacy_db": "samples/php7_corpus/legacy_db/db.php",
    },
}

# nom affiché -> (mode du pipeline, détecteurs fixes utilisés ?)
MODES = {
    "rules_only": ("rules_only", True),
    "llm_only": ("llm_only", True),
    "hybrid": ("hybrid", True),
    "hybrid-sans-detecteurs": ("hybrid", False),
}

EXPECTED_DIR = Path("eval/expected")
COLUMNS = [
    "langage", "fichier", "mode", "syntaxe", "s_execute", "resultat_attendu",
    "pieges_bloquants", "retour_arriere", "non_verifie",
    "appels", "tokens_entree", "tokens_sortie", "duree_s", "erreur",
]


def expected_path(language, name):
    if language == "python":
        return EXPECTED_DIR / f"{name}.txt"
    return EXPECTED_DIR / language / f"{name}.txt"


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def execute(language: str, code: str, name: str, timeout: int = 20):
    """Exécute le code migré (corpus de test uniquement). Renvoie (ok, sortie)."""
    command = [sys.executable] if language == "python" else [
        "php", "-d", "display_errors=stderr"]
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / name
        path.write_text(code, encoding="utf-8")
        try:
            run = subprocess.run(command + [str(path)], capture_output=True,
                                 text=True, timeout=timeout, cwd=folder)
        except subprocess.TimeoutExpired:
            return False, ""
    return run.returncode == 0, run.stdout


def evaluate(language, name, display_mode, state, seconds):
    """Transforme l'état final du pipeline en une ligne de résultats."""
    code, original = state["current_code"], state["original_code"]
    path = CORPORA[language][name]

    if language == "python":
        try:
            ast.parse(code)
            syntax = True
        except SyntaxError:
            syntax = False
        blocking = [r for r in detect_python_risks(code, original) if r["blocking"]]
    else:
        syntax = validate_php(code) == []
        blocking = [r for r in detect_php_risks(code, original) if r["blocking"]]

    expected_file = expected_path(language, name)
    # Les programmes PHP du corpus ne sont exécutés que s'ils ont un résultat attendu
    # (certains ont besoin d'une base de données, d'autres d'une langue locale).
    runnable = language == "python" or expected_file.exists()
    if runnable and syntax:
        runs, output = execute(language, code, Path(path).name)
    else:
        runs, output = (False if runnable else None), ""

    if expected_file.exists():
        matches = bool(runs) and normalize(output) == normalize(
            expected_file.read_text(encoding="utf-8"))
    else:
        matches = None  # pas de résultat attendu connu pour ce fichier

    return {
        "langage": language, "fichier": name, "mode": display_mode,
        "syntaxe": syntax, "s_execute": runs, "resultat_attendu": matches,
        "pieges_bloquants": len(blocking),
        "retour_arriere": state["rolled_back"],
        "non_verifie": any("non vérifié" in line for line in state["log"]),
        "appels": state["llm_calls"],
        "tokens_entree": state["tokens_in"], "tokens_sortie": state["tokens_out"],
        "duree_s": round(seconds, 1), "erreur": "",
    }


def run_benchmark(files, modes, provider="ollama", model=None,
                  max_iterations=2, on_row=None, language="python"):
    rows = []
    llm = None
    total = len(files) * len(modes)
    for number, (name, mode_name) in enumerate(
            [(f, m) for f in files for m in modes], start=1):
        mode, use_detectors = MODES[mode_name]
        print(f"[{number}/{total}] {name} × {mode_name}", flush=True)
        path = CORPORA[language][name]
        started = time.time()
        try:
            if mode != "rules_only" and llm is None:
                llm = get_llm(provider, model)
            issues = []
            if mode == "llm_only":
                if language == "php":
                    from plugins.php_analyzer.php_plugin import PhpPlugin as Plugin
                else:
                    from plugins.python_analyzer.python_plugin import PythonPlugin as Plugin
                issues = [i.to_dict() for i in Plugin().analyze_file(Path(path))]
            state = run_pipeline(
                path, language, mode, None if mode == "rules_only" else llm,
                issues=issues, max_iterations=max_iterations,
                use_detectors=use_detectors)
            row = evaluate(language, name, mode_name, state, time.time() - started)
        except Exception as error:  # une panne réseau ne doit pas tout arrêter
            row = {column: "" for column in COLUMNS}
            row.update(langage=language, fichier=name, mode=mode_name,
                       erreur=str(error)[:120],
                       duree_s=round(time.time() - started, 1))
        rows.append(row)
        if on_row:
            on_row(row)
    return rows


def yes_no(value):
    if value is None or value == "":
        return "-"
    return "oui" if value is True else "non" if value is False else str(value)


def markdown_table(rows):
    header = ("| Fichier | Mode | Syntaxe | S'exécute | = attendu | Pièges bloquants "
              "| Retour arrière | Appels | Tokens (e/s) | Durée |")
    lines = [header, "|" + "---|" * 10]
    for r in rows:
        if r["erreur"]:
            lines.append(f"| {r['fichier']} | {r['mode']} | ERREUR : {r['erreur']} |"
                         + " |" * 7)
            continue
        flag = " (non vérifié)" if r["non_verifie"] else ""
        lines.append(
            f"| {r['fichier']} | {r['mode']}{flag} | {yes_no(r['syntaxe'])} "
            f"| {yes_no(r['s_execute'])} | {yes_no(r['resultat_attendu'])} "
            f"| {r['pieges_bloquants']} | {yes_no(r['retour_arriere'])} "
            f"| {r['appels']} | {r['tokens_entree']}/{r['tokens_sortie']} "
            f"| {r['duree_s']} s |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Comparatif des approches")
    parser.add_argument("--language", default="python", choices=list(CORPORA))
    parser.add_argument("--files", nargs="+", default=None,
                        help="fichiers du corpus (par défaut : tous)")
    parser.add_argument("--modes", nargs="+", default=["rules_only", "hybrid"],
                        choices=list(MODES))
    parser.add_argument("--provider", default="ollama", choices=["openrouter", "ollama"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-iterations", type=int, default=2)
    args = parser.parse_args()

    corpus = CORPORA[args.language]
    files = args.files or list(corpus)
    unknown = [f for f in files if f not in corpus]
    if unknown:
        raise SystemExit(f"Fichier(s) inconnu(s) pour {args.language} : {unknown}. "
                         f"Choix : {list(corpus)}")

    llm_utils.VERBOSE = True
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_path = results_dir / f"benchmark_{args.language}_{stamp}.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()

        def save_row(row):  # enregistré au fur et à mesure : rien n'est perdu
            writer.writerow(row)
            handle.flush()

        rows = run_benchmark(files, args.modes, args.provider, args.model,
                             args.max_iterations, on_row=save_row,
                             language=args.language)

    table = markdown_table(rows)
    md_path = results_dir / f"benchmark_{args.language}_{stamp}.md"
    md_path.write_text(
        f"# Comparatif {args.language} ({args.provider}, "
        f"{args.model or 'modèle par défaut'})\n\n{table}\n", encoding="utf-8")
    print("\n" + table)
    print(f"\nRésultats enregistrés : {md_path} et {csv_path}")


if __name__ == "__main__":
    main()
