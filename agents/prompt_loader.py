import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(prompt_dir: str, name: str, **values) -> str:
    """Lit prompts/<prompt_dir>/<name>.md et remplace les {variables}."""
    template = (PROMPTS_DIR / prompt_dir / f"{name}.md").read_text(
        encoding="utf-8"
    )
    # Un seul passage : le code inséré n'est jamais retraité
    return re.sub(
        r"\{(\w+)\}",
        lambda match: str(values.get(match.group(1), match.group(0))),
        template,
    )
