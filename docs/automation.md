# Automation App Documentation

The `automation` module handles automated tasks such as reachability, backups, configuration changes, and device provisioning.

## Tasks

- `tasks.py`
  - Example: daily backup job, device config sync, rechability check
- Using `Celery` for scheduling

## Workflow
Celery Task  →  Worker  →  Engines  →  DB Models

- Dependencies:
  - Install GitPython for Git storage: `pip install gitpython`

- Device Reachability in Detail:
Celery Beat (schedule) 
  → Celery Worker (task) 
    → automation.scheduler.check_devices_reachability
      → JobRun created/loaded
        → execute_job(job_run) in workers.job_runner
          → ReachabilityEngine.update_device_status(...)
            → ping/snmp/ssh/netconf checks
              → DeviceRuntimeStatus saved
          → JobRun.log + status updated

- Configuration Backup:
Celery Beat  →  Celery Worker →  automation.scheduler.schedule_configuration_backups
                                   ↓
                             SSHEngine (Netmiko wrapper)
                                   ↓
                          Command Map (per platform/type)
                                   ↓
                      Save result in DeviceConfig model




