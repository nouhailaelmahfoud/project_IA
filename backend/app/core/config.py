from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # racine du repo
WORKSPACE = ROOT / "workspace" / "jobs"             # fichiers uploadés par job
WORKSPACE.mkdir(parents=True, exist_ok=True)

SUPPORTED_LANGUAGES = ("php", "python")
EXTENSIONS = {".php": "php", ".py": "python"}