"""Moteur de règles : applique automatiquement ce que 2to3 sait convertir."""
import warnings
from dataclasses import dataclass, field

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from lib2to3 import refactor


@dataclass
class RulesResult:
    code: str                     # le code après application des règles
    changed: bool                 # les règles ont-elles modifié quelque chose ?
    warnings: list = field(default_factory=list)  # remarques de 2to3


def apply_python_rules(source: str) -> RulesResult:
    """Convertit du Python 2 en Python 3 avec les règles de 2to3."""
    fixer_names = refactor.get_fixers_from_package("lib2to3.fixes")
    tool = refactor.RefactoringTool(fixer_names)

    code = source if source.endswith("\n") else source + "\n"
    try:
        tree = tool.refactor_string(code, "<code>")
    except Exception as error:
        return RulesResult(
            code=source,
            changed=False,
            warnings=[f"Règles non appliquées : {error}"],
        )

    new_code = str(tree)
    return RulesResult(
        code=new_code,
        changed=new_code != code,
        warnings=list(tool.fixer_log),
    )