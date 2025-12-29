Celery Architecture

┌──────────────────────────┐
│        Django App        │
│                          │
│  Admin / UI / API        │
│                          │
│  - Device CRUD           │
│  - Tags                  │
│  - AutomationSchedule    │
│  - SystemSettings        │
└─────────────┬────────────┘
              │
              │ writes / updates
              ▼
┌──────────────────────────┐
│        Database          │
│                          │
│  - Device                │
│  - Tag                   │
│  - AutomationJob         │
│  - JobRun                │
│  - AutomationSchedule    │
│  - django_celery_beat_*  │
└─────────────┬────────────┘
              │
              │ django-celery-beat
              │ polls DB schedules
              ▼
┌──────────────────────────┐
│       Celery Beat        │
│                          │
│  Reads PeriodicTask      │
│  rows from DB            │
│                          │
│  Emits scheduled tasks   │
└─────────────┬────────────┘
              │
              │ Redis (broker)
              ▼
┌──────────────────────────┐
│        Redis             │
│                          │
│  Task queue              │
│  (messages only)         │
└─────────────┬────────────┘
              │
              │ consumes tasks
              ▼
┌──────────────────────────┐
│      Celery Worker       │
│  (zas-celery.service)    │
│                          │
│  Registered tasks:       │
│                          │
│  - automation.tasks.     │
│    run_scheduled_        │
│    reachability          │
│                          │
│  - automation.tasks.     │
│    run_scheduled_        │
│    config_backup         │
│                          │
│  - automation.tasks.     │
│    cleanup_reachability_ │
│    history               │
└─────────────┬────────────┘
              │
              │ calls
              ▼
┌──────────────────────────┐
│      Job Orchestration   │
│                          │
│  automation.workers.     │
│  job_runner.execute_job  │
│                          │
│  - creates JobRun        │
│  - updates status        │
│  - dispatches engines    │
└─────────────┬────────────┘
              │
              │ delegates work
              ▼
┌─────────────────────────────────────────┐
│               Engines                   │
│                                         │
│  automation.engine.*                    │
│                                         │
│  - ReachabilityEngine                   │
│     • ping                              │
│     • snmp                              │
│     • ssh                               │
│     • netconf                           │
│                                         │
│  - SSHEngine                            │
│  - SNMPEngine                           │
│  - NetconfEngine                        │
└─────────────┬───────────────────────────┘
              │
              │ writes results
              ▼
┌──────────────────────────┐
│        Database          │
│                          │
│  - DeviceRuntimeStatus   │
│  - DeviceConfiguration   │
│  - JobRun.result/log     │
└──────────────────────────┘

How data flows (plain language)
1️⃣ Scheduling
You create or edit AutomationSchedule (via Admin or API)
django-celery-beat mirrors it into PeriodicTask

2️⃣ Trigger
Celery Beat wakes up
Sends task name + args to Redis
Example:
automation.tasks.run_scheduled_reachability

3️⃣ Execution
Celery Worker receives the task
Task function runs (@shared_task)
Task does not do heavy work

4️⃣ Orchestration
Scheduler task creates:
AutomationJob (if missing)
JobRun
Calls:
execute_job(job_run, ...)

5️⃣ Real Work
job_runner:
loads devices
calls engines
updates runtime status
stores results

6️⃣ Persistence
Results live in DB
UI / API only reads results
No polling the worker directly
