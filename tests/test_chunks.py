"""Découpage des gros fichiers : le modèle ne voit que les extraits utiles."""
from agents.chunks import (
    is_large, join_notes, large_note, lines_in_errors, merge_ranges,
    migrator_view, reviewer_excerpts, risk_windows,
)
from agents.graph import run_pipeline
from test_pipeline import APPROVED, FakeLLM, edit


def gros_fichier(taille=400, ligne_risquee=300):
    lignes = [f"x{n} = {n}" for n in range(1, taille + 1)]
    lignes[ligne_risquee - 1] = "result = cmp(a, b)"
    return "\n".join(lignes) + "\n"


def test_un_petit_fichier_reste_entier():
    code = "a = 1\nb = 2\n"
    assert not is_large(code)
    assert migrator_view(code, []) == code
    assert reviewer_excerpts(code, code + "c = 3\n") == (code, code + "c = 3\n")
    assert large_note(code) == "" and join_notes("deja", "") == "deja"


def test_les_fenetres_proches_sont_fusionnees():
    code = gros_fichier()
    risques = [{"line": 100}, {"line": 110}, {"line": 300}]
    assert risk_windows(code, risques) == [(88, 122), (288, 312)]


def test_lignes_citees_dans_les_erreurs():
    erreurs = ["Fatal error: Cannot redeclare str_contains() in code.php on line 5",
               "Il reste à la ligne 18 : méthode __cmp__", "Erreur de syntaxe, ligne 7"]
    assert lines_in_errors(erreurs) == [5, 18, 7]
    assert merge_ranges([(1, 5), (6, 9), (20, 30)]) == [(1, 9), (20, 30)]


def test_le_migrateur_ne_voit_que_les_extraits():
    code = gros_fichier()
    vue = migrator_view(code, [{"line": 300}])
    assert "[extrait : lignes 288 à 312 du fichier]" in vue
    assert "result = cmp(a, b)" in vue and "x5 = 5" not in vue
    assert len(vue) < len(code) / 3


def test_les_erreurs_de_validation_localisent_les_extraits():
    code = gros_fichier()
    vue = migrator_view(code, [], ["Fatal error: ... in code.php on line 50"])
    assert "[extrait : lignes 38 à 62 du fichier]" in vue


def test_le_reviewer_voit_les_parties_modifiees():
    avant = gros_fichier()
    apres = avant.replace("result = cmp(a, b)", "result = (a > b) - (a < b)")
    ancien, nouveau = reviewer_excerpts(avant, apres)
    assert "result = cmp(a, b)" in ancien and "result = (a > b) - (a < b)" in nouveau
    assert "Fichier long" in ancien and "x5 = 5" not in ancien and "x5 = 5" not in nouveau


def test_pipeline_sur_un_gros_fichier(tmp_path):
    chemin = tmp_path / "gros.py"
    chemin.write_text(gros_fichier(), encoding="utf-8")
    llm = FakeLLM([edit("result = cmp(a, b)", "result = (a > b) - (a < b)"), APPROVED])
    etat = run_pipeline(chemin, "python", "hybrid", llm)

    consigne_migrateur, consigne_reviewer = llm.prompts[0], llm.prompts[1]
    assert "Le fichier est long" in consigne_migrateur
    assert "result = cmp(a, b)" in consigne_migrateur and "x5 = 5" not in consigne_migrateur
    assert "Fichier long" in consigne_reviewer
    assert "x5 = 5" not in consigne_reviewer
    # la modification s'applique au fichier COMPLET, qui reste intact ailleurs
    assert "(a > b) - (a < b)" in etat["current_code"]
    assert "x5 = 5" in etat["current_code"] and "x399 = 399" in etat["current_code"]
    assert etat["approved"] is True and etat["llm_calls"] == 2
