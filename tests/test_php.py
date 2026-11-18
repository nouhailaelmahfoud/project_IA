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


@pytest.fixture
def sans_rector(monkeypatch):
    monkeypatch.setattr(php_support, "RECTOR", Path("/introuvable/rector"))


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


def test_regles_php_sans_rector(sans_rector):
    resultat = php_support.apply_php_rules(SOURCE)
    assert resultat.code == SOURCE and resultat.changed is False
    assert "Rector n'est pas installé" in resultat.warnings[0]


# ------------------------------------------- règle « fonction déjà native »
POLYFILL = (
    "<?php\n"
    "function str_contains($a, $b) {\n"
    "    $x = \"}\"; // une accolade dans une chaîne et un commentaire }\n"
    "    return strpos($a, $b) !== false;\n"
    "}\n"
    "echo \"ok\";\n"
)


def test_regle_retire_une_fonction_deja_native(sans_rector):
    resultat = php_support.apply_php_rules(POLYFILL)
    assert "function str_contains" not in resultat.code
    assert 'echo "ok";' in resultat.code
    assert any("str_contains() supprimée" in w for w in resultat.warnings)
    assert validate_code("php", resultat.code) == []


def test_regle_ne_touche_pas_une_methode_du_meme_nom(sans_rector):
    code = ("<?php\nclass A {\n    function str_contains($a) { return 1; }\n}\n"
            "function str_contains($a, $b) { return true; }\n")
    resultat = php_support.apply_php_rules(code)
    assert "class A" in resultat.code and "function str_contains($a) { return 1; }" in resultat.code
    assert "function str_contains($a, $b)" not in resultat.code


def test_regle_ignore_un_doublon_du_programme(sans_rector):
    code = "<?php\nfunction f() { return 1; }\nfunction f() { return 2; }\n"
    resultat = php_support.apply_php_rules(code)
    assert resultat.code == code and resultat.changed is False


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
def test_pipeline_php_hybride(tmp_path, sans_rector):
    llm = FakeLLM([edit(AVANT, APRES), APPROVED])
    etat = run_pipeline(ecrire(tmp_path), "php", "hybrid", llm)
    assert etat["llm_calls"] == 2                  # Migrateur + Reviewer
    assert "foreach" in etat["current_code"] and "each(" not in etat["current_code"]
    assert etat["approved"] is True and not etat["rolled_back"]
    assert "PHP 7 vers PHP 8" in llm.prompts[0]    # la consigne PHP a bien été chargée


@besoin_du_plugin
def test_le_reviewer_garde_la_parole(tmp_path, sans_rector):
    """Aucune approbation forcée : un refus du Reviewer provoque un retour arrière."""
    refus = '{"approved": false, "problems": ["la boucle a changé de sens"]}'
    llm = FakeLLM([edit(AVANT, APRES), refus])
    etat = run_pipeline(ecrire(tmp_path), "php", "hybrid", llm, max_iterations=1)
    assert etat["approved"] is False and etat["rolled_back"] is True
