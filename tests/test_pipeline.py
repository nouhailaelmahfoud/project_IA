"""Tests du pipeline avec un FAUX modèle : aucun appel réseau, aucun quota."""
import json

from agents.graph import run_pipeline as _run_pipeline


def run_pipeline(*args, **kwargs):
    """Les anciens tests visent l'Analyseur LLM : on coupe les détecteurs."""
    kwargs.setdefault("use_detectors", False)
    return _run_pipeline(*args, **kwargs)


SOURCE = "def avg(a, b):\n    return (a + b) / 2\n\nprint avg(2, 3)\n"
FIXED = "def avg(a, b):\n    return (a + b) // 2\n\nprint(avg(2, 3))\n"


class FakeResponse:
    def __init__(self, content):
        self.content = content
        self.usage_metadata = {"input_tokens": 10, "output_tokens": 5}


class FakeLLM:
    """Renvoie des réponses préparées, dans l'ordre."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return FakeResponse(self.replies.pop(0))


RISK = json.dumps({"risks": [{"line": 2, "code": "return (a + b) / 2", "description": "division entière", "suggestion": "utiliser //"}]})
NO_RISK = json.dumps({"risks": []})
APPROVED = json.dumps({"approved": True, "problems": []})
REJECTED = json.dumps({"approved": False, "problems": ["la division a changé"]})


def migration(code):
    """Réponse du Migrateur au format demandé : balises <changes> et <code>."""
    return "<changes>\n- division entière\n</changes>\n<code>\n" + code + "</code>"


def migration_json(code):
    return json.dumps({"code": code, "changes": ["division entière"]})


def write_source(tmp_path):
    path = tmp_path / "avg.py"
    path.write_text(SOURCE, encoding="utf-8")
    return path


def test_rules_only_n_appelle_pas_le_modele(tmp_path):
    llm = FakeLLM([])
    state = run_pipeline(write_source(tmp_path), "python", "rules_only", llm)
    assert llm.prompts == []
    assert state["llm_calls"] == 0
    assert "print(avg(2, 3))" in state["current_code"]
    assert state["errors"] == []


def test_hybride_sans_risque_s_arrete_apres_l_analyseur(tmp_path):
    llm = FakeLLM([NO_RISK])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["llm_calls"] == 1
    assert state["iteration"] == 0


def test_hybride_complet(tmp_path):
    llm = FakeLLM([RISK, migration(FIXED), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["llm_calls"] == 3
    assert state["approved"] is True
    assert "// 2" in state["current_code"]
    assert state["tokens_in"] == 30


def test_boucle_apres_erreur_de_syntaxe(tmp_path):
    llm = FakeLLM([RISK, migration("def avg(:\n"), migration(FIXED), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["iteration"] == 2
    assert state["approved"] is True
    # le deuxième appel du Migrateur a reçu l'erreur de syntaxe
    assert "Erreur de syntaxe" in llm.prompts[2]


def test_boucle_apres_refus_du_reviewer(tmp_path):
    llm = FakeLLM([RISK, migration(FIXED), REJECTED, migration(FIXED), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["iteration"] == 2
    assert "la division a changé" in llm.prompts[3]


def test_arret_apres_le_nombre_maximal_de_tours(tmp_path):
    bad = migration("def avg(:\n")
    llm = FakeLLM([RISK, bad, bad, bad])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm, max_iterations=3)
    assert state["iteration"] == 3
    assert state["errors"]


def test_reponse_avec_texte_autour_et_bloc_de_code(tmp_path):
    fence = "`" * 3
    texte = "Voici le résultat :\n" + fence + "python\n" + FIXED + fence + "\n"
    llm = FakeLLM([RISK, texte, APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert "// 2" in state["current_code"]


def test_llm_only_migre_sans_les_regles(tmp_path):
    llm = FakeLLM([RISK, migration(FIXED), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "llm_only", llm)
    assert state["llm_calls"] == 3
    assert "règles : ignorées" in " ".join(state["log"])


def test_migrateur_accepte_aussi_le_json(tmp_path):
    llm = FakeLLM([RISK, migration_json(FIXED), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert "// 2" in state["current_code"]


def test_balises_avec_apostrophes_inversees_a_l_interieur(tmp_path):
    fence = "`" * 3
    reponse = "<code>\n" + fence + "python\n" + FIXED + fence + "\n</code>"
    llm = FakeLLM([RISK, reponse, APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert "// 2" in state["current_code"]
    assert fence not in state["current_code"]


def test_reponse_tronquee_est_illisible_et_sauvegardee(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tronquee = "<code>\ndef avg(a, b):\n    return (a + b)"  # pas de </code>
    llm = FakeLLM([RISK, tronquee, tronquee, tronquee])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["errors"]
    assert (tmp_path / "output" / "debug" / "avg_migrator_1.txt").exists()


TRUNCATED_RISK = '{"risks": [{"line": 12, "code": "return (a + b) / 2", "description": "division entière", "suggestion": "util'


def test_json_coupe_est_repare_pour_l_analyseur(tmp_path):
    llm = FakeLLM([TRUNCATED_RISK, migration(FIXED), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["llm_calls"] == 3
    assert "division entière" in llm.prompts[1]  # le Migrateur a reçu le risque


def test_analyseur_reessaie_une_fois(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    llm = FakeLLM(["n'importe quoi", RISK, migration(FIXED), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["llm_calls"] == 4
    assert "ATTENTION" in llm.prompts[1]
    assert state["approved"] is True


def test_json_coupe_jamais_accepte_pour_le_migrateur():
    from agents.llm_utils import parse_migration
    code, _ = parse_migration('{"code": "def f(", "changes": ["x"')
    assert code is None


# ----------------------------------------------------- modifications ciblées
def edit(old, new):
    return f"<edit>\n<old>\n{old}\n</old>\n<new>\n{new}\n</new>\n</edit>"


LIGNE = "    return (a + b) / 2"
LIGNE_CORRIGEE = "    return (a + b) // 2"


def test_migrateur_par_modifications_ciblees(tmp_path):
    llm = FakeLLM([RISK, edit(LIGNE, LIGNE_CORRIGEE), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert "// 2" in state["current_code"]
    assert "print(avg(2, 3))" in state["current_code"]  # le reste est intact
    assert state["llm_calls"] == 3
    # on n'a jamais demandé le fichier entier
    assert "Tu ne renvoies PAS le fichier entier" in llm.prompts[1]


def test_modification_introuvable_renvoyee_au_migrateur(tmp_path):
    llm = FakeLLM([RISK, edit("    return a + b / 2", LIGNE_CORRIGEE),
                   edit(LIGNE, LIGNE_CORRIGEE), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert "introuvable" in llm.prompts[2]
    assert "// 2" in state["current_code"]
    assert state["iteration"] == 2


def test_morceau_de_ligne_accepte(tmp_path):
    llm = FakeLLM([RISK, edit("(a + b) / 2", "(a + b) // 2"), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert "// 2" in state["current_code"]


def test_apply_edits_suppression_et_plusieurs_modifications():
    from agents.edits import apply_edits, parse_edits
    code = "a = 1\nb = 2\nc = 3\n"
    reponse = edit("b = 2", "") + "\n" + edit("c = 3", "c = 30")
    new_code, applied, problems = apply_edits(code, parse_edits(reponse))
    assert new_code == "a = 1\nc = 30\n"
    assert applied == 2 and problems == []


def test_apply_edits_texte_ambigu():
    from agents.edits import apply_edits, parse_edits
    code = "x = 1\nx = 1\n"
    new_code, applied, problems = apply_edits(code, parse_edits(edit("x = 1", "x = 2")))
    assert applied == 0 and new_code == code
    assert "plusieurs fois" in problems[0]


def test_numerotation_des_lignes_pour_l_analyseur(tmp_path):
    llm = FakeLLM([RISK, edit(LIGNE, LIGNE_CORRIGEE), APPROVED])
    run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert "  2|     return (a + b) / 2" in llm.prompts[0]
    # le Migrateur voit la ligne concernée par le risque
    assert "code concerné : return (a + b) / 2" in llm.prompts[1]


# ------------------------------------------------ sécurité : risques et retour
def test_risque_invente_est_ecarte(tmp_path):
    invente = json.dumps({"risks": [{
        "line": 12, "code": "self.balance * 3 / 100",
        "description": "division entière", "suggestion": "utiliser //"}]})
    llm = FakeLLM([invente])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["llm_calls"] == 1  # aucun risque réel : le Migrateur n'est pas appelé
    assert state["risks"] == []
    assert "ignoré" in " ".join(state["log"])


def test_numero_de_ligne_corrige(tmp_path):
    mauvais_numero = json.dumps({"risks": [{
        "line": 12, "code": "return (a + b) / 2",
        "description": "division entière", "suggestion": "utiliser //"}]})
    llm = FakeLLM([mauvais_numero, edit(LIGNE, LIGNE_CORRIGEE), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["risks"][0]["line"] == 2


def test_retour_au_code_d_avant_si_le_reviewer_refuse(tmp_path):
    llm = FakeLLM([
        RISK,
        edit(LIGNE, LIGNE_CORRIGEE), REJECTED,
        edit(LIGNE_CORRIGEE, "    return 0"), REJECTED,
    ])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm,
                         max_iterations=2)
    assert state["rolled_back"] is True
    assert "(a + b) / 2" in state["current_code"]  # le code des règles est conservé
    assert "return 0" not in state["current_code"]


def test_pas_de_retour_en_arriere_si_approuve(tmp_path):
    llm = FakeLLM([RISK, edit(LIGNE, LIGNE_CORRIGEE), APPROVED])
    state = run_pipeline(write_source(tmp_path), "python", "hybrid", llm)
    assert state["rolled_back"] is False
    assert "// 2" in state["current_code"]


# ------------------------------------------------------- détecteurs fixes
from agents.detectors import detect_python_risks  # noqa: E402
from agents.graph import run_pipeline as pipeline_with_detectors  # noqa: E402

CMP_SOURCE = "class A(object):\n    def __cmp__(self, other):\n        return cmp(1, 2)\n"
CMP_METHODE = "    def __cmp__(self, other):\n        return cmp(1, 2)"
CMP_CORRIGE = "    def __lt__(self, other):\n        return 1 < 2"


def write_cmp(tmp_path):
    path = tmp_path / "cmp_demo.py"
    path.write_text(CMP_SOURCE, encoding="utf-8")
    return path


def test_detecteurs_remplacent_l_analyseur_llm(tmp_path):
    llm = FakeLLM([edit(CMP_METHODE, CMP_CORRIGE), APPROVED])
    state = pipeline_with_detectors(write_cmp(tmp_path), "python", "hybrid", llm)
    assert state["llm_calls"] == 2            # Migrateur + Reviewer, pas d'Analyseur LLM
    assert "__cmp__" in llm.prompts[0]
    assert "ligne 2" in llm.prompts[0]
    assert state["approved"] is True and not state["rolled_back"]


def test_piege_restant_relance_le_migrateur(tmp_path):
    llm = FakeLLM([
        edit("        return cmp(1, 2)", "        return 1 - 2"),   # corrige cmp() seulement
        edit("    def __cmp__(self, other):", "    def __lt__(self, other):"),
        APPROVED,
    ])
    state = pipeline_with_detectors(write_cmp(tmp_path), "python", "hybrid", llm)
    assert state["iteration"] == 2
    assert "Il reste à la ligne 2" in llm.prompts[1]
    assert "__cmp__" not in state["current_code"]


def test_analyseur_llm_en_plus_des_detecteurs(tmp_path):
    llm = FakeLLM([RISK, edit(LIGNE, LIGNE_CORRIGEE), APPROVED])
    state = pipeline_with_detectors(write_source(tmp_path), "python", "hybrid", llm,
                                    llm_analyzer=True)
    assert state["llm_calls"] == 3
    assert len(state["risks"]) == 1           # même ligne : pas de doublon


def test_la_division_est_un_conseil_pas_un_blocage(tmp_path):
    risks = detect_python_risks("def f(a, b):\n    return a / b\n")
    assert [r["kind"] for r in risks] == ["division"]
    assert risks[0]["blocking"] is False
    assert risks[0]["line"] == 2


def test_detecteurs_cas_particuliers():
    # from __future__ import division : la division était déjà décimale
    assert detect_python_risks("def f(a, b):\n    return a / b\n",
                               original="from __future__ import division\n") == []
    # un nombre décimal : pas de risque
    assert detect_python_risks("x = 3 / 2.0\n") == []
    # cmp défini par le programme lui-même : pas de risque
    assert detect_python_risks("def cmp(a, b):\n    return 0\nx = cmp(1, 2)\n") == []
    # les pièges les plus courants
    code = ("import string\nf = file('a')\ns = string.lower('A')\n"
            "items.sort(lambda a, b: cmp(a, b))\n")
    kinds = {r["kind"] for r in detect_python_risks(code)}
    assert {"file", "string:lower", "sort-cmp", "cmp"} <= kinds
