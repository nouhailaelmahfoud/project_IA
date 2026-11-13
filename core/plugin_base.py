from abc import ABC, abstractmethod
from pathlib import Path

from core.models import Issue

# Dossiers qu'on n'analyse jamais (bibliothèques, environnements, cache)
IGNORED_DIRECTORIES = {
    ".git", ".venv", "venv", "vendor", "node_modules", "__pycache__",
}


class LanguagePlugin(ABC):
    """Modèle commun à tous les plugins d'analyse."""

    name: str = ""
    file_extensions: tuple = ()

    @abstractmethod
    def analyze_file(self, file_path: Path) -> list[Issue]:
        """Analyse un fichier et renvoie la liste des problèmes trouvés."""

    def analyze_project(self, project_dir) -> list[Issue]:
        """Analyse tous les fichiers du projet pour ce langage."""
        project_dir = Path(project_dir)
        issues = []
        for extension in self.file_extensions:
            for source_file in sorted(project_dir.rglob(f"*{extension}")):
                relative_parts = source_file.relative_to(project_dir).parts
                if IGNORED_DIRECTORIES.intersection(relative_parts):
                    continue
                issues.extend(self.analyze_file(source_file))
        return issues