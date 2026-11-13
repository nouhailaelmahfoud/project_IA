from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Issue:
    """Un problème détecté dans un fichier de code legacy."""

    file_path: str
    line: int
    plugin: str
    rule_id: str
    severity: str  # "critical", "high" ou "warning"
    message: str
    recommendation: str
    code_snippet: Optional[str] = None

    def to_dict(self):
        return asdict(self)
