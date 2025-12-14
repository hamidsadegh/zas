#!/usr/bin/env bash
set -euo pipefail

#######################################
# Sanity checks
#######################################
required_vars=(
  DB_ENGINE DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD BACKUP_DIR
)

for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: $var is not set"
    exit 1
  fi
done

#######################################
# Defaults
#######################################
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_PREFIX=${BACKUP_PREFIX:-backup}
RETENTION_DAYS=${RETENTION_DAYS:-7}
COMPRESS=${COMPRESS:-true}

mkdir -p "$BACKUP_DIR"

FILENAME="${BACKUP_PREFIX}_${DB_NAME}_${TIMESTAMP}.sql"
FILEPATH="${BACKUP_DIR}/${FILENAME}"

#######################################
# Dump
#######################################
echo "Starting backup: $DB_ENGINE → $FILEPATH"

case "$DB_ENGINE" in
  mysql)
    export MYSQL_PWD="$DB_PASSWORD"
    mysqldump \
      --host="$DB_HOST" \
      --port="$DB_PORT" \
      --user="$DB_USER" \
      --single-transaction \
      --routines \
      --triggers \
      --events \
      "$DB_NAME" > "$FILEPATH"
    unset MYSQL_PWD
    ;;
  
  postgres)
    export PGPASSWORD="$DB_PASSWORD"
    pg_dump \
      --host="$DB_HOST" \
      --port="$DB_PORT" \
      --username="$DB_USER" \
      --format=plain \
      --no-owner \
      --no-acl \
      "$DB_NAME" > "$FILEPATH"
    unset PGPASSWORD
    ;;
  
  *)
    echo "ERROR: Unsupported DB_ENGINE: $DB_ENGINE"
    exit 1
    ;;
esac

#######################################
# Compression
#######################################
if [[ "$COMPRESS" == "true" ]]; then
  gzip "$FILEPATH"
  FILEPATH="${FILEPATH}.gz"
fi

#######################################
# Retention
#######################################
echo "Applying retention: ${RETENTION_DAYS} days"
find "$BACKUP_DIR" -type f -mtime +"$RETENTION_DAYS" -delete

#######################################
# Done
#######################################
echo "Backup completed: $FILEPATH"
