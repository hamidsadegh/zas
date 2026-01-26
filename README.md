# ZAS (Zentrales Administration- und Automation System)

ZAS is a Django-based network administration and automation platform for managing
DCIM data, discovery, and device synchronization through a web UI.

## Highlights
- Device inventory with sites, areas, racks, and configuration history
- Discovery pipeline with candidates, mismatch handling, and auto-assignment
- Device sync and reachability tracking
- SSH terminal access in the browser
- REST API via Django REST Framework

## Project structure
- core: shared layout, navigation, and base templates
- dcim: inventory, IPAM, VLANs, devices, and configuration views
- network: discovery, sync, and candidate workflows
- automation: SSH terminal and automation helpers

## Tech stack
- Python 3.11, Django 5.2
- PostgreSQL
- Redis (Channels)
- Django REST Framework
- Netmiko/Paramiko for device access
- Celery (nightly reachability checks and backups)
- Gunicorn (WSGI)

## Local setup
1. Create a virtualenv and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements-3.11.txt
   ```
2. Configure `.env`:
   - `FIELD_ENCRYPTION_KEY`
   - `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`
   - `REDIS_URL` (optional; defaults to `redis://127.0.0.1:6379/1`)
3. Run migrations and create an admin user:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. Start the server:
   ```bash
   python manage.py runserver
   ```
   For ASGI/WebSocket support in production, run Daphne:
   ```bash
   daphne -b 0.0.0.0 -p 9001 zas.asgi:application
   ```

## Management commands
- Discovery:
  ```bash
  python manage.py discover_runner --site <site-name> [--org <org-name>] [--cidr <cidr>]
  ```
- Sync:
  ```bash
  python manage.py sync_runner --site <site-name> [--org <org-name>] [--limit N] [--no-config]
  python manage.py sync_runner --device <device-name> [--no-config]
  ```
- Auto-assign:
  ```bash
  python manage.py auto_assign [--site-id <uuid>] [--candidate-id <uuid>] \
      [--candidate-hostname <str>] [--limit N] [--no-config]
  ```

## Logs
- `/var/log/zas/django/application.log`
- `/var/log/zas/django/requests.log`
- `/var/log/zas/django/security.log`
- `/var/log/zas/django/errors.log`

## Docker quick start
```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```
The compose file includes Celery worker and Celery Beat services for reachability checks and nightly backups.
