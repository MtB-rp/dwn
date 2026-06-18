#!/usr/bin/env sh
set -eu

GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"
GUNICORN_THREADS="${GUNICORN_THREADS:-8}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-300}"
USE_HTTPS="${USE_HTTPS:-false}"
TLS_CERT_FILE="${TLS_CERT_FILE:-/certs/tls.crt}"
TLS_KEY_FILE="${TLS_KEY_FILE:-/certs/tls.key}"

BASE_ARGS="--bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS} --worker-class gthread --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT}"

if [ "$USE_HTTPS" = "true" ]; then
  if [ ! -f "$TLS_CERT_FILE" ] || [ ! -f "$TLS_KEY_FILE" ]; then
    echo "ERROR: USE_HTTPS=true but TLS cert/key not found: cert=$TLS_CERT_FILE key=$TLS_KEY_FILE" >&2
    exit 1
  fi
  exec gunicorn $BASE_ARGS --certfile "$TLS_CERT_FILE" --keyfile "$TLS_KEY_FILE" "app:create_app()"
fi

exec gunicorn $BASE_ARGS "app:create_app()"
