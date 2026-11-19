"""Migre un fichier avec le pipeline d'agents.

Exemples :
    python3 run_agents.py python samples/py2_corpus/bank/bank.py --mode rules_only
    python3 run_agents.py python samples/py2_corpus/bank/bank.py --mode hybrid --provider ollama
    python3 run_agents.py python samples/py2_corpus/bank/bank.py --mode hybrid --provider openrouter
"""
import argparse
import difflib
import time
from pathlib import Path

from agents import llm_utils
from agents.graph import run_pipeline
from agents.llm import get_llm


def main():
    parser = argparse.ArgumentParser(description="Migration de code legacy")
    parser.add_argument("language", choices=["python", "php"])
    parser.add_argument("file")
    parser.add_argument("--mode", default="hybrid",
                        choices=["hybrid", "rules_only", "llm_only"])
    parser.add_argument("--provider", default="ollama",
                        choices=["openrouter", "ollama"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument("--llm-analyzer", action="store_true",
                        help="le LLM analyse aussi le code (en plus des détecteurs)")
    parser.add_argument("--no-detectors", action="store_true",
                        help="désactive les détecteurs fixes (pour le comparatif)")
    parser.add_argument("--verify", action="store_true",
                        help="Tâche 3 : analyse statique et comparaison dans Docker")
    parser.add_argument("--generate-tests", action="store_true",
                        help="avec --verify : le LLM écrit des tests avant la migration")
    args = parser.parse_args()

    llm_utils.VERBOSE = True
    print(f"Migration de {args.file} (mode {args.mode}, moteur {args.provider})...",
          flush=True)
    llm = None if args.mode == "rules_only" else get_llm(args.provider, args.model)

    issues = []
    if args.mode == "llm_only":
        if args.language == "php":
            from plugins.php_analyzer.php_plugin import PhpPlugin as Plugin
        else:
            from plugins.python_analyzer.python_plugin import PythonPlugin as Plugin
        issues = [i.to_dict() for i in Plugin().analyze_file(Path(args.file))]

    # Tâche 3 : tests de caractérisation écrits AVANT la migration
    tests = ""
    if args.verify and args.generate_tests:
        if llm is None:
            print("--generate-tests ignoré : le mode rules_only n'utilise pas de modèle")
        else:
            from verification.engine import prepare_tests
            prepared = prepare_tests(llm, args.language, args.file,
                                     Path(args.file).read_text(encoding="utf-8"))
            tests = prepared["tests"]
            for line in prepared["log"]:
                print(" ", line)

    start = time.time()
    state = run_pipeline(args.file, args.language, args.mode, llm,
                         issues=issues, max_iterations=args.max_iterations,
                         llm_analyzer=args.llm_analyzer,
                         use_detectors=not args.no_detectors,
                         verify=args.verify, tests=tests)
    elapsed = time.time() - start

    output = Path("output") / args.mode / Path(args.file).name
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(state["current_code"], encoding="utf-8")

    print("--- Journal")
    for line in state["log"]:
        print(" ", line)

    print("\n--- Changements")
    diff = difflib.unified_diff(
        state["original_code"].splitlines(), state["current_code"].splitlines(),
        "original", "migré", lineterm="", n=0)
    for line in diff:
        print(" ", line)

    print("\n--- Bilan")
    print(f"  mode               : {args.mode}")
    print(f"  appels au modèle   : {state['llm_calls']}")
    print(f"  tokens (entrée/sortie) : {state['tokens_in']} / {state['tokens_out']}")
    print(f"  tours du Migrateur : {state['iteration']}")
    print(f"  validation         : {'OK' if not state['errors'] else state['errors']}")
    if state["rolled_back"]:
        print("  ATTENTION          : modifications du modèle rejetées, "
              "code d'avant le Migrateur conservé")
    if any("non vérifié" in line for line in state["log"]):
        print("  ATTENTION          : relecture du Reviewer illisible, code validé "
              "seulement par les contrôles fixes (à relire)")
    if args.verify:
        details = state["verification"]
        metrics = details.get("metrics", {})
        if metrics.get("skipped"):
            print("  ATTENTION          : Docker indisponible, tests NON exécutés")
        else:
            print(f"  comportement       : {metrics.get('behaviour_ok')}")
            print(f"  tests écrits       : {'oui' if tests else 'non'} "
                  f"(réussis : {metrics.get('tests_passed')}, "
                  f"couverture : {metrics.get('coverage')})")
            print(f"  erreurs statiques  : {metrics.get('static_errors')}")
        for warning in details.get("warnings", [])[:5]:
            print(f"  avertissement      : {warning[:150]}")
        from verification.metrics import record_from_state, save_report
        json_path, _ = save_report([record_from_state(state)])
        print(f"  rapport            : {json_path}")
    print(f"  durée              : {elapsed:.1f} s")
    print(f"  fichier migré      : {output}")


if __name__ == "__main__":
    main()
