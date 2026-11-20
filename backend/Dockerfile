FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends php-cli \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-agents.txt /tmp/
COPY backend/requirements.txt /tmp/requirements-backend.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    -r /tmp/requirements-agents.txt -r /tmp/requirements-backend.txt
COPY . /app