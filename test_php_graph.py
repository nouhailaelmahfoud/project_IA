
from core.dependency_analyzer import DependencyAnalyzer
from pathlib import Path

analyzer = DependencyAnalyzer()

project_dir = (
    Path(__file__).resolve().parent
    / "Mon projet_test"
)

php_graph = analyzer.build_php_dependency_graph(project_dir)
cycles = analyzer.detect_cycles(php_graph)
print("\nCycles détectés :")

if cycles:
    for cycle in cycles:
        print(" -> ".join(cycle))
else:
    print("Aucun cycle détecté.")

print("Graphe des dépendances PHP :\n")

for source, dependencies in php_graph.items():

    print(source)

    for dependency in dependencies:
        print(f"    └──> {dependency}")

    if not dependencies:
        print("    (Aucune dépendance locale)")

# Visualisation du graphe PHP
graph_path = (
    Path(__file__).resolve().parent
    / "reports"
    / "php_dependency_graph.png"
)

analyzer.visualize_dependency_graph(
    php_graph,
    graph_path,
    language="PHP"
)