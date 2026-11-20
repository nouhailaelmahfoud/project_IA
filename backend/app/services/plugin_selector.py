"""Choisit le plugin d'analyse (Tâche 1) selon le langage."""
import importlib.util
import inspect
from collections import Counter
from pathlib import Path

from backend.app.core.config import EXTENSIONS, ROOT, SUPPORTED_LANGUAGES
from core.plugin_base import LanguagePlugin

PLUGIN_FILES = {
    "php": ROOT / "plugins" / "php_analyzer" / "php_plugin.py",
    "python": ROOT / "plugins" / "python_analyzer" / "python_plugin.py",
}


def detect_language(files: list[str]) -> str:
    """Devine le langage d'après les extensions des fichiers reçus."""
    counts = Counter(EXTENSIONS[Path(f).suffix.lower()]
                     for f in files if Path(f).suffix.lower() in EXTENSIONS)
    if not counts:
        raise ValueError("Langage non détecté : aucun fichier .php ou .py.")
    return counts.most_common(1)[0][0]


def get_plugin(language: str) -> LanguagePlugin:
    """Charge le fichier du plugin et instancie sa sous-classe de LanguagePlugin."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Langage non supporté : {language}")
    path = PLUGIN_FILES[language]
    spec = importlib.util.spec_from_file_location(f"plugin_{language}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if issubclass(cls, LanguagePlugin) and cls is not LanguagePlugin:
            return cls()
    raise RuntimeError(f"Aucune classe LanguagePlugin dans {path}")