# project_IA — Agent de migration de code legacy

Outil qui migre automatiquement du code ancien vers une version récente :
**PHP 7 → 8** et **Python 2 → 3**. Il combine des règles automatiques (Rector, 2to3),
des agents IA (analyseur, migrateur, relecteur) et une vérification dans Docker.

## Les 5 tâches

| Tâche | Rôle | Dossier |
|---|---|---|
| 1 | Analyse du code et détection des problèmes | `plugins/`, `core/` |
| 2 | Agents IA de migration | `agents/`, `prompts/` |
| 3 | Vérification (analyse statique, comportement, tests) | `verification/` |
| 4 | API et traitement en arrière-plan | `backend/` |
| 5 | Interface web, documentation, gestion de projet | `frontend/`, `docs/` |

## Démarrage rapide (Docker)

~~~bash
cp .env.example .env        # puis remplir les clés si on utilise un LLM
docker compose up --build
~~~

- Interface web : http://localhost:8501
- API (documentation interactive) : http://localhost:8000/docs

Sans Docker : voir `docs/installation.md`, puis dans deux terminaux
(Redis et le worker Celery doivent aussi tourner) :

~~~bash
uvicorn backend.app.main:app --port 8000
pip install -r frontend/requirements.txt
streamlit run frontend/app.py
~~~

## Utiliser l'interface

1. Choisir la migration (PHP 7→8 ou Python 2→3) et le mode dans la barre latérale.
2. Envoyer des fichiers ou donner l'URL d'un dépôt GitHub, puis « Analyser ».
3. « Lancer la migration ». Le mode `rules_only` n'utilise pas d'IA et est quasi instantané.
4. Lire le tableau de bord, comparer avant/après, télécharger le rapport PDF.

## Documentation

- [Architecture et schémas UML](docs/architecture.md)
- [Comment ajouter un nouveau langage](docs/ajouter_un_langage.md)
- [Étude Problème / Solution / ROI](docs/etude_roi.md)
- [Démo, soutenance et suivi de projet](docs/demo_soutenance_projet.md)
- [Installation](docs/installation.md) · [Agents](docs/tache2_agents.md) · [Vérification](docs/tache3_verification.md)

## Tests

~~~bash
python3 -m pytest tests -q
~~~
