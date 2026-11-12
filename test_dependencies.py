

from pathlib import Path
from core.dependency_analyzer import DependencyAnalyzer

analyzer = DependencyAnalyzer()

BASE_DIR = Path(__file__).resolve().parent

project_dir = BASE_DIR / "Mon projet_test"
file_path = project_dir / "test_imports.py"

# Extraire les imports
imports = analyzer.extract_imports(file_path)

# Identifier les dÃ©pendances locales
dependencies = analyzer.find_local_dependencies(
    imports,
    project_dir,
    file_path
)

print("DÃ©pendances locales dÃ©tectÃ©es :")

for dependency in dependencies:
    print(dependency.relative_to(project_dir))


graph = analyzer.build_dependency_graph(project_dir)

print("\nGraphe de dÃ©pendances :")

for source, dependencies in graph.items():

    print(f"\n{source}")

    for dependency in dependencies:
        print(f"  â””â”€â”€> {dependency}")


print("\nTest de dÃ©tection des cycles :")

test_graph = {
    "A.py": ["B.py"],
    "B.py": ["C.py"],
    "C.py": ["A.py"],
    "D.py": []
}

cycles = analyzer.detect_cycles(test_graph)

if cycles:
    for cycle in cycles:
        print("Cycle dÃ©tectÃ© :", " -> ".join(cycle))
else:
    print("Aucun cycle dÃ©tectÃ©.")


print("\nTest sans cycle :")

test_graph_2 = {
    "A.py": ["B.py"],
    "B.py": ["C.py"],
    "C.py": [],
    "D.py": []
}

cycles = analyzer.detect_cycles(test_graph_2)

if cycles:
    for cycle in cycles:
        print("Cycle dÃ©tectÃ© :", " -> ".join(cycle))
else:
    print("Aucun cycle dÃ©tectÃ©.")

print("\nCycles dans le projet rÃ©el :")

real_cycles = analyzer.detect_cycles(graph)

if real_cycles:
    for cycle in real_cycles:
        print("Cycle dÃ©tectÃ© :", " -> ".join(cycle))
else:
    print("Aucune dÃ©pendance circulaire dÃ©tectÃ©e.")
