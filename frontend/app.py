"""Interface web (Streamlit) de l'agent de migration.

Lancer :  streamlit run frontend/app.py      (l'API doit tourner sur API_URL)
"""
import difflib

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from frontend import api_client
from frontend.metrics import MIN_PER_ISSUE_MANUAL, MIN_REVIEW_PER_FILE, dashboard
from frontend.report_pdf import build_report

# Le sélecteur de migration : libellé affiché -> langage compris par l'API
MIGRATIONS = {"PHP 7 → 8": "php", "Python 2 → 3": "python"}

st.set_page_config(page_title="Agent de migration", layout="wide")
st.title("Agent de migration de code legacy")

# ---------- Barre latérale : réglages ----------
with st.sidebar:
    st.header("Réglages")
    migration = st.selectbox("Migration", list(MIGRATIONS))
    mode = st.selectbox("Mode", ["rules_only", "hybrid", "llm_only"],
                        help="rules_only : sans IA. hybrid : règles + IA. llm_only : IA seule.")
    provider, model = "ollama", ""
    if mode != "rules_only":
        provider = st.selectbox("Fournisseur LLM", ["openrouter", "ollama"])
        model = st.text_input("Modèle (facultatif)")
    max_iterations = st.slider("Itérations max", 1, 5, 3)
    st.header("Hypothèses de temps")
    min_issue = st.number_input("Minutes / problème corrigé à la main", 1, 120,
                                MIN_PER_ISSUE_MANUAL)
    min_review = st.number_input("Minutes de relecture / fichier", 0, 60, MIN_REVIEW_PER_FILE)

language = MIGRATIONS[migration]
ext = ".php" if language == "php" else ".py"

# ---------- Étape 1 : envoyer le code ----------
st.subheader("1. Code à migrer")
source = st.radio("Source", ["Fichiers", "Dépôt GitHub"], horizontal=True)
files, repo_url = None, None
if source == "Fichiers":
    files = st.file_uploader(f"Fichiers {ext}", type=[ext.strip(".")], accept_multiple_files=True)
else:
    repo_url = st.text_input("URL du dépôt", placeholder="https://github.com/proprietaire/depot")

if st.button("Analyser", type="primary", disabled=not (files or repo_url)):
    try:
        with st.spinner("Analyse en cours…"):
            created = api_client.create_job(files, repo_url, language)
            st.session_state["job"] = api_client.wait_for_job(created["job_id"])
    except Exception as error:
        st.error(str(error))

job = st.session_state.get("job")
if not job:
    st.info("Choisis une migration, envoie du code, puis clique sur « Analyser ».")
    st.stop()
if job["status"] == "failed":
    st.error(f"Le job a échoué : {job['error']}")
    st.stop()

# ---------- Étape 2 : résultat de l'analyse et lancement de la migration ----------
st.subheader("2. Analyse")
st.write(f"Job `{job['job_id']}` — {len(job['issues'])} problème(s) détecté(s).")
if job["issues"]:
    st.dataframe(pd.DataFrame(job["issues"])[["file_path", "line", "severity", "rule_id", "message"]],
                 use_container_width=True, hide_index=True)

if st.button("Lancer la migration"):
    try:
        with st.spinner("Migration en cours (peut durer plusieurs minutes avec un LLM)…"):
            api_client.start_migration(job["job_id"], mode, provider, model, max_iterations)
            st.session_state["job"] = job = api_client.wait_for_job(job["job_id"])
    except Exception as error:
        st.error(str(error))

if not job.get("result"):
    st.stop()
if job["status"] == "failed":
    st.error(f"La migration a échoué : {job['error']}")
    st.stop()

# ---------- Étape 3 : tableau de bord ----------
st.subheader("3. Tableau de bord")
stats = dashboard(job, min_issue, min_review)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Fichiers validés", f"{stats['files_ok']} / {stats['files_total']}")
c2.metric("Problèmes corrigés", f"{stats['issues_fixed']} / {stats['issues_total']}")
c3.metric("Erreurs restantes", stats["errors_remaining"])
c4.metric("Temps gagné (estimé)", f"{stats['minutes_saved']:.0f} min")
st.dataframe(pd.DataFrame(stats["rows"]), use_container_width=True, hide_index=True)
st.caption(f"Temps gagné = {min_issue} min × problèmes corrigés − {min_review} min de relecture "
           "× fichiers. C'est une estimation, pas une mesure.")

# ---------- Étape 4 : diff avant / après ----------
st.subheader("4. Différences avant / après")
files_result = job["result"]["files"]
name = st.selectbox("Fichier", list(files_result))
info = files_result[name]
diff_html = difflib.HtmlDiff(wrapcolumn=80).make_file(
    info["original_code"].splitlines(), info["migrated_code"].splitlines(),
    "Avant", "Après", context=True, numlines=3)
components.html(diff_html, height=500, scrolling=True)
with st.expander("Journal de migration"):
    st.code("\n".join(str(line) for line in info["log"]) or "(vide)")
if info["errors"]:
    st.warning("Erreurs de validation : " + " ; ".join(str(e) for e in info["errors"]))

# ---------- Étape 5 : rapport PDF ----------
st.subheader("5. Rapport")
st.download_button("Télécharger le rapport PDF",
                   data=build_report(job, min_issue, min_review),
                   file_name=f"rapport_migration_{job['job_id']}.pdf",
                   mime="application/pdf")
