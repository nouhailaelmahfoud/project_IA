# Environnement LEGACY PHP : exécute le code d'origine (PHP 7.4 + PHPUnit 9)
FROM composer:2 AS tools
ENV COMPOSER_HOME=/opt/composer
RUN composer global config platform.php 7.4.33 \
    && composer global require phpunit/phpunit:^9 \
        --no-interaction --ignore-platform-reqs

FROM php:7.4-cli
COPY --from=tools /opt/composer /opt/composer
ENV COMPOSER_HOME=/opt/composer PATH="/opt/composer/vendor/bin:${PATH}"
RUN chmod -R a+rX /opt/composer
WORKDIR /work