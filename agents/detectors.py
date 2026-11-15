"""Détecteurs fixes des pièges de Python 2 que les règles de 2to3 ne corrigent pas.

Ils lisent le code DÉJÀ converti par les règles (donc du Python 3 valide) et
renvoient des risques avec le bon numéro de ligne et une recette de correction.
"""
import ast
import re

# Ce que le module string de Python 3 contient encore
STRING_MODULE_OK = {
    "ascii_letters", "ascii_lowercase", "ascii_uppercase", "capwords", "digits",
    "hexdigits", "octdigits", "printable", "punctuation", "whitespace",
    "Formatter", "Template",
}

CMP_RECIPE = (
    "Remplace la méthode __cmp__ par cinq méthodes qui comparent les mêmes valeurs : "
    "__eq__ (==), __lt__ (<), __le__ (<=), __gt__ (>), __ge__ (>=). Par exemple, "
    "si __cmp__ compare self.x et other.x, écris : "
    "def __eq__(self, other): return self.x == other.x ; "
    "def __lt__(self, other): return self.x < other.x ; etc."
)

REMOVED_METHODS = {
    "__cmp__": ("La méthode __cmp__ est ignorée en Python 3 : les comparaisons "
                "(<, >, ==) plantent ou donnent un autre résultat", CMP_RECIPE),
    "__unicode__": ("La méthode __unicode__ n'est plus utilisée en Python 3",
                    "Renomme-la en __str__ (et supprime l'ancien __str__ s'il existe)"),
    "__div__": ("__div__ n'est plus utilisée pour l'opérateur / en Python 3",
                "Renomme-la en __truediv__ (ou __floordiv__ si la division doit rester entière)"),
    "__rdiv__": ("__rdiv__ n'est plus utilisée pour l'opérateur / en Python 3",
                 "Renomme-la en __rtruediv__"),
    "__idiv__": ("__idiv__ n'est plus utilisée pour l'opérateur /= en Python 3",
                 "Renomme-la en __itruediv__"),
    "__getslice__": ("__getslice__ n'existe plus en Python 3",
                     "Gère les tranches dans __getitem__ (l'argument est un objet slice)"),
    "__setslice__": ("__setslice__ n'existe plus en Python 3",
                     "Gère les tranches dans __setitem__ (l'argument est un objet slice)"),
}

DIVISION_ADVICE = (
    "Si les deux valeurs sont des entiers et que le résultat doit rester entier, "
    "remplace / par // ; si au moins une valeur est décimale, laisse tel quel"
)


def _is_float_like(node):
    return (
        isinstance(node, ast.Constant) and isinstance(node.value, float)
    ) or (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "float"
    )


def _local_names(tree):
    """Noms définis par le programme lui-même (fonctions, classes, variables)."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
    return names


def detect_python_risks(code: str, original: str = None) -> list:
    """Renvoie la liste des risques repérés dans le code Python 3 donné.

    original sert à retrouver un éventuel « from __future__ import division »
    que les règles ont supprimé.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    lines = code.splitlines()
    source_for_future = original if original is not None else code
    future_division = bool(re.search(
        r"from\s+__future__\s+import[^\n]*\bdivision\b", source_for_future))
    imports_string = any(
        isinstance(node, ast.Import)
        and any(alias.name == "string" for alias in node.names)
        for node in ast.walk(tree)
    )
    local = _local_names(tree)

    risks, seen = [], set()

    def add(node, kind, description, suggestion, blocking=True):
        line = node.lineno
        if (kind, line) in seen:
            return
        seen.add((kind, line))
        risks.append({
            "kind": kind,
            "line": line,
            "code": lines[line - 1].strip() if 0 < line <= len(lines) else "",
            "description": description,
            "suggestion": suggestion,
            "blocking": blocking,
        })

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in REMOVED_METHODS:
                description, suggestion = REMOVED_METHODS[node.name]
                add(node, f"method:{node.name}", description, suggestion)

        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "cmp" and "cmp" not in local:
                add(node, "cmp", "cmp() n'existe plus en Python 3",
                    "Remplace cmp(a, b) par (a > b) - (a < b)")
            elif isinstance(func, ast.Name) and func.id == "file" and "file" not in local:
                add(node, "file", "file() n'existe plus en Python 3",
                    "Utilise open() à la place de file()")
            elif isinstance(func, ast.Attribute) and func.attr == "sort" and node.args:
                add(node, "sort-cmp",
                    "sort() n'accepte plus de fonction de comparaison en argument",
                    "Utilise sort(key=functools.cmp_to_key(f)) avec import functools, "
                    "ou une fonction key")
            elif (isinstance(func, ast.Name) and func.id == "sorted"
                  and len(node.args) >= 2):
                add(node, "sort-cmp",
                    "sorted() n'accepte plus de fonction de comparaison en argument",
                    "Utilise sorted(x, key=functools.cmp_to_key(f)) avec import functools")

        elif isinstance(node, ast.Attribute):
            if (imports_string and isinstance(node.value, ast.Name)
                    and node.value.id == "string"
                    and node.attr not in STRING_MODULE_OK):
                add(node, f"string:{node.attr}",
                    f"string.{node.attr} n'existe plus en Python 3",
                    f"Utilise la méthode de la chaîne : x.{node.attr}() à la place "
                    f"de string.{node.attr}(x)")

        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            if not future_division and not (
                    _is_float_like(node.left) or _is_float_like(node.right)):
                add(node, "division",
                    "Division « / » : entière en Python 2 si les deux valeurs sont "
                    "entières, décimale en Python 3",
                    DIVISION_ADVICE, blocking=False)

        elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
            if not future_division and not _is_float_like(node.value):
                add(node, "division",
                    "Division « /= » : entière en Python 2 si les deux valeurs sont "
                    "entières, décimale en Python 3",
                    DIVISION_ADVICE, blocking=False)

    risks.sort(key=lambda risk: risk["line"])
    return risks
