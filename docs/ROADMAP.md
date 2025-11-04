# 🧭 ZAS Project Roadmap

## Phase 0 — Environment Setup & Foundation
**Goal:** Get the project running locally and ensure CI/CD stability.

### Milestones
- Setup repository, `.env`, Docker, and Docker Compose (Django + MariaDB).
- Configure base Django project and virtualenv.
- Add base apps: `devices`, `organizations`, `users`.
- Add GitHub Actions workflow for automated tests.
- Initialize pytest test structure and coverage report.

---

## Phase 1 — Core Framework & MVP
**Goal:** Functional base for device and endpoint management.

### Milestones
1. **Django Models**
   - `Organization`, `Device`, `Endpoint`, `Interface`.
   - Admin registration and migrations.

2. **Django REST Framework (DRF)**
   - Serializers, viewsets, and routers.
   - REST API for Devices and Interfaces.

3. **Basic Templates & UI**
   - Device list and detail views.
   - Pagination, search, and filtering.

4. **Authentication**
   - Django admin + token-based API authentication.

5. **Services Skeleton**
   - `services/ssh.py`, `services/snmp.py` with Netmiko/pysnmp stubs.
   - `dbmanager.py` for synchronization tasks.

6. **Testing & CI**
   - Unit tests for models, serializers, and views.
   - CI workflow validation.

7. **UX Polish & Data Import**
   - Refine device detail view (Basic Info / Config / Interfaces).
   - Add pagination for interfaces under device detail.
   - Implement CSV/Excel import/export (`openpyxl`).

8. **MVP Deployment**
   - Deploy Dockerized stack (Gunicorn + Nginx) for staging demo.

---

## Phase 2 — Automation & Advanced Functionality
**Goal:** Turn ZAS into a management and automation platform.

### Planned Features

#### 1. Automation & Tasks
- Daily configuration backups.
- Zero-Touch Provisioning (ZTP) for new devices.
- Bulk configuration changes via CLI.
- **Software image upgrade/downgrade** (single/group devices).
- **Execute CLI commands** (single/group devices).
- Scheduled jobs via Celery (or Django-crontab).
- Job tracking with `AutomationJob` model (status/logs).

#### 2. Device Interaction Services
- **SSH Service (`services/ssh.py`)**
  - Execute commands and gather outputs.
  - Transfer configuration or image files.

- **SNMP Service (`services/snmp.py`)**
  - Retrieve uptime, interface counters, CPU/memory.
  - Support for multiple community profiles.

- **Telemetry Service (`services/telemetry.py`)**
  - Periodically collects data for reports and dashboards.
  - Stores data in `DeviceTelemetry` and `InterfaceTelemetry`.
  - Used for real-time monitoring and historical analytics.

- **DB Manager (`services/dbmanager.py`)**
  - Synchronizes device and interface metadata with DB.
  - Handles config versioning and drift detection.

#### 3. Reports & Telemetry
- Device uptime, configuration drift, software versions.
- Interface utilization reports.
- Export to CSV/PDF.

#### 4. User & Permission Management
- Organization/site-level access control.
- Role-based permissions.

#### 5. UI/UX Enhancements
- Device detail with clear tabs:
  - **Basic Info**, **Configuration**, **Interfaces**, **Tasks/Logs**, **Telemetry**
- Job/task progress indicators.
- (Optional) Live updates with WebSockets.

#### 6. Monitoring & Logging
- Add monitoring/logging (like Prometheus, Loki, Grafana, Sentry).

---

## Phase 3 — Frontend UI & Workflows
**Goal:** Improve operator UX and workflows.

- Build HTMX or React-based frontend.
- Async actions for backups, upgrades, CLI commands.
- Task status widgets and dashboards.

---

## Phase 4 — Reports, Integrations & Smart Automation
**Goal:** Enterprise-level observability and automation.

- Zero-Touch Provisioning workflow.
- Integrations (NetBox, SolarWinds, Ansible Tower).
- Smart recommendations for firmware/version drift.
- Predictive analytics (future option).

---

### ✅ Current Focus
- **UX Polish & Data Import**
  - Device detail layout improvement.
  - Interface pagination & filtering.
  - CSV/Excel import/export.
- **Next Phase:** Automation & Telemetry Services
