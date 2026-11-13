import json
import subprocess
from pathlib import Path

from core.models import Issue
from core.plugin_base import LanguagePlugin

ENGINE = Path(__file__).resolve().parent / "engine" / "run_issue_detector.php"


class PhpPlugin(LanguagePlugin):
    """Détecte les constructions PHP 7 supprimées ou dépréciées en PHP 8."""

    name = "php_analyzer"
    file_extensions = (".php",)

    def analyze_file(self, file_path: Path) -> list[Issue]:
        file_path = Path(file_path)

        result = subprocess.run(
            ["php", str(ENGINE), str(file_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Erreur lors de l'analyse PHP de {file_path} : {result.stderr}"
            )

        lines = file_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()

        issues = []
        for item in json.loads(result.stdout):
            line = item["line"]
            in_range = 0 < line <= len(lines)
            issues.append(Issue(
                file_path=str(file_path),
                line=line,
                plugin=self.name,
                rule_id=item["rule_id"],
                severity=item["severity"],
                message=item["message"],
                recommendation=item["recommendation"],
                code_snippet=lines[line - 1].strip() if in_range else None,
            ))
        return issues