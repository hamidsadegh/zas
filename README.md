# ZAS - Zentrales Administration- und Automation System

ZAS is a centralized administration and automation system for network devices.
It is designed to manage devices, perform configuration changes, and generate reports
in a web-based interface. ZAS complements existing network management tools like Cisco Prime
or APIC for ACI fabrics.

## Features (Phase 1)
- Device management with hierarchical Areas and Organizations
- Device attributes: Hardware, Software, Operational
- Device Configuration and Interfaces
- HTML views and REST API endpoints
- Search, sorting, and pagination
- User authentication and access control

## Technologies
- Backend: Python 3.11, Django 5.2, MariaDB
- Frontend: Django templates + Bootstrap
- API: Django REST Framework
- Docker for containerized deployment

## Quick Start (Docker)
```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

