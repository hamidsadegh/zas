#!/bin/sh
set -e

until python -c "import MySQLdb; MySQLdb.connect(host='$DATABASE_HOST', user='$DATABASE_USER', passwd='$DATABASE_PASSWORD')" 2>/dev/null; do
    sleep 2
done

# # Wait for DB
# while ! mysqladmin ping -h "$DATABASE_HOST" --silent; do
#     sleep 2
# done

# Run Django management tasks
python manage.py makemigrations || true
python manage.py migrate || true
python manage.py collectstatic --noinput || true
python manage.py crontab add || true

# Start crond in background
/usr/sbin/crond -n -s &

# Start Celery beat in background
celery -A zas_project worker -l info &

# Start Gunicorn (foreground)
gunicorn zas_project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --log-level info
