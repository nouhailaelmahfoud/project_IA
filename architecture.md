# Architecture

## Vue d'ensemble

Le frontend ne contient aucune logique de migration : il parle uniquement à l'API.
L'API met les travaux dans une file (Redis) et un worker les exécute.

~~~mermaid
flowchart LR
    U[Utilisateur] --> F[Frontend Streamlit :8501]
    F -->|HTTP| A[API FastAPI :8000]
    A -->|file de tâches| R[(Redis)]
    R --> W[Worker Celery]
    W --> P[Plugins d'analyse - Tâche 1]
    W --> G[Agents IA - Tâche 2]
    G --> V[Vérification Docker - Tâche 3]
    W -->|résultat du job| R
    A -->|lecture du job| R
    W -.->|facultatif| GH[GitHub : Pull Request]
~~~

## Déroulement d'une migration

~~~mermaid
sequenceDiagram
    actor U as Utilisateur
    participant F as Frontend
    participant A as API
    participant W as Worker
    U->>F: envoie le code + choisit PHP 7→8 ou Python 2→3
    F->>A: POST /jobs
    A->>W: analyze_job
    F->>A: GET /jobs/{id} (toutes les 2 s)
    W-->>A: problèmes détectés (status done)
    U->>F: Lancer la migration
    F->>A: POST /jobs/{id}/migrate
    A->>W: migrate_job_task
    W-->>A: résultat (code avant/après, erreurs, journal)
    F->>A: GET /jobs/{id}
    F-->>U: tableau de bord, diff, rapport PDF
~~~

## Pipeline d'agents (Tâche 2)

~~~mermaid
flowchart LR
    S[Code source] --> RU[Règles automatiques]
    RU --> AN[Analyseur]
    AN --> MI[Migrateur]
    MI --> VA[Validation]
    VA -->|erreurs| MI
    VA -->|ok| RE[Relecteur]
    RE -->|refus| MI
    RE -->|approuvé| OUT[Code migré]
    VA -->|échec final| RB[Retour arrière : version des règles]
~~~

## Classes principales (UML simplifié)

~~~mermaid
classDiagram
    class LanguagePlugin {
        +name
        +file_extensions
        +analyze_file() list~Issue~
        +analyze_project() list~Issue~
    }
    class PhpPlugin
    class PythonPlugin
    class Issue {
        +file_path
        +line
        +rule_id
        +severity
        +message
        +recommendation
    }
    class MigrationState {
        +original_code
        +current_code
        +errors
        +approved
        +rolled_back
        +log
    }
    LanguagePlugin <|-- PhpPlugin
    LanguagePlugin <|-- PythonPlugin
    LanguagePlugin ..> Issue : produit
    MigrationState ..> Issue : reçoit
~~~

## Pourquoi ces choix

- **Plugins par langage** : ajouter un langage ne change pas le reste (voir `ajouter_un_langage.md`).
- **File de tâches** : une migration avec un LLM dure des minutes, l'API ne doit pas bloquer.
- **Retour arrière** : si le LLM casse le code, on garde la version produite par les règles.
- **Streamlit** : une seule langue (Python) pour toute l'équipe, pas de build JavaScript.
