# Automation App Documentation


### new 16.12.2025
## The boring spine (explicitly)
[ API / UI / Admin ]
          ↓
   Application Services
          ↓
     Domain Logic
          ↓
 Infrastructure (DB / SSH / SNMP / Git / Celery)

# Workflow
Schedule / API / Admin
   ↓
JobService (create job+run)
   ↓
JobDispatcher (queue)
   ↓
Celery task (glue)
   ↓
Worker (exec)
   ↓
JobResultService (persist)

# Freeze the write path
Rule #1 of the spine
  Models are dumb.
  Domain services are the only writers.

Example (dcim):
dcim/
├── domain
│   ├── device.py          ← invariants
│   ├── vlan.py
│   └── area.py
├── application
│   ├── device_service.py  ← CREATE / UPDATE / DELETE
│   └── vlan_service.py

automation/
├── application
│   ├── job_service.py        ← creates jobs, validates intent
│   ├── job_dispatcher.py     ← queues celery tasks
│   └── job_result_service.py ← persists results
├── workers
│   ├── backup_worker.py      ← executes, never decides
│   └── ssh_worker.py

A job lifecycle is deterministic
Application services decide what to do is
Workers execute
Engines are pure adapters (pure functions + IO)
    engine.run()
    engine.save_to_db()
    engine.create_diff()
Models store truth




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

### Automation rules by device status
INVENTORY        → read-only
PLANNED          → read-only
STAGED           → discovery updates allowed
ACTIVE           → config push allowed
FAILED           → no automation
DECOMMISSIONING  → teardown only





