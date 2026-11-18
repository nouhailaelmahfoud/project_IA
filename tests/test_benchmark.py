"""Le comparatif sans modèle : les règles seules, sur le vrai corpus."""
from pathlib import Path

import pytest

from agents import php_support
from eval.run_benchmark import run_benchmark


def test_regles_seules_sur_le_corpus():
    rows = {r["fichier"]: r for r in run_benchmark(
        ["inventory", "bank", "textstats"], ["rules_only"])}

    # inventory : s'exécute, mais le prix moyen change (2.5 au lieu de 2)
    assert rows["inventory"]["s_execute"] is True
    assert rows["inventory"]["resultat_attendu"] is False
    # bank et textstats : les pièges restent, le code plante
    assert rows["bank"]["s_execute"] is False
    assert rows["textstats"]["s_execute"] is False
    assert rows["bank"]["pieges_bloquants"] == 3      # __cmp__, cmp() et __unicode__
    assert all(r["appels"] == 0 for r in rows.values())


def test_regles_seules_sur_le_corpus_php():
    if not Path("plugins/php_analyzer/vendor/autoload.php").exists():
        pytest.skip("composer install non fait dans plugins/php_analyzer")

    rows = {r["fichier"]: r for r in run_benchmark(
        ["blog", "legacy_db"], ["rules_only"], language="php")}
    # legacy_db : __autoload() est supprimée -> erreur de compilation, base de données requise
    assert rows["legacy_db"]["syntaxe"] is False
    assert rows["legacy_db"]["s_execute"] is None
    assert all(r["appels"] == 0 for r in rows.values())
    # blog : avec Rector, les règles (dont « fonction déjà native ») suffisent
    if php_support.RECTOR.exists():
        assert rows["blog"]["syntaxe"] is True
        assert rows["blog"]["resultat_attendu"] is True
