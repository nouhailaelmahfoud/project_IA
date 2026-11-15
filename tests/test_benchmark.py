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
