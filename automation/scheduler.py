 # automation/scheduler.py
import logging
from os import name

from dcim.models import Device
from automation.models import AutomationJob, JobRun
from automation.backup_tasks.config_backup import backup_device_config
from automation.workers.job_runner import execute_job
from accounts.services.settings_service import (
    get_reachability_checks,
    get_system_settings,
)
from celery import shared_task


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# REACHABILITY SCHEDULER
# ---------------------------------------------------------------------
@shared_task
def check_devices_reachability(tags: list = None):
    if tags is None:
        tags = ["reachability_check_tag"]
    
    settings = get_system_settings()
    checks = get_reachability_checks(settings)

    # If all checks are disabled → don't schedule job
    if not any(checks.values()):
        logger.info("Reachability check skipped: all probes disabled.")
        return "disabled"

    # Ensure the reachability job exists
    job, _ = AutomationJob.objects.get_or_create(
        job_type="reachability",
        defaults={
            "name": "Reachability Sweep",
            "description": "Automated reachability verification",
        },
    )

    # Create a new JobRun
    job_run = JobRun.objects.create(job=job)

    # Assign taged devices for this run
    devices = Device.objects.filter(tags__name__in=tags).distinct()
    job_run.devices.set(devices)

    if not devices.exists():
        logger.info("Reachability check skipped: no devices found.")

    # Delegate the actual execution to the job runner worker
    execute_job(
        job_run,
        reachability_checks=checks,
        system_settings=settings,
    )

    logger.info(f"Reachability job triggered for tags: {tags}.")
    return "scheduled"


# ---------------------------------------------------------------------
# BACKUP SCHEDULER
# ---------------------------------------------------------------------
@shared_task
def schedule_configuration_backups():
    """
    Schedules configuration backup tasks for all devices tagged
    with 'config_backup_tag'. Each device is backed up by
    an individual Celery task.
    """
    devices = Device.objects.filter(tags__name="config_backup_tag").distinct()

    for device in devices:
        backup_device_config.delay(str(device.id))

    logger.info(f"Scheduled configuration backups for {devices.count()} devices.")
    return "scheduled"
