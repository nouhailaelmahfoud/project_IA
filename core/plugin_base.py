from abc import ABC, abstractmethod
from pathlib import Path

from core.models import Issue


class LanguagePlugin(ABC):
    """Modèle commun à tous les plugins d'analyse."""

    name: str = ""
    file_extensions: tuple = ()

    @abstractmethod
    def analyze_file(self, file_path: Path) -> list[Issue]:
        """Analyse un fichier et renvoie la liste des problèmes trouvés."""

    def analyze_project(self, project_dir) -> list[Issue]:
        """Analyse tous les fichiers du projet pour ce langage."""
        issues = []
        for extension in self.file_extensions:
            for source_file in Path(project_dir).rglob(f"*{extension}"):
                issues.extend(self.analyze_file(source_file))
        return issues
