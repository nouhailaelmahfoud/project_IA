"""Modifications ciblées : le modèle ne renvoie que les lignes à remplacer."""
import re

from agents.llm_utils import strip_code_fence

EDIT_PATTERN = re.compile(r"<old>\n?(.*?)</old>\s*<new>\n?(.*?)</new>", re.DOTALL)


def number_lines(code: str) -> str:
    """Ajoute un numéro devant chaque ligne : '  12| texte'."""
    return "\n".join(
        f"{number:3}| {line}" for number, line in enumerate(code.splitlines(), start=1)
    )


def parse_edits(text: str) -> list:
    """Extrait les couples (ancien texte, nouveau texte) de la réponse du modèle."""
    return EDIT_PATTERN.findall(text)


def replace_unique(code: str, old_text: str, new_text: str):
    """Remplace old_text par new_text s'il apparaît une seule fois.

    Renvoie (nouveau_code, "ok") ou (None, "absent" / "ambigu").
    """
    code_lines = code.split("\n")
    old_lines = old_text.split("\n")
    size = len(old_lines)

    # 1. Lignes entières identiques (on ignore les espaces en fin de ligne)
    wanted = [line.rstrip() for line in old_lines]
    matches = [
        i for i in range(len(code_lines) - size + 1)
        if [line.rstrip() for line in code_lines[i:i + size]] == wanted
    ]
    if len(matches) == 1:
        i = matches[0]
        new_lines = new_text.split("\n") if new_text else []
        return "\n".join(code_lines[:i] + new_lines + code_lines[i + size:]), "ok"
    if len(matches) > 1:
        return None, "ambigu"

    # 2. Plan B : un morceau de ligne
    occurrences = code.count(old_text)
    if occurrences == 1:
        return code.replace(old_text, new_text, 1), "ok"
    if occurrences > 1:
        return None, "ambigu"
    return None, "absent"


def apply_edits(code: str, edits: list):
    """Applique les modifications. Renvoie (nouveau_code, nombre_appliquées, problèmes)."""
    problems = []
    applied = 0
    for number, (old, new) in enumerate(edits, start=1):
        old_text = strip_code_fence(old).strip("\n")
        new_text = strip_code_fence(new).strip("\n")
        if not old_text.strip():
            problems.append(f"modification {number} : le texte <old> est vide")
            continue

        patched, status = replace_unique(code, old_text, new_text)
        first_line = old_text.splitlines()[0].strip()[:60]
        if status == "ok":
            code = patched
            applied += 1
        elif status == "absent":
            problems.append(
                f"modification {number} : le texte <old> est introuvable dans le code "
                f"(« {first_line} »). Copie les lignes EXACTEMENT comme dans le code."
            )
        else:
            problems.append(
                f"modification {number} : le texte <old> apparaît plusieurs fois "
                f"(« {first_line} »). Ajoute les lignes voisines pour le rendre unique."
            )
    return code, applied, problems


def locate_snippet(code: str, snippet: str):
    """Numéro (à partir de 1) de la première ligne contenant l'extrait, sinon None."""
    lines = (snippet or "").strip().splitlines()
    if not lines:
        return None
    # Si le modèle a recopié le numéro ("12| texte"), on l'enlève
    wanted = re.sub(r"^\s*\d+\|\s?", "", lines[0]).strip()
    if len(wanted) < 3:
        return None
    for number, line in enumerate(code.splitlines(), start=1):
        if wanted in line:
            return number
    return None


def verify_risks(code: str, risks: list):
    """Ne garde que les risques dont la ligne de code existe vraiment.

    Corrige aussi le numéro de ligne. Renvoie (risques_retenus, nombre_écartés).
    """
    kept, dropped = [], 0
    for risk in risks:
        line = locate_snippet(code, risk.get("code", ""))
        if line is None:
            dropped += 1
            continue
        kept.append({**risk, "line": line})
    return kept, dropped
