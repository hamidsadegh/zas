import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from automation.models import AutomationJob, JobRun
from automation.workers.job_runner import execute_job
from dcim.models import Device
from accounts.services.settings_service import (
    get_reachability_checks,
    get_snmp_config,
    get_system_settings,
)

logger = logging.getLogger(__name__)

@shared_task
def check_devices_reachability():
    settings = get_system_settings()
    checks = get_reachability_checks(settings)

    if not any(checks.values()):
        logger.info("Reachability check skipped: all probes disabled.")
        return "disabled"

    interval = timedelta(minutes=settings.reachability_interval_minutes or 1)
    now = timezone.now()
    if settings.reachability_last_run and (now - settings.reachability_last_run) < interval:
        logger.debug("Reachability check waiting for interval window.")
        return "waiting"

    job, _ = AutomationJob.objects.get_or_create(
        job_type="reachability",
        defaults={
            "name": "Reachability Sweep",
            "description": "Automated reachability verification",
        },
    )
    job_run = JobRun.objects.create(job=job)
    devices = Device.objects.all()
    job_run.devices.set(devices)

    if not devices.exists():
        logger.info("Reachability check skipped: no devices found.")

    execute_job(job_run, snmp_config=get_snmp_config(settings), reachability_checks=checks)
    logger.info("%s: reachability job triggered.", now)
    return "scheduled"


def run_scheduled_backups():
    """Run all jobs of type 'backup' that are marked as scheduled."""
    backup_jobs = AutomationJob.objects.filter(job_type='backup')
    for job in backup_jobs:
        job_run = JobRun.objects.create(job=job)
        job_run.devices.set(Device.objects.all())  # optionally filter by org/site
        execute_job(job_run)
        logger.info(f"{timezone.now()}: backup job {job.name} executed.")
