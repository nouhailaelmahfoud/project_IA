import json
import sys
from pathlib import Path

from plugins.python_analyzer.python_plugin import PythonPlugin


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "samples/legacy"
    issues = PythonPlugin().analyze_project(project_dir)

    for issue in issues:
        print(f"{issue.file_path}:{issue.line}  [{issue.severity.upper()}] "
              f"{issue.rule_id}  {issue.code_snippet}")

    out = Path("samples/py2_issues_real.json")
    out.write_text(
        json.dumps(
            {"language": "python", "issues": [i.to_dict() for i in issues]},
            indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(f"\n{len(issues)} problèmes -> {out}")


if __name__ == "__main__":
    main()