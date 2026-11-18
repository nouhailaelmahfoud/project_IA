# Installation (Linux ou WSL Ubuntu)

Versions testées : Python 3.12 et PHP 8.3.

## 1. Outils système

~~~bash
sudo apt install -y git python3 python3-venv python3-pip python3-lib2to3 php-cli php-mbstring php-xml php-curl composer unzip
~~~

`2to3` disparaît en Python 3.13 : il faut rester en Python 3.12.

## 2. Dépôt et environnement Python

~~~bash
git clone git@github.com:nouhailaelmahfoud/project_IA.git
cd project_IA
git checkout feature/agents-ia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-agents.txt
~~~

## 3. Dépendances PHP

~~~bash
(cd plugins/php_analyzer && composer install)
(cd tools/rector && composer install)
~~~

## 4. Clés et modèles

Copier `.env.example` en `.env` et le remplir (clé OpenRouter, nom du modèle).
Modèle local facultatif : installer Ollama puis `ollama pull qwen2.5-coder:3b`.

## 5. Vérifier

~~~bash
python3 -m pytest tests -q
~~~

Voir aussi `docs/tache2_agents.md` (architecture et lancement).
