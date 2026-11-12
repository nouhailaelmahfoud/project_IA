import difflib
import warnings
from pathlib import Path

from core.models import Issue
from core.plugin_base import LanguagePlugin

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from lib2to3 import refactor


# Règles connues : nom de la règle 2to3 -> (gravité, message, recommandation)
KNOWN_RULES = {
    "print": ("critical", "Instruction print de Python 2",
              "Utiliser la fonction print()"),
    "except": ("critical", "Syntaxe except X, e de Python 2",
               "Écrire except X as e"),
    "raise": ("critical", "Syntaxe raise de Python 2",
              "Utiliser raise Exception(...)"),
    "exec": ("critical", "Instruction exec de Python 2",
             "Utiliser la fonction exec()"),
    "ne": ("critical", "Opérateur <> supprimé en Python 3",
           "Remplacer <> par !="),
    "repr": ("critical", "Backticks supprimés en Python 3",
             "Utiliser repr()"),
    "xrange": ("high", "xrange n'existe plus en Python 3",
               "Remplacer xrange par range"),
    "unicode": ("high", "Le type unicode n'existe plus en Python 3",
                "Utiliser str"),
    "has_key": ("high", "dict.has_key() supprimé en Python 3",
                "Utiliser l'opérateur in"),
    "long": ("high", "Le type long n'existe plus en Python 3",
             "Utiliser int"),
    "basestring": ("high", "basestring n'existe plus en Python 3",
                   "Utiliser str"),
    "raw_input": ("high", "raw_input n'existe plus en Python 3",
                  "Utiliser input()"),
    "input": ("high", "input() de Python 2 évaluait la saisie",
              "Utiliser input() de Python 3 (ou eval(input()) si voulu)"),
    "iteritems": ("warning", "iteritems/itervalues/iterkeys supprimés",
                  "Utiliser items(), values() ou keys()"),
    "import": ("warning", "Import implicite relatif de Python 2",
               "Utiliser un import absolu ou relatif explicite"),
    "imports": ("warning", "Module renommé en Python 3",
                "Utiliser le nouveau nom du module"),
    "urllib": ("warning", "Module urllib réorganisé en Python 3",
               "Utiliser urllib.request / urllib.parse"),
    "dict": ("warning", "dict.keys()/values()/items() renvoient des vues",
             "Entourer de list() si une liste est nécessaire"),
    "map": ("warning", "map() renvoie un itérateur en Python 3",
            "Entourer de list() si une liste est nécessaire"),
    "filter": ("warning", "filter() renvoie un itérateur en Python 3",
               "Entourer de list() si une liste est nécessaire"),
    "zip": ("warning", "zip() renvoie un itérateur en Python 3",
            "Entourer de list() si une liste est nécessaire"),
}


# Règles de 2to3 qui ne signalent pas un vrai problème
IGNORED_RULES = {"future"}


def changed_line_offsets(before: str, after: str) -> list:
    """Numéros de lignes (à partir de 0) modifiées entre deux versions."""
    old, new = before.splitlines(), after.splitlines()
    offsets = []
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, _, _ in matcher.get_opcodes():
        if tag == "equal":
            continue
        last = min(max(i2, i1 + 1), len(old))
        offsets.extend(range(i1, last) if old else [0])
    return offsets or [0]


class PythonPlugin(LanguagePlugin):
    """Détecte les constructions Python 2 grâce aux règles de lib2to3."""

    name = "python_analyzer"
    file_extensions = (".py",)

    def __init__(self):
        fixer_names = refactor.get_fixers_from_package("lib2to3.fixes")
        self.tool = refactor.RefactoringTool(fixer_names)
        self.fixers = self.tool.pre_order + self.tool.post_order

    def analyze_file(self, file_path: Path) -> list[Issue]:
        file_path = Path(file_path)
        source = file_path.read_text(encoding="utf-8", errors="replace")
        if not source.endswith("\n"):
            source += "\n"
        lines = source.splitlines()

        # Si le fichier est illisible, on le signale au lieu de planter
        try:
            self.tool.driver.parse_string(source)
        except Exception as error:
            return [Issue(
                file_path=str(file_path), line=1, plugin=self.name,
                rule_id="PY_PARSE_ERROR", severity="warning",
                message=f"Fichier non analysable : {error}",
                recommendation="Vérifier la syntaxe du fichier",
            )]

        issues = []
        seen = set()

        for fixer in self.fixers:
            fixer_name = fixer.__class__.__module__.split("fix_")[-1]
            if fixer_name in IGNORED_RULES:
                continue

            # Un arbre neuf par règle : les règles ne se perturbent pas
            fresh_tree = self.tool.driver.parse_string(source)
            fresh_tree.future_features = frozenset()
            try:
                fixer.start_tree(fresh_tree, str(file_path))
            except Exception:
                continue

            for node in list(fresh_tree.pre_order()):
                try:
                    results = fixer.match(node)
                    if not results:
                        continue
                    before = str(node)
                    first_line = node.get_lineno() - node.prefix.count("\n")
                    new = fixer.transform(node, results)
                    after = str(new) if new is not None else str(node)
                except Exception:
                    continue

                if after == before:
                    continue  # la règle ne change rien : faux positif

                for offset in changed_line_offsets(before, after):
                    line = first_line + offset
                    key = (fixer_name, line)
                    if key in seen:
                        continue
                    seen.add(key)

                    severity, message, recommendation = KNOWN_RULES.get(
                        fixer_name,
                        ("warning",
                         f"Construction Python 2 détectée (règle {fixer_name})",
                         "Voir la documentation de 2to3 pour cette règle"),
                    )
                    in_range = 0 < line <= len(lines)
                    issues.append(Issue(
                        file_path=str(file_path), line=line, plugin=self.name,
                        rule_id=f"PY2_{fixer_name.upper()}",
                        severity=severity, message=message,
                        recommendation=recommendation,
                        code_snippet=lines[line - 1].strip() if in_range else None,
                    ))

        issues.sort(key=lambda issue: issue.line)
        return issues