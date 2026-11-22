#!/bin/sh
# Sauvegarde de la base PostgreSQL et des photos, à lancer chaque nuit (cron).
# Conserve les 14 dernières sauvegardes dans /root/sauvegardes-ttb.
#
#   crontab -e
#   30 3 * * * /root/tous-types-de-bricolage/deploy/sauvegarde.sh >> /root/sauvegardes-ttb/log.txt 2>&1
set -eu

cd "$(dirname "$0")"
DEST=/root/sauvegardes-ttb
STAMP=$(date +%Y-%m-%d_%H%M)
mkdir -p "$DEST"

# shellcheck disable=SC1091
. ./.env

docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "$DEST/base_$STAMP.dump"
docker compose exec -T web tar czf - -C /app media > "$DEST/photos_$STAMP.tar.gz"

# garder les 14 plus récentes de chaque type
ls -1t "$DEST"/base_*.dump | tail -n +15 | xargs -r rm --
ls -1t "$DEST"/photos_*.tar.gz | tail -n +15 | xargs -r rm --

echo "$(date) sauvegarde OK : base_$STAMP.dump photos_$STAMP.tar.gz"
