 # automation/scheduler.py
import logging

from dcim.models import Device
from automation.models import AutomationJob, JobRun
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


# Legacy backup scheduler removed in favor of automation.tasks.run_scheduled_config_backup
