"""Outils pour appeler un modèle et lire ses réponses."""
import json
import re
import time
from pathlib import Path

VERBOSE = False  # si True, affiche l'avancement pendant les appels

FENCE = "`" * 3  # les trois apostrophes inversées qui entourent un bloc de code


def ask_llm(llm, prompt: str, label: str = "modèle"):
    """Envoie le prompt. Renvoie (texte, tokens_entrée, tokens_sortie)."""
    if VERBOSE:
        print(f"  ... {label} : appel en cours (plusieurs minutes possibles "
              f"sur un petit PC)", flush=True)
    start = time.time()
    response = llm.invoke(prompt)
    if VERBOSE:
        print(f"  ... {label} : réponse reçue en {time.time() - start:.0f} s",
              flush=True)
    content = response.content
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    # Certains modèles écrivent leur réflexion entre balises <think>
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    usage = getattr(response, "usage_metadata", None) or {}
    return content, usage.get("input_tokens", 0), usage.get("output_tokens", 0)


def extract_json(text: str) -> dict:
    """Trouve un objet JSON dans la réponse, même entouré de texte."""
    text = text.strip()
    candidates = [text]

    fenced = re.search(FENCE + r"(?:json)?\s*(.*?)" + FENCE, text, re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1).strip())

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise ValueError("Aucun JSON valide dans la réponse du modèle")


def extract_code_block(text: str):
    """Plan B : récupère le premier bloc de code entouré de trois apostrophes inversées."""
    match = re.search(FENCE + r"[a-zA-Z0-9]*\n(.*?)" + FENCE, text, re.DOTALL)
    return match.group(1) if match else None


def extract_tagged(text: str, tag: str):
    """Renvoie le texte entre <tag> et </tag>, ou None si absent."""
    match = re.search(rf"<{tag}>\s*\n?(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1) if match else None


def strip_code_fence(code: str) -> str:
    """Retire les apostrophes inversées si le modèle en a mis dans les balises."""
    lines = code.strip("\n").splitlines()
    if lines and lines[0].startswith(FENCE):
        lines = lines[1:]
        if lines and lines[-1].strip() == FENCE:
            lines = lines[:-1]
    return "\n".join(lines)


def parse_migration(text: str):
    """Lit la réponse du Migrateur. Renvoie (code, changements) ou (None, [])."""
    # Format demandé : <changes>...</changes> puis <code>...</code>
    tagged = extract_tagged(text, "code")
    if tagged and tagged.strip():
        block = extract_tagged(text, "changes") or ""
        changes = [line.lstrip("-* ").strip() for line in block.splitlines() if line.strip()]
        return strip_code_fence(tagged) + "\n", changes

    # Plan B : du JSON avec un champ "code"
    try:
        data = extract_json(text)
        code = data.get("code")
        if isinstance(code, str) and code.strip():
            changes = data.get("changes")
            return code, [str(c) for c in changes] if isinstance(changes, list) else []
    except ValueError:
        pass

    # Plan C : un bloc de code entouré d'apostrophes inversées
    fenced = extract_code_block(text)
    if fenced and fenced.strip():
        return fenced, []
    return None, []


def save_debug(file_path, step: str, iteration: int, text: str) -> str:
    """Garde la réponse brute du modèle pour comprendre un échec."""
    folder = Path("output") / "debug"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{Path(file_path).stem}_{step}_{iteration}.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)
