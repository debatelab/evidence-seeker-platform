#!/bin/bash

set -euo pipefail

DOMAIN="b7233fdd-ac70-4e21-ae82-54a2e6c682e4.ka.bw-cloud-instance.org"
PROJECT_DIR="/opt/evidence-seeker-platform"
SSL_SOURCE="/etc/letsencrypt/live/${DOMAIN}"
SSL_TARGET="${PROJECT_DIR}/ssl"

install -d -m 0755 "${SSL_TARGET}"

install -m 0644 "${SSL_SOURCE}/fullchain.pem" "${SSL_TARGET}/fullchain.pem"
install -m 0600 "${SSL_SOURCE}/privkey.pem" "${SSL_TARGET}/privkey.pem"

/usr/bin/docker compose -f "${PROJECT_DIR}/docker-compose.prod.yml" restart nginx >/dev/null 2>&1 || \
  /usr/bin/docker compose -f "${PROJECT_DIR}/docker-compose.prod.yml" up -d nginx --no-deps >/dev/null 2>&1 || true
