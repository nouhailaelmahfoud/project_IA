"""Tests du frontend : calculs du tableau de bord et génération du PDF."""
from frontend.metrics import dashboard
from frontend.report_pdf import build_report


def _job():
    ok = {"written": True, "approved": True, "rolled_back": False, "errors": [], "iterations": 1,
          "llm_calls": 0, "tokens_in": 0, "tokens_out": 0, "log": ["règles appliquées"],
          "original_code": "print 'a'", "migrated_code": "print('a')"}
    bad = {**ok, "approved": False, "errors": ["SyntaxError ligne 3"], "log": ["échec"]}
    return {"job_id": "abc", "language": "python", "status": "done",
            "issues": [{"file_path": "x/a.py", "line": 1}, {"file_path": "x/a.py", "line": 2},
                       {"file_path": "x/b.py", "line": 5}],
            "result": {"mode": "rules_only", "files": {"a.py": ok, "b.py": bad}}}


def test_dashboard_compte_les_problemes_corriges():
    stats = dashboard(_job(), min_per_issue=10, min_review=3)
    assert stats["files_ok"] == 1 and stats["files_total"] == 2
    assert stats["issues_total"] == 3 and stats["issues_fixed"] == 2
    assert stats["errors_remaining"] == 1
    assert stats["minutes_saved"] == 2 * 10 - 2 * 3


def test_rapport_pdf_est_un_pdf():
    assert build_report(_job(), 10, 3).startswith(b"%PDF")
