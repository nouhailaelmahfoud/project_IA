
import subprocess
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Chemin vers le script PHP intermédiaire
parser_path = (
    BASE_DIR
    / "plugins"
    / "php_analyzer"
    / "engine"
    / "run_dependency_parser.php"
)

# Fichier PHP à analyser
php_file = BASE_DIR / "Mon projet_test" / "test_dependencies.php"

# Appel du script PHP depuis Python
result = subprocess.run(
    ["php", str(parser_path), str(php_file)],
    capture_output=True,
    text=True
)

print("Code retour :", result.returncode)
print("Erreurs PHP :", result.stderr)

if result.returncode == 0:
    includes = json.loads(result.stdout)

    print("\nDépendances PHP détectées :")

    for item in includes:
        print(
            f"Type : {item['type']} | "
            f"Fichier : {item['path']} | "
            f"Existe : {item['exists']} | "
            f"Ligne : {item['line']}"
        )
