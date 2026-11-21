"""Tests de la Tâche 3 SANS Docker : un faux exécuteur lance Python en local."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from agents.graph import run_pipeline
from agents.validation import validate_code
from test_pipeline import APPROVED, RISK, FakeLLM, migration
from verification import characterization as char
from verification import engine, metrics, runner
from verification.static_analysis import analyze


class FakeDocker:
    """Remplace runner.run_in_docker : exécute `python` en local, sans Docker.

    `tools` permet d'imposer la sortie d'un outil (ruff, phpstan...) : {"ruff": RunResult}.
    """

    def __init__(self, tools=None):
        self.tools = tools or {}
        self.calls = []

    def __call__(self, language, side, files, command, timeout=30, memory="256m", cpus="1"):
        self.calls.append((language, side, command))
        if command[0] in self.tools:
            return self.tools[command[0]]
        if command[0] != "python":
            return runner.RunResult(True, "", "", 0)  # outil d'analyse : tout va bien
        command = [sys.executable] + [a for a in command[1:] if not a.startswith("--cov")]
        with tempfile.TemporaryDirectory() as folder:
            for name, content in files.items():
                (Path(folder) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(folder) / name).write_text(content, encoding="utf-8")
            run = subprocess.run(command, capture_output=True, text=True,
                                 cwd=folder, timeout=60)
        return runner.RunResult(run.returncode == 0, run.stdout, run.stderr, run.returncode)


@pytest.fixture
def docker(monkeypatch):
    fake = FakeDocker()
    monkeypatch.setattr(runner, "run_in_docker", fake)
    monkeypatch.setattr(runner, "docker_available", lambda: True)
    return fake


def fail(text="boom"):
    return runner.RunResult(False, "", text, 1)


# ------------------------------------------------------------ validate_code

def test_validate_code_sans_verify_reste_comme_avant():
    assert validate_code("python", "print(1)\n") == []
    assert "Erreur de syntaxe" in validate_code("python", "def f(:\n")[0]


def test_validate_code_avec_verify_remplit_les_details(docker):
    details = {}
    errors = validate_code("python", "print(1)\n", original="print(1)\n",
                           file_path="a.py", verify=True, details=details)
    assert errors == []
    assert details["metrics"]["behaviour_ok"] is True


# ------------------------------------------------------------------ verify()

def test_docker_absent_ne_bloque_pas(monkeypatch):
    monkeypatch.setattr(runner, "docker_available", lambda: False)
    result = engine.verify("python", "print(1)", "print(1)", "a.py")
    assert result["errors"] == []
    assert result["metrics"]["skipped"] is True
    assert "Docker indisponible" in result["warnings"][0]


def test_meme_comportement(docker):
    result = engine.verify("python", "print(2 + 2)\n", "print(4)\n", "calc.py")
    assert result["errors"] == []
    assert result["metrics"]["behaviour_ok"] is True
    # l'original tourne dans l'ancien environnement, le migré dans le nouveau
    sides = [(side, cmd[0]) for _, side, cmd in docker.calls if cmd[0] == "python"]
    assert sides == [("legacy", "python"), ("modern", "python")]


def test_comportement_different(docker):
    result = engine.verify("python", "print(5 / 2)\n", "print(5 // 2)\n", "calc.py")
    assert result["metrics"]["behaviour_ok"] is False
    assert "Comportement différent" in result["errors"][0]


def test_code_migre_qui_plante(docker):
    result = engine.verify("python", "print(1)\n", "raise ValueError('x')\n", "a.py")
    assert "ne s'exécute pas" in result["errors"][0]


def test_original_non_executable_n_est_pas_compare(docker):
    result = engine.verify("python", "raise SystemExit(3)\n", "print(1)\n", "a.py")
    assert result["errors"] == []
    assert result["metrics"]["golden_usable"] is False
    assert result["metrics"]["behaviour_ok"] is None


def test_erreur_statique_bloque_avant_l_execution(monkeypatch, docker):
    docker.tools["ruff"] = fail("a.py:3:1: F821 Undefined name `cmp`")
    result = engine.verify("python", "print(1)\n", "print(cmp(1, 2))\n", "a.py")
    assert any("F821" in e for e in result["errors"])
    assert result["metrics"]["static_errors"] == 1
    assert "behaviour_ok" not in result["metrics"]  # pas d'exécution inutile


def test_pylint_et_mypy_sont_des_avertissements(docker):
    docker.tools["pylint"] = fail("a.py:1:0: E1101: no-member")
    docker.tools["mypy"] = fail("a.py:2: error: incompatible types")
    result = engine.verify("python", "print(1)\n", "print(1)\n", "a.py")
    assert result["errors"] == []
    assert result["metrics"]["static_warnings"] == 2


def test_phpstan_bloque_seulement_les_fonctions_disparues(docker):
    docker.tools["phpstan"] = fail(
        "x.php:3:Call to undefined function mysql_connect().\n"
        "x.php:5:Variable $a might not be defined.")
    result = analyze("php", "<?php\n", "x.php")
    assert len(result["errors"]) == 1 and "mysql_connect" in result["errors"][0]
    assert len(result["warnings"]) == 1


def test_tests_generes_qui_echouent(docker):
    tests = "def test_x():\n    assert 1 == 2\n"
    result = engine.verify("python", "x = 1\n", "x = 1\n", "m.py", tests)
    assert result["metrics"]["tests_passed"] is False
    assert any("Tests de caractérisation en échec" in e for e in result["errors"])


def test_tests_generes_qui_passent(docker):
    tests = "import m\n\ndef test_x():\n    assert m.x == 1\n"
    result = engine.verify("python", "x = 1\n", "x = 1\n", "m.py", tests)
    assert result["errors"] == []
    assert result["metrics"]["tests_passed"] is True

def test_artefacts_python2_ne_comptent_pas_comme_difference():
    assert char.python2_artifacts("21 300L") == "21 300"
    assert char.python2_artifacts("[u'a', u\"b\"]") == "['a', \"b\"]"
    assert char.python2_artifacts("version 2L3 et ABCL") == "version 2L3 et ABCL"


def test_golden_python_ignore_le_suffixe_long(docker):
    golden = char.record_golden("python", "a.py", "print('x = 300L')\n")
    assert golden["stdout"] == "x = 300"

def test_en_tete_des_tests_python_est_corrige():
    brut = ("import pytest\nfrom __future__ import print_function\n\n"
            "def test_x():\n    assert Inventory() is not None\n")
    corrige = char.fix_test_header(brut, "inventory")
    assert corrige.startswith("from __future__ import print_function\n")
    assert "from inventory import *" in corrige
    deja = char.fix_test_header("import inventory\n\ndef test_x():\n    pass\n", "inventory")
    assert "from inventory import *" not in deja

def test_parse_coverage():
    sortie = ("Name    Stmts   Miss  Cover\n----\nm.py       10      2    80%\n"
              "TOTAL      10      2    80%\n")
    assert char.parse_coverage("python", "m.py", sortie) == 80
    assert char.parse_coverage("python", "m.py", "Name\nTOTAL 4 1 75%\n") == 75
    assert char.parse_coverage("php", "m.php", " Lines:   66.67% (2/3)") == 66.67
    assert char.parse_coverage("python", "m.py", "rien") is None


# ------------------------------------------------- tests écrits par le LLM

def test_prepare_tests_corrige_puis_valide(docker):
    mauvais = "```python\ndef test_x():\n    assert 1 == 2\n```"
    bon = "```python\nimport m\n\ndef test_x():\n    assert m.x == 1\n```"
    llm = FakeLLM([mauvais, bon])
    result = engine.prepare_tests(llm, "python", "m.py", "x = 1\n")
    assert "assert m.x == 1" in result["tests"]
    assert result["llm_calls"] == 2
    assert "échouent sur le code ORIGINAL" in llm.prompts[1]  # l'échec est renvoyé au modèle

def test_prepare_tests_garde_les_tests_qui_passent(docker):
    melange = ("```python\nimport m\n\ndef test_bon():\n    assert m.x == 1\n\n"
               "def test_faux():\n    assert m.x == 2\n```")
    result = engine.prepare_tests(FakeLLM([melange]), "python", "m.py", "x = 1\n")
    assert "test_bon" in result["tests"] and "test_faux" not in result["tests"]
    assert result["llm_calls"] == 1

def test_garde_les_tests_php_qui_passent():
    tests = ("<?php\nclass GeneratedTest extends PHPUnit\\Framework\\TestCase\n{\n"
             "    public function testBon()\n    {\n        $this->assertTrue(true);\n    }\n\n"
             "    public function testFaux()\n    {\n        $this->assertTrue(false);\n    }\n}\n")
    rapport = "There was 1 failure:\n\n1) GeneratedTest::testFaux\nFailed asserting that false is true.\n"
    garde = char.keep_passing_tests(tests, rapport, "php")
    assert "testBon" in garde and "testFaux" not in garde
    assert garde.count("{") == garde.count("}")


def test_prepare_tests_abandonne_apres_deux_echecs(docker):
    mauvais = "```python\ndef test_x():\n    assert False\n```"
    result = engine.prepare_tests(FakeLLM([mauvais, mauvais]), "python", "m.py", "x = 1\n")
    assert result["tests"] == ""
    assert "aucun jeu de tests valide" in result["log"][-1]


# ---------------------------------------------- intégration dans le pipeline

SOURCE = "def avg(a, b):\n    return (a + b) / 2\n\nprint avg(2, 3)\n"
FIXED = "def avg(a, b):\n    return (a + b) // 2\n\nprint(avg(2, 3))\n"


def test_pipeline_renvoie_les_erreurs_de_verification_au_migrateur(monkeypatch, tmp_path):
    appels = []

    def fausse_verification(language, original, migrated, file_path, tests=""):
        appels.append(migrated)
        if len(appels) == 1:
            return {"errors": ["Comportement différent de l'original"],
                    "warnings": ["mypy : un avertissement"], "metrics": {"skipped": False}}
        return {"errors": [], "warnings": [],
                "metrics": {"skipped": False, "behaviour_ok": True}}

    monkeypatch.setattr("verification.engine.verify", fausse_verification)
    source = tmp_path / "avg.py"
    source.write_text(SOURCE, encoding="utf-8")
    llm = FakeLLM([RISK, migration(FIXED), migration(FIXED), APPROVED])

    state = run_pipeline(source, "python", "llm_only", llm, use_detectors=False,
                         verify=True, max_iterations=3)

    assert len(appels) == 2
    assert "Comportement différent de l'original" in llm.prompts[2]  # 2e tour du Migrateur
    assert state["iteration"] == 2 and state["errors"] == []
    assert state["verification"]["metrics"]["behaviour_ok"] is True


def test_pipeline_sans_verify_n_appelle_pas_le_moteur(monkeypatch, tmp_path):
    monkeypatch.setattr("verification.engine.verify",
                        lambda *a, **k: pytest.fail("ne doit pas être appelé"))
    source = tmp_path / "avg.py"
    source.write_text(SOURCE, encoding="utf-8")
    state = run_pipeline(source, "python", "rules_only", None)
    assert state["verification"] == {}


# ------------------------------------------------------------------ métriques

def test_metriques_et_rapport(tmp_path):
    base = {"file_path": "a.py", "language": "python", "mode": "hybrid",
            "iteration": 2, "rolled_back": False, "errors": [],
            "verification": {"warnings": ["w"], "metrics": {
                "skipped": False, "behaviour_ok": True, "tests_run": True,
                "tests_passed": True, "coverage": 80, "static_errors": 0}}}
    ko = dict(base, file_path="b.py", iteration=3, errors=["x"],
              verification={"metrics": {"skipped": False, "coverage": 40}})
    records = [metrics.record_from_state(base), metrics.record_from_state(ko)]
    resume = metrics.summarize(records)
    assert resume["taux_reussite_pct"] == 50.0
    assert resume["iterations_moyennes"] == 2.5
    assert resume["couverture_moyenne_pct"] == 60.0
    json_path, md_path = metrics.save_report(records, tmp_path, stamp="test")
    assert json.loads(json_path.read_text(encoding="utf-8"))["resume"]["fichiers"] == 2
    assert "| a.py |" in md_path.read_text(encoding="utf-8")