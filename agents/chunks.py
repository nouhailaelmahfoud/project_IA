"""Découpage des gros fichiers : on n'envoie au modèle que les extraits utiles."""
import difflib
import re

LARGE_FILE_LINES = 150  # au-delà, le fichier entier n'est plus envoyé au modèle
CONTEXT_LINES = 12      # lignes de contexte autour de chaque risque ou erreur
REVIEW_CONTEXT = 6      # lignes de contexte autour de chaque modification


def is_large(code: str) -> bool:
    return len(code.splitlines()) > LARGE_FILE_LINES


def merge_ranges(ranges):
    """Fusionne les intervalles (début, fin) qui se touchent ou se chevauchent."""
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def lines_in_errors(errors):
    """Numéros de ligne cités dans des messages d'erreur (« on line 5 », « ligne 12 »)."""
    found = []
    for error in errors:
        found.extend(int(n) for n in re.findall(r"(?:line|ligne)\s+(\d+)", error))
    return found


def risk_windows(code, risks, errors=(), context=CONTEXT_LINES):
    """Intervalles de lignes à montrer : autour de chaque risque et de chaque erreur."""
    total = len(code.splitlines())
    targets = [int(r["line"]) for r in risks if str(r.get("line", "")).isdigit()]
    targets += lines_in_errors(errors)
    ranges = [(max(1, n - context), min(total, n + context))
              for n in targets if 1 <= n <= total]
    return merge_ranges(ranges)


def render_excerpts(code, windows):
    lines = code.splitlines()
    parts = []
    for start, end in windows:
        parts.append(f"[extrait : lignes {start} à {end} du fichier]")
        parts.extend(lines[start - 1:end])
    return "\n".join(parts)


def migrator_view(code, risks, errors=()):
    """Ce que voit le Migrateur : le fichier entier s'il est court, sinon des extraits."""
    if not is_large(code):
        return code
    windows = risk_windows(code, risks, errors)
    if not windows:  # rien à localiser : on montre le début du fichier
        windows = [(1, LARGE_FILE_LINES)]
    return render_excerpts(code, windows)


def large_note(code):
    """Consigne ajoutée au Migrateur quand le fichier est long."""
    if not is_large(code):
        return ""
    return ("Le fichier est long : le bloc <code> ne contient que des extraits, marqués "
            "« [extrait : lignes A à B du fichier] ». Copie exactement les lignes de ces "
            "extraits dans <old>, sans les lignes de marquage.")


def join_notes(feedback, note):
    return (feedback + "\n\n" + note).strip() if note else feedback


def reviewer_excerpts(original, migrated):
    """Ce que voit le Reviewer : les deux fichiers s'ils sont courts, sinon les parties modifiées."""
    if not (is_large(original) or is_large(migrated)):
        return original, migrated
    old, new = original.splitlines(), migrated.splitlines()
    groups = difflib.SequenceMatcher(None, old, new, autojunk=False) \
        .get_grouped_opcodes(REVIEW_CONTEXT)
    if not groups:
        return original, migrated  # aucune différence
    note = "(Fichier long : seules les parties modifiées sont montrées, avec leur contexte.)"
    old_parts, new_parts = [note], [note]
    for group in groups:
        i1, i2, j1, j2 = group[0][1], group[-1][2], group[0][3], group[-1][4]
        old_parts.append(f"[extrait : lignes {i1 + 1} à {max(i1 + 1, i2)} du fichier]")
        old_parts.extend(old[i1:i2])
        new_parts.append(f"[extrait : lignes {j1 + 1} à {max(j1 + 1, j2)} du fichier]")
        new_parts.extend(new[j1:j2])
    return "\n".join(old_parts), "\n".join(new_parts)
