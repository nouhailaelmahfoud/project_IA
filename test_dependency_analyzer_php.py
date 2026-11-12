from core.dependency_analyzer import DependencyAnalyzer
from pathlib import Path

analyzer = DependencyAnalyzer()

php_file = (
    Path(__file__).resolve().parent
    / "Mon projet_test"
    / "test_dependencies.php"
)

dependencies = analyzer.extract_php_dependencies(php_file)

for dependency in dependencies:
    print(dependency)