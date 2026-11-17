"""Le comparatif sans modèle : les règles seules, sur le vrai corpus."""
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
    from pathlib import Path

    import pytest
    if not Path("plugins/php_analyzer/vendor/autoload.php").exists():
        pytest.skip("composer install non fait dans plugins/php_analyzer")

    rows = {r["fichier"]: r for r in run_benchmark(
        ["blog", "legacy_db"], ["rules_only"], language="php")}
    # blog : la fonction str_contains du programme existe en natif -> erreur de compilation
    assert rows["blog"]["syntaxe"] is False
    assert rows["blog"]["resultat_attendu"] is False
    # legacy_db : __autoload() est supprimée -> erreur de compilation
    assert rows["legacy_db"]["syntaxe"] is False
    assert rows["legacy_db"]["s_execute"] is None      # pas exécutable (base de données)
    assert all(r["appels"] == 0 for r in rows.values())
