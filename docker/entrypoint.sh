#!/bin/sh
set -o errexit
set -o nounset
set -o pipefail

DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
MAX_RETRIES=${DB_MAX_RETRIES:-60}
SLEEP_SECONDS=${DB_RETRY_SLEEP:-1}

printf 'Waiting for database %s:%s' "$DB_HOST" "$DB_PORT"
retry=0
while ! nc -z "$DB_HOST" "$DB_PORT" >/dev/null 2>&1; do
    retry=$((retry + 1))
    if [ "$retry" -ge "$MAX_RETRIES" ]; then
        printf '\nDatabase is still unavailable after %s attempts.\n' "$MAX_RETRIES"
        exit 1
    fi
    printf '.'
    sleep "$SLEEP_SECONDS"
done
printf '\nDatabase is available, continuing...\n'

python manage.py migrate --noinput

exec "$@"
