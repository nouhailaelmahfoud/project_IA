# Démo, soutenance et suivi de projet

## Vidéo de démo (3 à 4 minutes)

Enregistrer l'écran (OBS Studio ou Xbox Game Bar) pendant que l'on suit ce script :

1. **(20 s)** Présenter le problème : du code legacy PHP 7 / Python 2.
2. **(20 s)** Montrer `docker compose up` et ouvrir http://localhost:8501.
3. **(40 s)** Choisir « Python 2 → 3 », envoyer `samples/py2_corpus/bank/bank.py`, cliquer « Analyser ».
   Commenter la liste des problèmes (par exemple `<>` supprimé en Python 3).
4. **(40 s)** Mode `rules_only` : « Lancer la migration », montrer le tableau de bord.
5. **(40 s)** Ouvrir la vue avant/après : expliquer les changements.
6. **(30 s)** Refaire avec « PHP 7 → 8 » et `samples/php7/legacy.php`.
7. **(20 s)** Télécharger et ouvrir le rapport PDF.
8. **(20 s)** Conclure : gain de temps estimé, limites, prochain langage à ajouter.

Astuce : utiliser `rules_only` pour la vidéo (rapide, sans clé API). Montrer `hybrid` seulement
si le modèle répond vite.

## Plan de la soutenance (10 à 12 diapositives)

1. Titre et équipe
2. Problème (code legacy, risques)
3. Solution en une phrase
4. Architecture (schéma de `docs/architecture.md`)
5. Tâche 1 : détection
6. Tâche 2 : agents IA et retour arrière
7. Tâche 3 : vérification dans Docker
8. Tâche 4 : API et file de tâches
9. Tâche 5 : interface (capture d'écran)
10. Résultats du benchmark (tableau de `etude_roi.md`)
11. ROI et limites
12. Démo en direct (ou vidéo) et questions

Répartition conseillée : un rôle par tâche, chacun présente la sienne.

## Suivi Trello (ou Jira)

Colonnes : **À faire → En cours → En relecture → Terminé**.

Cartes à créer (une par ligne, avec responsable et date) :

| Carte | Tâche |
|---|---|
| Analyseur PHP / Python | 1 |
| Pipeline d'agents + prompts | 2 |
| Moteur de vérification Docker | 3 |
| API FastAPI + Celery + Redis | 4 |
| Interface Streamlit | 5 |
| Rapport PDF | 5 |
| README, UML, guide « nouveau langage » | 5 |
| Étude ROI | 5 |
| Vidéo de démo | 5 |
| Soutenance | 5 |

Bonnes pratiques : une carte = un livrable vérifiable, une branche Git par carte
(`feature/...`), une Pull Request relue avant fusion, une réunion courte par semaine.
Ajouter le lien du tableau Trello ici : `https://trello.com/b/...`
