# Environnement MODERNE PHP : exécute le code migré + PHPUnit 10, PHPStan, pcov
FROM composer:2 AS tools
ENV COMPOSER_HOME=/opt/composer \
    COMPOSER_MAX_PARALLEL_HTTP=3 \
    COMPOSER_HTTP_STALL_TIMEOUT=120
RUN composer global config platform.php 8.3.0
RUN for i in 1 2 3; do \
      composer global require phpunit/phpunit:^10 --no-interaction --ignore-platform-reqs && break; \
      echo "nouvel essai ($i)"; sleep 5; \
    done; \
    test -x /opt/composer/vendor/bin/phpunit
RUN for i in 1 2 3; do \
      composer global require phpstan/phpstan --no-interaction --ignore-platform-reqs && break; \
      echo "nouvel essai ($i)"; sleep 5; \
    done; \
    test -x /opt/composer/vendor/bin/phpstan

FROM php:8.3-cli
RUN pecl install pcov && docker-php-ext-enable pcov
COPY --from=tools /opt/composer /opt/composer
ENV COMPOSER_HOME=/opt/composer PATH="/opt/composer/vendor/bin:${PATH}"
RUN chmod -R a+rX /opt/composer
WORKDIR /work