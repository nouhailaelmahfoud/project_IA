import networkx as nx
import matplotlib.pyplot as plt
import ast
from pathlib import Path
import subprocess
import json
import importlib.util
import sys

class DependencyAnalyzer:

    def extract_imports(self, file_path):

        with open(file_path, "r", encoding="utf-8") as file:
            source_code = file.read()

        tree = ast.parse(source_code)

        imports = []

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "level": 0,
                        "names": []
                    })

            elif isinstance(node, ast.ImportFrom):
                imports.append({
                    "module": node.module or "",
                    "level": node.level,
                    "names": [alias.name for alias in node.names]
                })

        return imports

    def extract_php_dependencies(self, file_path):

        base_dir = Path(__file__).resolve().parent.parent

        parser_path = (
                base_dir
                / "plugins"
                / "php_analyzer"
                / "engine"
                / "run_dependency_parser.php"
        )

        result = subprocess.run(
            ["php", str(parser_path), str(file_path)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Erreur lors de l'analyse PHP : {result.stderr}"
            )

        return json.loads(result.stdout)

    def build_php_dependency_graph(self, project_dir):

        project_dir = Path(project_dir).resolve()
        graph = {}

        # Parcourir tous les fichiers PHP du projet
        for source_file in project_dir.rglob("*.php"):

            # Extraire les dépendances du fichier courant
            dependencies = self.extract_php_dependencies(source_file)

            relative_source = str(
                source_file.relative_to(project_dir)
            )

            graph[relative_source] = []

            for dependency in dependencies:

                # Ignorer les fichiers inexistants
                if not dependency["exists"]:
                    continue

                dependency_path = Path(
                    dependency["path"]
                ).resolve()

                # Vérifier que la dépendance appartient au projet
                try:
                    relative_dependency = str(
                        dependency_path.relative_to(project_dir)
                    )
                except ValueError:
                    continue

                # Éviter les doublons
                if relative_dependency not in graph[relative_source]:
                    graph[relative_source].append(relative_dependency)

        return graph

    def find_missing_php_dependencies(self, project_dir):
        project_dir = Path(project_dir).resolve()
        missing_dependencies = {}

        for source_file in project_dir.rglob("*.php"):

            dependencies = self.extract_php_dependencies(source_file)

            relative_source = str(
                source_file.relative_to(project_dir)
            )

            for dependency in dependencies:

                if dependency["exists"]:
                    continue

                dependency_path = Path(dependency["path"]).resolve()

                # Ne conserver que les dépendances internes au projet
                try:
                    relative_dependency = str(
                        dependency_path.relative_to(project_dir)
                    )
                except ValueError:
                    continue

                missing_dependencies.setdefault(
                    relative_source, []
                ).append({
                    "path": relative_dependency,
                    "type": dependency["type"],
                    "line": dependency["line"]
                })

        return missing_dependencies

    def find_missing_python_dependencies(self, project_dir):
        project_dir = Path(project_dir).resolve()
        missing_dependencies = {}

        def module_exists(module_name):
            module_path = Path(*module_name.split("."))

            file_path = project_dir / module_path.with_suffix(".py")
            package_path = project_dir / module_path / "__init__.py"
            directory_path = project_dir / module_path

            return (
                    file_path.is_file()
                    or package_path.is_file()
                    or directory_path.is_dir()
            )

        def is_external_module(module_name):
            top_level = module_name.split(".")[0]

            # Modules standards de Python
            if top_level in sys.stdlib_module_names:
                return True

            # Bibliothèques installées dans l'environnement
            try:
                return importlib.util.find_spec(top_level) is not None
            except (ModuleNotFoundError, ValueError):
                return False

        for source_file in project_dir.rglob("*.py"):

            with open(source_file, "r", encoding="utf-8") as file:
                source_code = file.read()

            tree = ast.parse(source_code)
            relative_source = str(source_file.relative_to(project_dir))

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):
                    imported_modules = [
                        alias.name for alias in node.names
                    ]

                elif isinstance(node, ast.ImportFrom):
                    # Les imports relatifs seront traités ultérieurement
                    if node.level > 0 or not node.module:
                        continue

                    imported_modules = [
                        f"{node.module}.{alias.name}"
                        for alias in node.names
                    ]

                    # Un package local ou externe peut exporter
                    # des fonctions et des classes, pas seulement des modules.
                    if (
                            module_exists(node.module)
                            or is_external_module(node.module)
                    ):
                        continue

                else:
                    continue

                for module in imported_modules:

                    if module_exists(module):
                        continue

                    if is_external_module(module):
                        continue

                    missing_dependencies.setdefault(
                        relative_source, []
                    ).append({
                        "module": module,
                        "line": node.lineno
                    })

        return missing_dependencies

    def find_local_dependencies(self, imports, project_dir, source_file):

        project_dir = Path(project_dir).resolve()
        source_file = Path(source_file).resolve()

        local_dependencies = []

        for item in imports:

            module = item["module"]
            level = item["level"]

            # Cas 1 : import absolu
            if level == 0:
                base_dir = project_dir

            # Cas 2 : import relatif
            else:
                base_dir = source_file.parent

                # Remonter dans les packages selon le nombre de points
                for _ in range(level - 1):
                    base_dir = base_dir.parent

            # Construire les chemins possibles
            module_path = (
                base_dir / Path(*module.split("."))
                if module
                else base_dir
            )

            candidates = []

            # Le module peut être un fichier Python
            if module:
                candidates.append(module_path.with_suffix(".py"))

            # Ou un package Python
            candidates.append(module_path / "__init__.py")

            # Cas : from . import db
            # Les noms importés peuvent également être des sous-modules.
            for name in item.get("names", []):
                if name == "*":
                    continue

                candidates.append(
                    module_path / f"{name}.py"
                )
                candidates.append(
                    module_path / name / "__init__.py"
                )

            for candidate in candidates:

                if candidate.is_file():
                    candidate = candidate.resolve()

                    # Éviter qu'un fichier dépende de lui-même
                    if candidate == source_file:
                        continue

                    # Ne conserver que les fichiers du projet
                    try:
                        candidate.relative_to(project_dir)
                    except ValueError:
                        continue

                    if candidate not in local_dependencies:
                        local_dependencies.append(candidate)

        return local_dependencies

    def build_dependency_graph(self, project_dir):

        project_dir = Path(project_dir)
        graph = {}

        # Parcourir tous les fichiers Python du projet
        for source_file in project_dir.rglob("*.py"):

            # Extraire les imports du fichier
            imports = self.extract_imports(source_file)

            # Identifier les dépendances locales
            dependencies = self.find_local_dependencies(
                imports,
                project_dir,
                source_file
            )

            # Enregistrer les relations dans le graphe
            relative_source = str(source_file.relative_to(project_dir))

            graph[relative_source] = [
                str(dependency.relative_to(project_dir))
                for dependency in dependencies
            ]

        return graph



    def detect_cycles(self, graph):

        visited = set()
        recursion_stack = set()
        cycles = []

        def dfs(node, path):

            visited.add(node)
            recursion_stack.add(node)

            path.append(node)

            for neighbor in graph.get(node, []):

                if neighbor not in visited:
                    dfs(neighbor, path)

                elif neighbor in recursion_stack:

                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]

                    if cycle not in cycles:
                        cycles.append(cycle)

            path.pop()
            recursion_stack.remove(node)

        for node in graph:

            if node not in visited:
                dfs(node, [])

        return cycles

    def calculate_dependency_metrics(self, graph, missing_dependencies=None):
        """
        Calcule les indicateurs de dépendances d'un langage.
        """

        if missing_dependencies is None:
            missing_dependencies = {}

        # Nombre total de fichiers
        total_files = len(graph)

        # Nombre de dépendances existantes
        total_dependencies = sum(
            len(dependencies)
            for dependencies in graph.values()
        )

        # Nombre de fichiers avec dépendances existantes
        files_with_dependencies = sum(
            1 for dependencies in graph.values()
            if dependencies
        )

        files_without_dependencies = (
                total_files - files_with_dependencies
        )

        # Nombre de cycles
        # Détection des cycles
        cycles = self.detect_cycles(graph)
        total_cycles = len(cycles)

        # Identification des fichiers impliqués dans les cycles
        files_in_cycles = set()

        for cycle in cycles:
            # Le dernier élément répète généralement le premier
            cycle_files = cycle[:-1] if cycle[0] == cycle[-1] else cycle

            files_in_cycles.update(cycle_files)

        total_files_in_cycles = len(files_in_cycles)

        # Densité des dépendances
        max_possible_dependencies = total_files * (total_files - 1)

        dependency_density = (
            total_dependencies / max_possible_dependencies
            if max_possible_dependencies > 0 else 0
        )

        # Proportion des fichiers impliqués dans des cycles
        cycle_file_ratio = (
            total_files_in_cycles / total_files
            if total_files > 0 else 0
        )


        # Nombre de dépendances manquantes
        total_missing_dependencies = sum(
            len(dependencies)
            for dependencies in missing_dependencies.values()
        )

        # Nombre de fichiers ayant des dépendances manquantes
        files_with_missing_dependencies = sum(
            1 for dependencies in missing_dependencies.values()
            if dependencies
        )

        # Total des références locales, existantes ou manquantes
        total_references = (
                total_dependencies + total_missing_dependencies
        )

        # Moyenne des dépendances existantes par fichier
        average_dependencies = (
            total_dependencies / total_files
            if total_files > 0 else 0
        )

        metrics = {
            "total_files": total_files,
            "total_dependencies": total_dependencies,
            "files_with_dependencies": files_with_dependencies,
            "files_without_dependencies": files_without_dependencies,
            "total_cycles": total_cycles,
            "total_missing_dependencies": total_missing_dependencies,
            "files_with_missing_dependencies": files_with_missing_dependencies,
            "total_references": total_references,
            "average_dependencies": round(average_dependencies, 2),
            "files_in_cycles": total_files_in_cycles,
            "cycle_file_ratio": round(cycle_file_ratio, 4),
            "dependency_density": round(dependency_density, 4)
        }

        return metrics

    def calculate_technical_debt_score(self, metrics):
        """
        Calcule un score heuristique de dette technique
        basé sur les dépendances.
        """

        # Facteur M : proportion de dépendances manquantes
        total_references = metrics["total_references"]

        missing_ratio = (
            metrics["total_missing_dependencies"] / total_references
            if total_references > 0 else 0
        )

        # Facteur C : proportion de fichiers impliqués dans des cycles
        cycle_ratio = metrics["cycle_file_ratio"]

        # Facteur D : densité des dépendances
        density = metrics["dependency_density"]

        # Calcul du score
        score = 100 * (
                0.4 * missing_ratio
                + 0.4 * cycle_ratio
                + 0.2 * density
        )

        return {
            "missing_ratio": round(missing_ratio, 4),
            "cycle_ratio": round(cycle_ratio, 4),
            "dependency_density": round(density, 4),
            "debt_score": round(score, 2)
        }

        def visualize_dependency_graph(self, graph, output_path, language="Python"):
        # 1. Créer un graphe orienté
           G = nx.DiGraph()

        # 2. Ajouter les fichiers et leurs dépendances
        for source, dependencies in graph.items():

            G.add_node(source)

            for dependency in dependencies:
                G.add_edge(source, dependency)

        # Vérifier si le graphe est vide
        if G.number_of_nodes() == 0:
            print("Aucun fichier à visualiser.")
            return

        # 3. Définir la taille de la figure
        plt.figure(figsize=(14, 10))

        # 4. Organiser automatiquement les nœuds
        pos = nx.spring_layout(G, seed=42, k=1.2)

        # 5. Dessiner les nœuds
        nx.draw_networkx_nodes(
            G,
            pos,
            node_color="#DCEAFE",
            node_size=2500,
            edgecolors="#3478c0"
        )

        # 6. Dessiner les flèches
        nx.draw_networkx_edges(
            G,
            pos,
            arrows=True,
            arrowstyle="-|>",
            arrowsize=20,
            edge_color="#64748b",
            connectionstyle="arc3,rad=0.08"
        )

        # 7. Afficher les noms des fichiers
        nx.draw_networkx_labels(
            G,
            pos,
            font_size=8,
            font_weight="bold"
        )
        plt.title(f"Graphe de dépendances {language}")
        plt.axis("off")
        plt.tight_layout()

        # 8. Enregistrer l'image
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        plt.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight"
        )

        print(f"Graphe enregistré : {output_path}")

        # 9. Afficher le graphe
        plt.show()
        plt.close()


    def visualize_dependency_graph(
        self, graph, output_path, language="Python"
    ):

        G = nx.DiGraph()

        for source, dependencies in graph.items():
            G.add_node(source)

            for dependency in dependencies:
                G.add_edge(source, dependency)

        if G.number_of_nodes() == 0:
            print("Aucun fichier à visualiser.")
            return

        plt.figure(figsize=(14, 10))

        pos = nx.spring_layout(G, seed=42, k=1.2)

        nx.draw_networkx_nodes(
            G, pos,
            node_color="#DCEAFE",
            node_size=2500,
            edgecolors="#3478c0"
        )

        nx.draw_networkx_edges(
            G, pos,
            arrows=True,
            arrowstyle="-|>",
            arrowsize=20,
            edge_color="#64748b",
            connectionstyle="arc3,rad=0.08"
        )

        nx.draw_networkx_labels(
            G, pos,
            font_size=8,
            font_weight="bold"
        )

        plt.title(f"Graphe de dépendances {language}")
        plt.axis("off")
        plt.tight_layout()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        plt.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight"
        )

        print(f"Graphe enregistré : {output_path}")

        plt.show()
        plt.close()