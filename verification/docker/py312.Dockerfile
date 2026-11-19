# Environnement MODERNE Python : exécute le code migré + analyse statique
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
RUN pip install --no-cache-dir pytest pytest-cov mypy ruff pylint
WORKDIR /work