"""Le pipeline d'agents : Règles -> Analyseur -> Migrateur -> Validation -> Reviewer."""
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from agents.languages import LANGUAGES
from agents.edits import apply_edits, number_lines, parse_edits, verify_risks
from agents.llm_utils import ask_llm, extract_json, parse_migration, save_debug
from agents.prompt_loader import load_prompt
from agents.schemas import AnalysisOutput, MigrationOutput, ReviewOutput
from agents.state import MigrationState
from agents.validation import validate_code


RETRY_HINT = (
    "\n\nATTENTION : ta réponse précédente était incomplète ou illisible. "
    "Réponds avec un JSON complet et court (10 mots maximum par description)."
)


def build_graph(llm, language: str):
    config = LANGUAGES[language]
    prompt_dir = config["prompt_dir"]

    def counters(state, tokens_in, tokens_out, calls=1):
        """Met à jour les compteurs utilisés pour le comparatif."""
        return {
            "llm_calls": state["llm_calls"] + calls,
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
            "rules_code": result.code,
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

        # Détecteurs fixes : gratuits, instantanés, numéros de ligne exacts
        detected, detected_details = [], []
        detector = config.get("detector")
        if state["mode"] == "hybrid" and detector and state["use_detectors"]:
            detected = detector(state["current_code"], state["original_code"])
            detected_details = [
                f"  risque ligne {r['line']} : {r['description'][:90]}"
                for r in detected
            ]
            if not state["llm_analyzer"]:
                return {
                    "risks": detected,
                    "log": state["log"]
                    + [f"analyseur (détecteurs fixes) : {len(detected)} risque(s)"]
                    + detected_details,
                }

        prompt = load_prompt(
            prompt_dir, "analyzer", code=number_lines(state["current_code"]),
            static_issues=static,
        )

        risks, details, calls, total_in, total_out = [], [], 0, 0, 0
        message = ""
        for attempt in (1, 2):
            label = "analyseur" if attempt == 1 else "analyseur (2e essai)"
            text, tokens_in, tokens_out = ask_llm(llm, prompt, label)
            calls += 1
            total_in += tokens_in
            total_out += tokens_out
            try:
                found = [
                    r.model_dump()
                    for r in AnalysisOutput(**extract_json(text, repair=True)).risks
                ]
                # On ne garde que les risques dont la ligne de code existe vraiment
                risks, dropped = verify_risks(state["current_code"], found)
                message = f"analyseur : {len(risks)} risque(s) retenu(s)"
                if dropped:
                    message += f", {dropped} ignoré(s) (ligne de code introuvable)"
                details = [
                    f"  risque ligne {r.get('line') or '?'} : {r['description'][:90]}"
                    for r in risks
                ]
                break
            except Exception:
                raw = save_debug(state["file_path"], "analyzer", attempt, text)
                message = f"analyseur : réponse illisible (brute : {raw})"
                # Même consigne = même réponse : on précise ce qu'on attend
                prompt += RETRY_HINT

        # Les risques des détecteurs passent d'abord ; ceux du modèle s'y ajoutent
        known_lines = {r["line"] for r in detected}
        risks = detected + [r for r in risks if r["line"] not in known_lines]
        return {
            "risks": risks,
            "log": state["log"] + [message] + detected_details + details,
            **counters(state, total_in, total_out, calls),
        }

    # --------------------------------------------------------- migrateur
    def migrator_node(state: MigrationState):
        code_lines = state["current_code"].splitlines()

        def describe(risk):
            line = risk.get("line")
            text = f"- ligne {line or '?'} : {risk['description']}"
            if risk.get("suggestion"):
                text += f" (suggestion : {risk['suggestion']})"
            try:
                text += f"\n    code concerné : {code_lines[int(line) - 1].strip()}"
            except (TypeError, ValueError, IndexError):
                pass
            return text

        risks_text = "\n".join(describe(r) for r in state["risks"][:8]) or (
            "- aucun risque précis : corrige tout ce qui empêche l'exécution en Python 3"
        )

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
        text, tokens_in, tokens_out = ask_llm(
            llm, prompt, f"migrateur (tour {state['iteration'] + 1})")

        edits = parse_edits(text)
        new_code, changes, edit_problems = None, [], []
        if edits:
            # Format demandé : des modifications ciblées (ancien texte -> nouveau)
            patched, applied, edit_problems = apply_edits(state["current_code"], edits)
            if applied:
                new_code = patched
                changes = [f"modification {n}" for n in range(1, applied + 1)]
        else:
            # Plan B : le modèle a renvoyé le fichier complet
            new_code, changes = parse_migration(text)

        update = {
            "iteration": state["iteration"] + 1,
            "errors": [],
            "review_problems": [],
            **counters(state, tokens_in, tokens_out),
        }
        if new_code and new_code.strip():
            update["current_code"] = new_code
            update["errors"] = edit_problems  # modifications ratées : à refaire
            update["log"] = state["log"] + [
                f"migrateur (tour {update['iteration']}) : {len(changes)} changement(s)"
            ] + [f"  non appliqué : {p}" for p in edit_problems]
        else:
            raw = save_debug(state["file_path"], "migrator", update["iteration"], text)
            update["errors"] = edit_problems or [
                "Réponse du Migrateur illisible : utilise le format "
                "<edit><old>...</old><new>...</new></edit>"
            ]
            what = "aucune modification applicable" if edits else "réponse illisible"
            update["log"] = state["log"] + [
                f"migrateur (tour {update['iteration']}) : {what} (brute : {raw})"
            ]
        return update

    # -------------------------------------------------------- validation
    def validator_node(state: MigrationState):
        errors = state["errors"] or validate_code(language, state["current_code"])
        detector = config.get("detector")
        if (not errors and state["mode"] == "hybrid" and detector
                and state["use_detectors"] and state["iteration"] > 0):
            # Les pièges bloquants doivent avoir disparu
            errors = [
                f"Il reste à la ligne {r['line']} : {r['description']}. {r['suggestion']}"
                for r in detector(state["current_code"], state["original_code"])
                if r["blocking"]
            ]
        message = "validation : OK" if not errors else f"validation : {len(errors)} erreur(s)"
        return {"errors": errors, "log": state["log"] + [message]}

    # ---------------------------------------------------------- reviewer
    def reviewer_node(state: MigrationState):
        prompt = load_prompt(
            prompt_dir, "reviewer",
            original=state["original_code"], migrated=state["current_code"],
        )
        text, tokens_in, tokens_out = ask_llm(llm, prompt, "reviewer")

        try:
            output = ReviewOutput(**extract_json(text, repair=True))
            approved, problems = output.approved, output.problems
            message = "reviewer : approuvé" if approved else f"reviewer : {len(problems)} problème(s)"
        except Exception as error:
            approved, problems = True, []
            raw = save_debug(state["file_path"], "reviewer", state["iteration"], text)
            message = f"reviewer : réponse illisible, non vérifié (brute : {raw})"

        return {
            "approved": approved,
            "review_problems": problems,
            "log": state["log"] + [message],
            **counters(state, tokens_in, tokens_out),
        }

    # --------------------------------------------------------- finalisation
    def finalize_node(state: MigrationState):
        """Si les modifications du modèle n'ont pas été validées, on les écarte."""
        if state["mode"] == "rules_only" or state["iteration"] == 0:
            return {"rolled_back": False}
        if state["approved"] and not state["errors"]:
            return {"rolled_back": False}
        return {
            "current_code": state["rules_code"],
            "rolled_back": True,
            "log": state["log"] + [
                "finalisation : modifications du modèle non validées, "
                "retour au code d'avant le Migrateur"
            ],
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
            ) else "finalize"
        if state["mode"] == "rules_only" or state["iteration"] == 0:
            return "finalize"
        return "reviewer"

    def after_reviewer(state):
        if state["approved"] or state["iteration"] >= state["max_iterations"]:
            return "finalize"
        return "migrator"

    graph = StateGraph(MigrationState)
    graph.add_node("rules", rules_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("migrator", migrator_node)
    graph.add_node("validator", validator_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "rules")
    graph.add_conditional_edges("rules", after_rules)
    graph.add_conditional_edges("analyzer", after_analyzer)
    graph.add_edge("migrator", "validator")
    graph.add_conditional_edges("validator", after_validator)
    graph.add_conditional_edges("reviewer", after_reviewer)
    graph.add_edge("finalize", END)
    return graph.compile()


def run_pipeline(file_path, language: str, mode: str, llm,
                 issues=None, max_iterations: int = 3,
                 llm_analyzer: bool = False, use_detectors: bool = True):
    """Migre un fichier et renvoie l'état final du pipeline."""
    code = Path(file_path).read_text(encoding="utf-8")
    initial_state = {
        "language": language,
        "mode": mode,
        "file_path": str(file_path),
        "original_code": code,
        "current_code": code,
        "rules_code": code,
        "rolled_back": False,
        "llm_analyzer": llm_analyzer,
        "use_detectors": use_detectors,
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
