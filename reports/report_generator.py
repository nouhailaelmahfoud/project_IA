
from collections import defaultdict
import json
from pathlib import Path
from html import escape


class ReportGenerator:

    # ==========================================
    # 1. RAPPORT TERMINAL

    def generate_terminal_report(self, results):

        print("\n")
        print("=" * 65)
        print("                 RAPPORT DE MIGRATION")
        print("=" * 65)

        if not results:
            print("\nAucune anomalie détectée.")
            return

        files_results = defaultdict(list)

        for result in results:
            files_results[result.file_path].append(result)

        for file_path, problems in files_results.items():

            print("\nFICHIER :", file_path)
            print("-" * 65)

            for problem in problems:
                print(f"\nLigne       : {problem.line}")
                print(f"Plugin      : {problem.plugin}")
                print(f"Règle       : {problem.rule_id}")
                print(f"Gravité     : {problem.severity.upper()}")
                print(f"Problème    : {problem.message}")
                print(f"Solution    : {problem.recommendation}")

        total = len(results)

        critical = sum(
            1 for r in results if r.severity.lower() == "critical"
        )

        high = sum(
            1 for r in results if r.severity.lower() == "high"
        )

        warning = sum(
            1 for r in results if r.severity.lower() == "warning"
        )

        print("\n")
        print("=" * 65)
        print("                 STATISTIQUES")
        print("=" * 65)

        print("Nombre total de problèmes :", total)
        print("Fichiers analysés          :", len(files_results))
        print("Problèmes critiques        :", critical)
        print("Problèmes élevés           :", high)
        print("Avertissements             :", warning)

        print("=" * 65)

    # ==========================================


    # ==========================================
    # 2. RAPPORT JSON
    # ==========================================

    def generate_json_report(self, results, output_path):

        problems = [result.to_dict() for result in results]

        total = len(results)

        critical = sum(
            1 for r in results if r.severity.lower() == "critical"
        )

        high = sum(
            1 for r in results if r.severity.lower() == "high"
        )

        warning = sum(
            1 for r in results if r.severity.lower() == "warning"
        )

        report = {
            "summary": {
                "total_problems": total,
                "files_analyzed": len(set(r.file_path for r in results)),
                "critical": critical,
                "high": high,
                "warning": warning
            },
            "problems": problems
        }

        output_path = Path(output_path)

        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(f"\nRapport JSON enregistré : {output_path}")

    # ==========================================
    # 3. RAPPORT HTML INTERACTIF
    # ==========================================

    def generate_html_report(self, results, output_path):

        total = len(results)

        critical = sum(
            1 for r in results if r.severity.lower() == "critical"
        )

        high = sum(
            1 for r in results if r.severity.lower() == "high"
        )

        warning = sum(
            1 for r in results if r.severity.lower() == "warning"
        )

        files_count = len(set(r.file_path for r in results))

        # Générer les lignes du tableau
        rows = ""

        for result in results:

            severity = result.severity.lower()

            if severity not in ["critical", "high", "warning"]:
                severity = "other"

            rows += f"""
                <tr>
                    <td>{escape(str(result.file_path))}</td>
                    <td>{result.line}</td>
                    <td>{escape(str(result.rule_id))}</td>
                    <td>
                        <span class="severity {severity}">
                            {escape(str(result.severity).upper())}
                        </span>
                    </td>
                    <td>{escape(str(result.message))}</td>
                    <td>{escape(str(result.recommendation))}</td>
                </tr>
            """

        # Construire la page HTML
        # IMPORTANT : les accolades CSS et JavaScript sont doublées
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">

            <title>Rapport de migration</title>

            <style>

                body {{
                    font-family: Arial, sans-serif;
                    margin: 30px;
                    background-color: #f4f6f9;
                    color: #333;
                }}

                h1 {{
                    text-align: center;
                    color: #263445;
                }}

                .statistics {{
                    display: flex;
                    gap: 15px;
                    flex-wrap: wrap;
                    margin: 30px 0;
                }}

                .card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    flex: 1;
                    min-width: 130px;
                    text-align: center;
                }}

                .card h2 {{
                    font-size: 28px;
                    margin: 5px;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: white;
                }}

                th, td {{
                    padding: 12px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}

                th {{
                    background-color: #263445;
                    color: white;
                }}

                tr:nth-child(even) {{
                    background-color: #f2f2f2;
                }}

                .severity {{
                    padding: 5px 8px;
                    border-radius: 5px;
                    font-weight: bold;
                }}

                .critical {{
                    background-color: #ffcccc;
                    color: #a00000;
                }}

                .high {{
                    background-color: #ffe0b2;
                    color: #995500;
                }}

                .warning {{
                    background-color: #fff3b0;
                    color: #806000;
                }}

                .other {{
                    background-color: #ddd;
                    color: #333;
                }}

                .table-container {{
                    overflow-x: auto;
                }}

                .filters {{
                    margin: 20px 0;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}

                .filters select {{
                    padding: 10px;
                    border-radius: 5px;
                    border: 1px solid #ccc;
                    cursor: pointer;
                    background-color: white;
                }}

            </style>

        </head>

        <body>

            <h1>Rapport de migration</h1>

            <div class="statistics">

                <div class="card">
                    <h2>{total}</h2>
                    <p>Total des problèmes</p>
                </div>

                <div class="card">
                    <h2>{files_count}</h2>
                    <p>Fichiers analysés</p>
                </div>

                <div class="card">
                    <h2>{critical}</h2>
                    <p>Problèmes critiques</p>
                </div>

                <div class="card">
                    <h2>{high}</h2>
                    <p>Problèmes élevés</p>
                </div>

                <div class="card">
                    <h2>{warning}</h2>
                    <p>Avertissements</p>
                </div>

            </div>

            <h2>Détails des anomalies</h2>

            <!-- FILTRE PAR GRAVITE -->

            <div class="filters">

                <label for="severityFilter">
                    Filtrer par gravité :
                </label>

                <select id="severityFilter" onchange="filterBySeverity()">

                    <option value="all">Toutes les anomalies</option>
                    <option value="critical">CRITICAL</option>
                    <option value="high">HIGH</option>
                    <option value="warning">WARNING</option>

                </select>

            </div>

            <!-- TABLEAU DES ANOMALIES -->

            <div class="table-container">

                <table>

                    <thead>
                        <tr>
                            <th>Fichier</th>
                            <th>Ligne</th>
                            <th>Règle</th>
                            <th>Gravité</th>
                            <th>Problème</th>
                            <th>Recommandation</th>
                        </tr>
                    </thead>

                    <tbody>
                        {rows}
                    </tbody>

                </table>

            </div>

            <!-- JAVASCRIPT : FILTRAGE -->

            <script>

                function filterBySeverity() {{

                    const selectedSeverity =
                        document.getElementById("severityFilter").value;

                    const rows = document.querySelectorAll("tbody tr");

                    rows.forEach(row => {{

                        const severity =
                            row.querySelector(".severity").textContent
                                .trim()
                                .toLowerCase();

                        if (
                            selectedSeverity === "all" ||
                            severity === selectedSeverity
                        ) {{
                            row.style.display = "";
                        }} else {{
                            row.style.display = "none";
                        }}

                    }});

                }}

            </script>

        </body>
        </html>
        """

        # Enregistrer le fichier HTML
        output_path = Path(output_path)

        with output_path.open("w", encoding="utf-8") as file:
            file.write(html_content)

        print(f"\nRapport HTML enregistré : {output_path}")



    # ==========================================
    # 4. RAPPORT DE DETTE TECHNIQUE PAR LANGAGE
    # ==========================================

    def generate_debt_report(
        self,
        language,
        metrics,
        debt_assessment,
        missing_dependencies,
        cycles,
        output_path
    ):

        report = {
            "language": language,

            "metrics": metrics,

            "debt_assessment": debt_assessment,

            "missing_dependencies": missing_dependencies,

            "cycles": cycles
        }

        output_path = Path(output_path)

        # Créer le dossier de destination s'il n'existe pas
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Enregistrer le rapport JSON
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(
            f"\nRapport de dette technique ({language}) "
            f"enregistré : {output_path}"
        )



    # ==========================================
    # 5. RAPPORT HTML DE DETTE TECHNIQUE
    # ==========================================

    def generate_debt_html_report(
        self,
        language,
        metrics,
        debt_assessment,
        missing_dependencies,
        cycles,
        output_path
    ):

        score = debt_assessment["debt_score"]

        # Construire les lignes des dépendances manquantes
        missing_rows = ""

        for source, dependencies in missing_dependencies.items():

            for dependency in dependencies:

                dependency_name = (
                    dependency.get("module")
                    or dependency.get("path")
                    or "Inconnue"
                )

                dependency_type = dependency.get("type", "-")
                line = dependency.get("line", "-")

                missing_rows += f"""
                    <tr>
                        <td>{escape(str(source))}</td>
                        <td>{escape(str(dependency_name))}</td>
                        <td>{escape(str(dependency_type))}</td>
                        <td>{escape(str(line))}</td>
                    </tr>
                """

        if not missing_rows:
            missing_rows = """
                <tr>
                    <td colspan="4">Aucune dépendance manquante</td>
                </tr>
            """

        # Construire les lignes des cycles
        cycle_rows = ""

        for index, cycle in enumerate(cycles, start=1):

            cycle_path = " → ".join(str(file) for file in cycle)

            cycle_rows += f"""
                <tr>
                    <td>{index}</td>
                    <td>{escape(cycle_path)}</td>
                </tr>
            """

        if not cycle_rows:
            cycle_rows = """
                <tr>
                    <td colspan="2">Aucun cycle détecté</td>
                </tr>
            """

        # Construire les lignes des indicateurs
        metric_rows = ""

        for name, value in metrics.items():

            metric_rows += f"""
                <tr>
                    <td>{escape(str(name))}</td>
                    <td>{escape(str(value))}</td>
                </tr>
            """

        # Traduction des facteurs de dette
        factor_labels = {
            "missing_ratio": "Taux de dépendances manquantes",
            "cycle_ratio": "Taux de fichiers impliqués dans des cycles",
            "dependency_density": "Densité des dépendances"
        }

        # Construire les lignes des facteurs de dette
        factor_rows = ""

        for name, value in debt_assessment.items():

            if name == "debt_score":
                continue

            label = factor_labels.get(name, name)

            factor_rows += f"""
                <tr>
                    <td>{escape(str(label))}</td>
                    <td>{escape(str(value))}</td>
                </tr>
            """

        # Barre de progression du score
        score_width = max(0, min(100, score))
        # Interprétation du score
        if score < 30:
            score_level = "Faible"
        elif score < 60:
            score_level = "Modérée"
        else:
            score_level = "Élevée"
        # Couleur selon le niveau de dette
        if score < 30:
            score_color = "#28a745"  # Vert
        elif score < 60:
            score_color = "#f0ad4e"  # Orange
        else:
            score_color = "#dc3545"  # Rouge
        # Générer le contenu HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">

        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1.0">

            <title>Dette technique - {escape(language)}</title>

            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 30px;
                    background: #f4f6f9;
                    color: #263445;
                }}

                h1, h2 {{
                    color: #263445;
                }}

                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}

                .score-card {{
                    background: white;
                    padding: 25px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 25px;
                }}

                .score {{
    font-size: 42px;
    font-weight: bold;
    margin: 10px;
    color: {score_color};
}}

                .progress {{
                    background: #e0e0e0;
                    height: 15px;
                    border-radius: 10px;
                    overflow: hidden;
                    margin-top: 15px;
                }}

                .progress-bar {{
                    background: #3478c0;
                    height: 100%;
                    width: {score_width}%;
                }}

                .statistics {{
                    display: grid;
                    grid-template-columns:
                        repeat(auto-fit, minmax(180px, 1fr));
                    gap: 15px;
                    margin-bottom: 30px;
                }}

                .card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                }}

                .card h3 {{
                    font-size: 25px;
                    margin: 10px;
                }}

                .section {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 25px;
                }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}

                th, td {{
                    padding: 12px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}

                th {{
                    background: #263445;
                    color: white;
                }}

                tr:nth-child(even) {{
                    background: #f2f2f2;
                }}

                .table-container {{
                    overflow-x: auto;
                }}
            </style>
        </head>

        <body>

            <div class="header">
                <h1>Rapport de dette technique</h1>
                <h2>Langage : {escape(language)}</h2>
            </div>

            <div class="score-card">
                <h2>Score global de dette technique</h2>

                <div class="score">
    {score:.2f} / 100
</div>

<p>
    Niveau de dette technique :
    <strong style="color: {score_color};">
        {score_level}
    </strong>
</p>

                <div class="progress">
                    <div class="progress-bar"></div>
                </div>
            </div>

            <h2>Indicateurs principaux</h2>

            <div class="statistics">

    <div class="card">
        <h3>{metrics["total_files"]}</h3>
        <p>Fichiers analysés</p>
    </div>

    <div class="card">
        <h3>{metrics["total_dependencies"]}</h3>
        <p>Dépendances existantes</p>
    </div>

    <div class="card">
        <h3>{metrics["files_with_dependencies"]}</h3>
        <p>Fichiers avec dépendances</p>
    </div>

    <div class="card">
        <h3>{metrics["files_without_dependencies"]}</h3>
        <p>Fichiers sans dépendances</p>
    </div>

    <div class="card">
        <h3>{metrics["average_dependencies"]:.2f}</h3>
        <p>Moyenne des dépendances par fichier</p>
    </div>

    <div class="card">
        <h3>{metrics["total_missing_dependencies"]}</h3>
        <p>Dépendances manquantes</p>
    </div>

    <div class="card">
        <h3>{metrics["total_cycles"]}</h3>
        <p>Cycles détectés</p>
    </div>

</div>

            <div class="section">
                <h2>Facteurs de dette technique</h2>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Facteur</th>
                                <th>Valeur</th>
                            </tr>
                        </thead>

                        <tbody>
                            {factor_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2>Ensemble des indicateurs</h2>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Indicateur</th>
                                <th>Valeur</th>
                            </tr>
                        </thead>

                        <tbody>
                            {metric_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2>Dépendances manquantes</h2>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Fichier source</th>
                                <th>Dépendance</th>
                                <th>Type</th>
                                <th>Ligne</th>
                            </tr>
                        </thead>

                        <tbody>
                            {missing_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2>Cycles de dépendances</h2>

                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Numéro</th>
                                <th>Chemin du cycle</th>
                            </tr>
                        </thead>

                        <tbody>
                            {cycle_rows}
                        </tbody>
                    </table>
                </div>
            </div>

        </body>
        </html>
        """

        # Enregistrer le rapport HTML
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as file:
            file.write(html_content)

        print(
            f"\nRapport HTML de dette technique ({language}) "
            f"enregistré : {output_path}"
        )
