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

from agents.graph import run_pipeline
from agents.llm import get_llm


def main():
    parser = argparse.ArgumentParser(description="Migration de code legacy")
    parser.add_argument("language", choices=["python"])
    parser.add_argument("file")
    parser.add_argument("--mode", default="hybrid",
                        choices=["hybrid", "rules_only", "llm_only"])
    parser.add_argument("--provider", default="ollama",
                        choices=["openrouter", "ollama"])
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-iterations", type=int, default=3)
    args = parser.parse_args()

    llm = None if args.mode == "rules_only" else get_llm(args.provider, args.model)

    issues = []
    if args.mode == "llm_only":
        from plugins.python_analyzer.python_plugin import PythonPlugin
        issues = [i.to_dict() for i in PythonPlugin().analyze_file(Path(args.file))]

    start = time.time()
    state = run_pipeline(args.file, args.language, args.mode, llm,
                         issues=issues, max_iterations=args.max_iterations)
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
    print(f"  durée              : {elapsed:.1f} s")
    print(f"  fichier migré      : {output}")


if __name__ == "__main__":
    main()
