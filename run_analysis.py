"""Lance un plugin d'analyse sur un dossier et écrit le rapport JSON.

Usage :
    python3 run_analysis.py python samples/py2_corpus
    python3 run_analysis.py php samples/php7
"""
import json
import sys
from pathlib import Path


def load_plugin(language):
    if language == "python":
        from plugins.python_analyzer.python_plugin import PythonPlugin
        return PythonPlugin()
    if language == "php":
        from plugins.php_analyzer.php_plugin import PhpPlugin
        return PhpPlugin()
    raise SystemExit(f"Langage inconnu : {language} (python ou php)")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)

    language, project_dir = sys.argv[1], sys.argv[2]
    issues = load_plugin(language).analyze_project(project_dir)

    for issue in issues:
        print(f"{issue.file_path}:{issue.line}  [{issue.severity.upper()}] "
              f"{issue.rule_id}  {issue.code_snippet}")

    output = Path("samples") / f"issues_{language}.json"
    output.write_text(
        json.dumps(
            {"language": language, "issues": [i.to_dict() for i in issues]},
            indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(f"\n{len(issues)} problèmes -> {output}")


if __name__ == "__main__":
    main()