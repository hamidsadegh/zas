import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from dcim.models import Device
from automation.models import AutomationJob, JobRun
from automation.workers.job_runner import execute_job
from accounts.services.settings_service import (
    get_reachability_checks,
    get_snmp_config,
    get_system_settings,
)

from automation.backup_tasks.config_backup import backup_device_config


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# REACHABILITY SCHEDULER
# ---------------------------------------------------------------------
@shared_task
def check_devices_reachability(tags: list = None):
    """
    Periodic scheduler for reachability checks.
    Creates a JobRun and delegates execution to job_runner.
    """
    settings = get_system_settings()
    checks = get_reachability_checks(settings)

    # Default to all tags if none specified
    if tags is None:
        tags = ["reachability_check"]

    # If all checks are disabled → don't schedule job
    if not any(checks.values()):
        logger.info("Reachability check skipped: all probes disabled.")
        return "disabled"

    # Enforce minimum interval (from system settings)
    interval = timedelta(minutes=settings.reachability_interval_minutes or 1)
    now = timezone.now()

    # Check last run time to enforce interval
    last = settings.reachability_last_run
    if last and (now - last) < interval:
        logger.debug("Reachability check waiting for interval window.")
        return "waiting"

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
        snmp_config=get_snmp_config(settings), 
        reachability_checks=checks,
        system_settings=settings
    )

    logger.info("%s: reachability job triggered for tags: %s.", now, tags)
    return "scheduled"


# ---------------------------------------------------------------------
# BACKUP SCHEDULER
# ---------------------------------------------------------------------
@shared_task
def schedule_configuration_backups():
    """
    Schedules configuration backup tasks for all devices tagged
    with 'configuration_backup'. Each device is backed up by
    an individual Celery task.
    """
    devices = Device.objects.filter(tags__name="configuration_backup").distinct()

    for device in devices:
        backup_device_config.delay(str(device.id))

    logger.info(f"Scheduled configuration backups for {devices.count()} devices.")
    return "scheduled"