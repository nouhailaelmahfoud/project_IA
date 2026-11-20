FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
        php-cli php-mbstring php-xml php-curl unzip git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer
COPY requirements.txt requirements-agents.txt /tmp/
COPY backend/requirements.txt /tmp/requirements-backend.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    -r /tmp/requirements-agents.txt -r /tmp/requirements-backend.txt
COPY . /app
RUN cd /app/plugins/php_analyzer && composer install --no-interaction --no-dev
RUN cd /app/tools/rector && composer install --no-interaction