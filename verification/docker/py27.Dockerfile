# Environnement LEGACY Python : exécute le code d'origine
FROM python:2.7-slim
ENV PYTHONDONTWRITEBYTECODE=1
RUN pip install --no-cache-dir "pytest<5" "coverage<6"
WORKDIR /work