# Automation App Documentation

The `automation` module handles automated tasks such as backups, configuration changes, and device provisioning.

## Tasks

- `tasks.py`
  - Example: daily backup job, device config sync
- Can use `Celery` or `Django management commands` for scheduling

## Services

- `devices/services/ssh_service.py`: SSH connectivity for devices
- `devices/services/snmp_service.py`: SNMP data collection
- `devices/services/db_manager.py`: Database serialization/deserialization

