"""Interface web (Streamlit) de l'agent de migration.

Lancer :  streamlit run frontend/app.py      (l'API doit tourner sur API_URL)
"""
import difflib
import io
import zipfile

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
    verify = st.checkbox("Vérifier dans Docker",
                         help="Compare le comportement avant/après et lance l'analyse statique. "
                              "Demande que le worker de vérification tourne sur ton PC "
                              "(voir docs/tache3_verification.md).")
    if verify:
        st.warning("Lance d'abord le worker de vérification sur ton PC, sinon la migration "
                   "restera en attente.")
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
            api_client.start_migration(job["job_id"], mode, provider, model, max_iterations,
                                       verify=verify)
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
st.caption("Problèmes corrigés = problèmes détectés avant la migration − constructions "
           "restantes après (Python 2 encore présent dans le code migré).")
if job["result"].get("mode") == "rules_only":
    st.caption("Mode rules_only : les règles seules ne vérifient pas le comportement et aucun "
               "relecteur n'est lancé. Utilise le mode hybrid, et « Vérifier dans Docker » pour "
               "confirmer que le comportement est conservé.")

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

# Vérification de la Tâche 3 (affichée seulement si la case a été cochée)
verification = info.get("verification") or {}
vmetrics = verification.get("metrics", {})
if vmetrics.get("skipped"):
    st.info("Vérification Docker ignorée : Docker n'est pas disponible pour le worker.")
elif vmetrics:
    v1, v2, v3 = st.columns(3)
    v1.metric("Même comportement",
              {True: "oui", False: "non", None: "non comparé"}[vmetrics.get("behaviour_ok")])
    v2.metric("Erreurs statiques", vmetrics.get("static_errors", 0))
    v3.metric("Avertissements", len(verification.get("warnings", [])))

# ---------- Étape 5 : téléchargements ----------
st.subheader("5. Téléchargements")
if info["errors"]:
    st.caption("Ce fichier a des erreurs de validation : relis-le avant de l'utiliser.")
archive = io.BytesIO()
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
    for file_name, file_info in files_result.items():
        bundle.writestr(file_name.lstrip("/"), file_info["migrated_code"])
d1, d2, d3 = st.columns(3)
d1.download_button(f"Code migré : {name.split('/')[-1]}", data=info["migrated_code"],
                   file_name=name.split("/")[-1], mime="text/plain")
d2.download_button("Tous les fichiers migrés (.zip)", data=archive.getvalue(),
                   file_name=f"code_migre_{job['job_id']}.zip", mime="application/zip")
d3.download_button("Rapport PDF",
                   data=build_report(job, min_issue, min_review),
                   file_name=f"rapport_migration_{job['job_id']}.pdf",
                   mime="application/pdf")