"""Support PHP : validation, détecteurs, règles et pipeline (avec un faux modèle)."""
from pathlib import Path

import pytest

from agents import php_support
from agents.graph import run_pipeline
from agents.validation import validate_code
from test_pipeline import APPROVED, FakeLLM, edit

PLUGIN_PRET = Path("plugins/php_analyzer/vendor/autoload.php").exists()
besoin_du_plugin = pytest.mark.skipif(
    not PLUGIN_PRET, reason="composer install non fait dans plugins/php_analyzer")
besoin_de_rector = pytest.mark.skipif(
    not php_support.RECTOR.exists(), reason="Rector non installé (tools/rector)")

SOURCE = (
    "<?php\n"
    "function lire($ligne) {\n"
    "    while (list($cle, $valeur) = each($ligne)) {\n"
    "        echo $cle;\n"
    "    }\n"
    "}\n"
)
AVANT = "    while (list($cle, $valeur) = each($ligne)) {"
APRES = "    foreach ($ligne as $cle => $valeur) {"


def ecrire(tmp_path):
    chemin = tmp_path / "lire.php"
    chemin.write_text(SOURCE, encoding="utf-8")
    return chemin


def test_php_valide_est_accepte():
    assert validate_code("php", "<?php\necho 1;\n") == []


def test_accolades_refusees_par_php_l():
    erreurs = validate_code("php", "<?php\n$t = 'abc';\necho $t{0};\n")
    assert len(erreurs) == 1
    assert "curly braces" in erreurs[0] and "line 3" in erreurs[0]


def test_fonction_deja_native_refusee_par_php_l():
    erreurs = validate_code("php", "<?php\nfunction str_contains($a, $b) { return true; }\n")
    assert "Cannot redeclare str_contains" in erreurs[0]


def test_regles_php_sans_rector(monkeypatch):
    monkeypatch.setattr(php_support, "RECTOR", Path("/introuvable/rector"))
    resultat = php_support.apply_php_rules(SOURCE)
    assert resultat.code == SOURCE and resultat.changed is False
    assert "Rector n'est pas installé" in resultat.warnings[0]


@besoin_de_rector
def test_rector_convertit_each_en_foreach():
    resultat = php_support.apply_php_rules(SOURCE)
    assert resultat.changed is True
    assert "foreach" in resultat.code and "each(" not in resultat.code


@besoin_du_plugin
def test_detecteurs_php():
    code = "<?php\nfunction f($r) {\n    $x = each($r);\n    return mysql_query('SELECT 1');\n}\n"
    risques = {r["kind"]: r for r in php_support.detect_php_risks(code)}
    assert risques["PHP8_EACH"]["line"] == 3 and risques["PHP8_EACH"]["blocking"] is True
    assert "PHP7_MYSQL_API" in risques


@besoin_du_plugin
def test_pipeline_php_hybride(tmp_path, monkeypatch):
    monkeypatch.setattr(php_support, "RECTOR", Path("/introuvable/rector"))  # pas de règles
    llm = FakeLLM([edit(AVANT, APRES), APPROVED])
    etat = run_pipeline(ecrire(tmp_path), "php", "hybrid", llm)
    assert etat["llm_calls"] == 2                  # Migrateur + Reviewer
    assert "foreach" in etat["current_code"] and "each(" not in etat["current_code"]
    assert etat["approved"] is True and not etat["rolled_back"]
    assert "PHP 7 vers PHP 8" in llm.prompts[0]    # la consigne PHP a bien été chargée
