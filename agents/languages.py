"""Configuration par langage : pour en ajouter un, on ajoute une entrée."""
from agents.rules_engine import apply_python_rules

LANGUAGES = {
    "python": {
        "prompt_dir": "py2_to_3",
        "rules": apply_python_rules,
    },
}
