"""Outils pour appeler un modèle et lire ses réponses."""
import json
import re
import time
from pathlib import Path

VERBOSE = False  # si True, affiche l'avancement pendant les appels

# Raison de fin de la dernière réponse (aide à comprendre une coupure)
LAST_FINISH = {"reason": None}

FENCE = "`" * 3  # les trois apostrophes inversées qui entourent un bloc de code


RETRY_WAITS = (30, 60)  # secondes d'attente avant chaque nouvel essai


def _is_rate_limit(error) -> bool:
    """Le fournisseur dit « trop de demandes » (erreur 429) ?"""
    return "429" in str(error) or "RateLimit" in type(error).__name__


def ask_llm(llm, prompt: str, label: str = "modèle"):
    """Envoie le prompt. Renvoie (texte, tokens_entrée, tokens_sortie)."""
    if VERBOSE:
        print(f"  ... {label} : appel en cours (plusieurs minutes possibles "
              f"sur un petit PC)", flush=True)
    start = time.time()
    for attempt in range(len(RETRY_WAITS) + 1):
        try:
            response = llm.invoke(prompt)
            break
        except Exception as error:
            if not _is_rate_limit(error):
                raise
            if attempt == len(RETRY_WAITS):
                raise RuntimeError(
                    "Limite de débit du fournisseur (429) toujours atteinte après "
                    f"{attempt + 1} essais. Réessaie plus tard ou change de modèle "
                    "(option --model)."
                ) from error
            wait = RETRY_WAITS[attempt]
            if VERBOSE:
                print(f"  ... {label} : limite de débit du fournisseur (429), "
                      f"nouvel essai dans {wait} s", flush=True)
            time.sleep(wait)
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
    meta = getattr(response, "response_metadata", None) or {}
    LAST_FINISH["reason"] = meta.get("done_reason") or meta.get("finish_reason")
    if VERBOSE and LAST_FINISH["reason"] == "length":
        print("  ... ATTENTION : réponse coupée par la limite de longueur "
              "(le modèle « réfléchit » trop ?)", flush=True)
    return content, usage.get("input_tokens", 0), usage.get("output_tokens", 0)


def extract_json(text: str, repair: bool = False) -> dict:
    """Trouve un objet JSON dans la réponse, même entouré de texte.

    Avec repair=True, tente aussi de réparer un JSON coupé en route.
    """
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
    if repair:
        data = repair_truncated_json(text)
        if data is not None:
            return data
    raise ValueError("Aucun JSON valide dans la réponse du modèle")


def extract_code_block(text: str):
    """Plan B : récupère le premier bloc de code entouré de trois apostrophes inversées."""
    match = re.search(FENCE + r"[a-zA-Z0-9]*\n(.*?)" + FENCE, text, re.DOTALL)
    return match.group(1) if match else None


def repair_truncated_json(text: str):
    """Ferme les guillemets et accolades d'un JSON coupé ; None si impossible."""
    start = text.find("{")
    if start == -1:
        return None
    body = text[start:]

    # On essaie le texte entier, puis en reculant jusqu'à une virgule ou fermeture
    cut_points = [len(body)] + [
        i for i in range(len(body) - 1, 0, -1) if body[i] in ",}]"
    ]
    for cut in cut_points[:25]:
        candidate = body[:cut]
        closers, in_string, escaped = [], False, False
        for char in candidate:
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char in "{[":
                closers.append("}" if char == "{" else "]")
            elif char in "}]" and closers:
                closers.pop()
        repaired = candidate + ('"' if in_string else "") + "".join(reversed(closers))
        try:
            data = json.loads(repaired, strict=False)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


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
    reason = LAST_FINISH.get("reason")
    path.write_text(
        f"{text}\n\n[raison de fin de génération : {reason}]\n",
        encoding="utf-8",
    )
    return str(path)
