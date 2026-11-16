"""Configuration par langage : pour en ajouter un, on ajoute une entrée."""
from agents.detectors import detect_python_risks
from agents.php_support import apply_php_rules, detect_php_risks
from agents.rules_engine import apply_python_rules

LANGUAGES = {
    "python": {
        "prompt_dir": "py2_to_3",
        "target": "Python 3",
        "rules": apply_python_rules,
        "detector": detect_python_risks,
    },
    "php": {
        "prompt_dir": "php7_to_8",
        "target": "PHP 8",
        "rules": apply_php_rules,
        "detector": detect_php_risks,
    },
}
