"""Tests du pipeline avec un FAUX modèle : aucun appel réseau, aucun quota."""
import json

from agents.graph import run_pipeline

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


RISK = json.dumps({"risks": [{"line": 2, "description": "division entière", "suggestion": "utiliser //"}]})
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
