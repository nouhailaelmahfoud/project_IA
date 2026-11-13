"""Le pipeline d'agents : Règles -> Analyseur -> Migrateur -> Validation -> Reviewer."""
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agents.languages import LANGUAGES
from agents.llm_utils import ask_llm, extract_code_block, extract_json
from agents.prompt_loader import load_prompt
from agents.schemas import AnalysisOutput, MigrationOutput, ReviewOutput
from agents.state import MigrationState
from agents.validation import validate_code


def build_graph(llm, language: str):
    config = LANGUAGES[language]
    prompt_dir = config["prompt_dir"]

    def counters(state, tokens_in, tokens_out):
        """Met à jour les compteurs utilisés pour le comparatif."""
        return {
            "llm_calls": state["llm_calls"] + 1,
            "tokens_in": state["tokens_in"] + tokens_in,
            "tokens_out": state["tokens_out"] + tokens_out,
        }

    # ------------------------------------------------------------ règles
    def rules_node(state: MigrationState):
        if state["mode"] == "llm_only":
            return {"log": state["log"] + ["règles : ignorées (mode llm_only)"]}
        result = config["rules"](state["current_code"])
        message = "règles : code converti" if result.changed else "règles : rien à convertir"
        return {
            "current_code": result.code,
            "log": state["log"] + [message] + [f"  remarque : {w}" for w in result.warnings],
        }

    # --------------------------------------------------------- analyseur
    def analyzer_node(state: MigrationState):
        static = ""
        if state["mode"] == "llm_only" and state["issues"]:
            lines = "\n".join(
                f"- ligne {i['line']} : {i['message']}" for i in state["issues"]
            )
            static = "Problèmes déjà détectés par l'analyse statique :\n" + lines

        prompt = load_prompt(
            prompt_dir, "analyzer", code=state["current_code"], static_issues=static
        )
        text, tokens_in, tokens_out = ask_llm(llm, prompt)

        try:
            risks = [r.model_dump() for r in AnalysisOutput(**extract_json(text)).risks]
            message = f"analyseur : {len(risks)} risque(s) repéré(s)"
        except Exception as error:
            risks = []
            message = f"analyseur : réponse illisible ({error})"

        return {
            "risks": risks,
            "log": state["log"] + [message],
            **counters(state, tokens_in, tokens_out),
        }

    # --------------------------------------------------------- migrateur
    def migrator_node(state: MigrationState):
        risks_text = "\n".join(
            f"- ligne {r.get('line') or '?'} : {r['description']}"
            + (f" (suggestion : {r['suggestion']})" if r.get("suggestion") else "")
            for r in state["risks"]
        ) or "- aucun risque précis : corrige tout ce qui empêche l'exécution en Python 3"

        problems = state["errors"] + state["review_problems"]
        feedback = ""
        if problems:
            feedback = (
                "Ta version précédente avait ces problèmes, corrige-les :\n"
                + "\n".join(f"- {p}" for p in problems)
            )

        prompt = load_prompt(
            prompt_dir, "migrator",
            code=state["current_code"], risks=risks_text, feedback=feedback,
        )
        text, tokens_in, tokens_out = ask_llm(llm, prompt)

        new_code, changes = None, []
        try:
            output = MigrationOutput(**extract_json(text))
            new_code, changes = output.code, output.changes
        except Exception:
            new_code = extract_code_block(text)  # plan B

        update = {
            "iteration": state["iteration"] + 1,
            "errors": [],
            "review_problems": [],
            **counters(state, tokens_in, tokens_out),
        }
        if new_code and new_code.strip():
            update["current_code"] = new_code
            update["log"] = state["log"] + [
                f"migrateur (tour {update['iteration']}) : {len(changes)} changement(s)"
            ]
        else:
            update["errors"] = ["Réponse du Migrateur illisible : renvoie le fichier complet en JSON"]
            update["log"] = state["log"] + [
                f"migrateur (tour {update['iteration']}) : réponse illisible"
            ]
        return update

    # -------------------------------------------------------- validation
    def validator_node(state: MigrationState):
        errors = state["errors"] or validate_code(language, state["current_code"])
        message = "validation : OK" if not errors else f"validation : {len(errors)} erreur(s)"
        return {"errors": errors, "log": state["log"] + [message]}

    # ---------------------------------------------------------- reviewer
    def reviewer_node(state: MigrationState):
        prompt = load_prompt(
            prompt_dir, "reviewer",
            original=state["original_code"], migrated=state["current_code"],
        )
        text, tokens_in, tokens_out = ask_llm(llm, prompt)

        try:
            output = ReviewOutput(**extract_json(text))
            approved, problems = output.approved, output.problems
            message = "reviewer : approuvé" if approved else f"reviewer : {len(problems)} problème(s)"
        except Exception as error:
            approved, problems = True, []
            message = f"reviewer : réponse illisible, non vérifié ({error})"

        return {
            "approved": approved,
            "review_problems": problems,
            "log": state["log"] + [message],
            **counters(state, tokens_in, tokens_out),
        }

    # ------------------------------------------------------------ routes
    def after_rules(state):
        return "validator" if state["mode"] == "rules_only" else "analyzer"

    def after_analyzer(state):
        # En mode hybride, sans risque, le LLM n'a rien à faire de plus
        if state["mode"] == "hybrid" and not state["risks"]:
            return "validator"
        return "migrator"

    def after_validator(state):
        if state["errors"]:
            return "migrator" if (
                state["mode"] != "rules_only"
                and state["iteration"] < state["max_iterations"]
            ) else END
        if state["mode"] == "rules_only" or state["iteration"] == 0:
            return END
        return "reviewer"

    def after_reviewer(state):
        if state["approved"] or state["iteration"] >= state["max_iterations"]:
            return END
        return "migrator"

    graph = StateGraph(MigrationState)
    graph.add_node("rules", rules_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("migrator", migrator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("reviewer", reviewer_node)

    graph.add_edge(START, "rules")
    graph.add_conditional_edges("rules", after_rules)
    graph.add_conditional_edges("analyzer", after_analyzer)
    graph.add_edge("migrator", "validator")
    graph.add_conditional_edges("validator", after_validator)
    graph.add_conditional_edges("reviewer", after_reviewer)
    return graph.compile()


def run_pipeline(file_path, language: str, mode: str, llm,
                 issues=None, max_iterations: int = 3):
    """Migre un fichier et renvoie l'état final du pipeline."""
    code = Path(file_path).read_text(encoding="utf-8")
    initial_state = {
        "language": language,
        "mode": mode,
        "file_path": str(file_path),
        "original_code": code,
        "current_code": code,
        "issues": issues or [],
        "risks": [],
        "errors": [],
        "review_problems": [],
        "approved": False,
        "iteration": 0,
        "max_iterations": max_iterations,
        "llm_calls": 0,
        "tokens_in": 0,
        "tokens_out": 0,
        "log": [],
    }
    return build_graph(llm, language).invoke(initial_state)
