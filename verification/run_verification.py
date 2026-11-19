"""Commandes de la Tâche 3.

    python3 -m verification.run_verification build-images
    python3 -m verification.run_verification check python original.py migre.py
    python3 -m verification.run_verification regenerate-expected --dry-run
    python3 -m verification.run_verification regenerate-expected
"""
import argparse
import json
import sys
from pathlib import Path

from verification import characterization as char
from verification import runner
from verification.engine import verify

ROOT = Path(__file__).resolve().parent.parent

# langage -> (dossier du corpus, extension, dossier des sorties attendues)
CORPORA = {
    "python": (ROOT / "samples" / "py2_corpus", ".py", ROOT / "eval" / "expected"),
    "php": (ROOT / "samples" / "php7_corpus", ".php", ROOT / "eval" / "expected" / "php"),
}


def cmd_build_images(_args):
    for (language, side) in runner.ENVIRONMENTS:
        runner.build_image(language, side)
    print("Images prêtes :", ", ".join(name for name, _ in runner.ENVIRONMENTS.values()))
    return 0


def cmd_check(args):
    result = verify(args.language, Path(args.original).read_text(encoding="utf-8"),
                    Path(args.migrated).read_text(encoding="utf-8"), args.migrated,
                    Path(args.tests).read_text(encoding="utf-8") if args.tests else "")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["errors"] else 0


def cmd_regenerate_expected(args):
    """Exécute chaque programme d'ORIGINE dans son ancien environnement (Python 2.7,
    PHP 7.4) et enregistre sa vraie sortie dans eval/expected/."""
    if not runner.docker_available():
        print("Docker ne répond pas : lance Docker puis réessaie.")
        return 2
    languages = list(CORPORA) if args.language == "all" else [args.language]
    for language in languages:
        corpus, extension, expected_dir = CORPORA[language]
        for project in sorted(p for p in corpus.iterdir() if p.is_dir()):
            sources = sorted(project.glob(f"*{extension}"))
            if not sources:
                continue
            source = sources[0]
            golden = char.record_golden(language, source.name,
                                        source.read_text(encoding="utf-8"))
            target = expected_dir / f"{project.name}.txt"
            if not golden["usable"]:
                print(f"[{language}] {project.name} : non exécutable seul "
                      f"({golden['stderr'][:80]!r}) -> ignoré")
                continue
            old = char.normalize(target.read_text(encoding="utf-8")) if target.exists() else None
            status = ("nouveau" if old is None else
                      "identique" if old == golden["stdout"] else "DIFFÉRENT de l'ancien")
            print(f"[{language}] {project.name} : {status}")
            if not args.dry_run and status != "identique":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(golden["stdout"] + "\n", encoding="utf-8")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Moteur de vérification (Tâche 3)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build-images", help="construit les 4 images Docker")

    check = sub.add_parser("check", help="vérifie un fichier migré")
    check.add_argument("language", choices=["python", "php"])
    check.add_argument("original")
    check.add_argument("migrated")
    check.add_argument("--tests", default=None, help="fichier de tests de caractérisation")

    regen = sub.add_parser("regenerate-expected",
                           help="refait eval/expected/ avec Python 2.7 / PHP 7.4")
    regen.add_argument("--language", default="all", choices=["all", "python", "php"])
    regen.add_argument("--dry-run", action="store_true", help="n'écrit rien")

    args = parser.parse_args()
    handlers = {"build-images": cmd_build_images, "check": cmd_check,
                "regenerate-expected": cmd_regenerate_expected}
    sys.exit(handlers[args.command](args))


if __name__ == "__main__":
    main()