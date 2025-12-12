#!/usr/bin/env bash
set -euo pipefail

# ============================
# ZAS Post-Change Health Check
# ============================

PROJECT_DIR="/opt/code/zas"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "====================================="
echo " ZAS health check started"
echo "====================================="

cd "$PROJECT_DIR"

# ---------- 1. Python & venv ----------
echo "[1/10] Checking Python & virtualenv..."

if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: virtualenv not found at $VENV_DIR"
  exit 1
fi

"$PYTHON" --version
"$PYTHON" - <<EOF
import sys
assert sys.version_info[:2] == (3, 11), "Python version is not 3.11"
EOF

echo "OK: Python version correct"

# ---------- 2. Dependency integrity ----------
echo "[2/10] Running pip check (with known exceptions)..."

PIP_CHECK_OUTPUT=$("$PIP" check || true)

# Known, accepted conflict (SNMP stack)
KNOWN_OK_PATTERN="pyasn1-modules 0.4.2 has requirement pyasn1<0.7.0,>=0.6.1, but you have pyasn1 0.4.8"

FILTERED_OUTPUT=$(echo "$PIP_CHECK_OUTPUT" | grep -vE "$KNOWN_OK_PATTERN" || true)

if [[ -n "$FILTERED_OUTPUT" ]]; then
  echo "ERROR: pip dependency issues detected:"
  echo "$FILTERED_OUTPUT"
  exit 1
fi

echo "OK: dependencies consistent (known SNMP exception accepted)"

# ---------- 3. Django system check ----------
echo "[3/10] Running Django system check..."
"$PYTHON" manage.py check --fail-level WARNING
echo "OK: Django check passed"

# ---------- 4. Django tests ----------
echo "[4/10] Running Django test suite..."
"$PYTHON" manage.py test
echo "OK: Django tests passed"

# ---------- 5. pytest ----------
echo "[5/10] Running pytest..."
"$VENV_DIR/bin/pytest"
echo "OK: pytest passed"

# ---------- 6. Database connectivity ----------
echo "[6/10] Verifying database connectivity..."
DJANGO_SETTINGS_MODULE=zas.settings.base \
"$PYTHON" - <<EOF
from django.conf import settings
from django.db import connections
conn = connections["default"]
conn.ensure_connection()
print("DB connected:", conn.settings_dict["NAME"])
EOF
echo "OK: database reachable"

# ---------- 7. Celery sanity ----------
echo "[7/10] Checking Celery app import..."
"$PYTHON" - <<EOF
from zas.celery import app
print("Celery app loaded:", app.main)
EOF
echo "OK: Celery app imports correctly"

# ---------- 8. Redis ----------
echo "[8/10] Checking Redis connectivity..."
if command -v redis-cli >/dev/null 2>&1; then
  redis-cli ping | grep -q PONG && echo "OK: Redis reachable"
else
  echo "WARNING: redis-cli not installed, skipping Redis check"
fi

# ---------- 9. SNMP import (non-fatal) ----------
echo "[9/10] Checking SNMP stack import..."
"$PYTHON" - <<EOF || echo "WARNING: SNMP import failed (expected on non-SNMP nodes)"
try:
    import pysnmp
    print("SNMP available")
except Exception as e:
    print("SNMP not available:", e)
EOF

# ---------- 10. Final summary ----------
echo "[10/10] Health check complete"
echo "====================================="
echo " ZAS is HEALTHY"
echo "====================================="
