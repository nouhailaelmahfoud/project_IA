"""Rapport de migration PDF (reportlab)."""
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

from frontend.metrics import dashboard

LABELS = {"php": "PHP 7 → 8", "python": "Python 2 → 3"}


def _table(data, widths=None):
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b4c7e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def build_report(job: dict, min_per_issue: float, min_review: float) -> bytes:
    """Construit le PDF et le renvoie sous forme d'octets (pour st.download_button)."""
    stats = dashboard(job, min_per_issue, min_review)
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Rapport de migration")
    story = [
        Paragraph("Rapport de migration", styles["Title"]),
        Paragraph(f"Migration : {LABELS.get(job['language'], job['language'])} — "
                  f"job {job['job_id']} — {datetime.now():%d/%m/%Y %H:%M}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Résumé", styles["Heading2"]),
        _table([
            ["Indicateur", "Valeur"],
            ["Fichiers migrés", f"{stats['files_ok']} / {stats['files_total']}"],
            ["Problèmes détectés", stats["issues_total"]],
            ["Problèmes corrigés", stats["issues_fixed"]],
            ["Erreurs bloquantes restantes", stats["errors_remaining"]],
            ["Temps manuel estimé", f"{stats['minutes_manual']:.0f} min"],
            ["Temps avec l'outil (relecture)", f"{stats['minutes_automated']:.0f} min"],
            ["Temps gagné", f"{stats['minutes_saved']:.0f} min"],
        ], [250, 200]),
        Spacer(1, 6),
        Paragraph(f"Hypothèses : {min_per_issue:g} min par problème corrigé à la main, "
                  f"{min_review:g} min de relecture par fichier migré.", styles["Italic"]),
        Spacer(1, 12),
        Paragraph("Détail par fichier", styles["Heading2"]),
        _table([["Fichier", "État", "Détectés", "Erreurs", "Itér.", "LLM"]] +
               [[r["Fichier"], r["État"], r["Problèmes détectés"], r["Erreurs restantes"],
                 r["Itérations"], r["Appels LLM"]] for r in stats["rows"]]),
    ]
    files = (job.get("result") or {}).get("files", {})
    problems = [(n, e) for n, i in files.items() for e in i["errors"]]
    if problems:
        story += [Spacer(1, 12), Paragraph("Erreurs restantes", styles["Heading2"])]
        story += [Paragraph(f"<b>{escape(n)}</b> : {escape(str(e)[:300])}", styles["Normal"])
                  for n, e in problems]
    story += [Spacer(1, 12), Paragraph("Journal de migration", styles["Heading2"])]
    for name, info in files.items():
        log = "\n".join(str(line) for line in info["log"])[:1500]
        story += [Paragraph(name, styles["Heading4"]), Preformatted(log, styles["Code"])]
    doc.build(story)
    return buffer.getvalue()
