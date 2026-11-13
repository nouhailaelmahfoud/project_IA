"""Outils pour appeler un modèle et lire ses réponses."""
import json
import re

FENCE = "`" * 3  # les trois apostrophes inversées qui entourent un bloc de code


def ask_llm(llm, prompt: str):
    """Envoie le prompt. Renvoie (texte, tokens_entrée, tokens_sortie)."""
    response = llm.invoke(prompt)
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
