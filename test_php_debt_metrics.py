
from pathlib import Path
from core.dependency_analyzer import DependencyAnalyzer
from reports.report_generator import ReportGenerator

analyzer = DependencyAnalyzer()

# Dossier contenant les fichiers PHP à analyser
project_dir = (
    Path(__file__).resolve().parent
    / "Mon projet_test"
)

# 1. Construction du graphe PHP
php_graph = analyzer.build_php_dependency_graph(project_dir)

# 2. Détection des dépendances PHP manquantes
missing_php = analyzer.find_missing_php_dependencies(
    project_dir
)

# 3. Détection des cycles
php_cycles = analyzer.detect_cycles(php_graph)

# 4. Calcul des indicateurs
php_metrics = analyzer.calculate_dependency_metrics(
    php_graph,
    missing_php
)

# 5. Calcul du score de dette technique
php_score = analyzer.calculate_technical_debt_score(
    php_metrics
)

# 6. Affichage des résultats
print("\n========== GRAPHE DE DEPENDANCES PHP ==========")

for source, dependencies in php_graph.items():
    print(f"\n{source}")

    for dependency in dependencies:
        print(f"  -> {dependency}")

print("\n========== INDICATEURS DE DETTE PHP ==========")

for name, value in php_metrics.items():
    print(f"{name} : {value}")

print("\n========== SCORE DE DETTE PHP ==========")

for name, value in php_score.items():
    print(f"{name} : {value}")

print("\n========== DEPENDANCES PHP MANQUANTES ==========")

if missing_php:
    for source, dependencies in missing_php.items():
        print(f"\nFichier : {source}")

        for dependency in dependencies:
            print(
                f"  - {dependency['path']} "
                f"(ligne {dependency['line']})"
            )
else:
    print("Aucune dépendance manquante.")

print("\n========== CYCLES PHP ==========")

if php_cycles:
    for cycle in php_cycles:
        print(" -> ".join(cycle))
else:
    print("Aucun cycle détecté.")

# 7. Génération des rapports
report_generator = ReportGenerator()

reports_dir = Path(__file__).resolve().parent / "reports"

report_generator.generate_debt_report(
    language="PHP",
    metrics=php_metrics,
    debt_assessment=php_score,
    missing_dependencies=missing_php,
    cycles=php_cycles,
    output_path=reports_dir / "php_debt_report.json"
)

report_generator.generate_debt_html_report(
    language="PHP",
    metrics=php_metrics,
    debt_assessment=php_score,
    missing_dependencies=missing_php,
    cycles=php_cycles,
    output_path=reports_dir / "php_debt_report.html"
)

# 8. Visualisation du graphe PHP
graph_path = reports_dir / "php_dependency_graph.png"

analyzer.visualize_dependency_graph(
    php_graph,
    graph_path,
    language="PHP"
)

print("\nRapports PHP générés avec succès.")
