from core.dependency_analyzer import DependencyAnalyzer
from pathlib import Path

analyzer = DependencyAnalyzer()

project_dir = (
    Path(__file__).resolve().parent
    / "Mon projet_test"
    / "cycles_php"
)

graph = analyzer.build_php_dependency_graph(project_dir)

print("Graphe PHP :")
for source, dependencies in graph.items():
    print(source, "->", dependencies)

cycles = analyzer.detect_cycles(graph)

print("\nCycles détectés :")

if cycles:
    for cycle in cycles:
        print(" -> ".join(cycle))
else:
    print("Aucun cycle détecté.")