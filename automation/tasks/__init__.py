# automation/tasks.py
# MAke the ZAS Spine
from datetime import timedelta
from django.utils import timezone
from celery import shared_task

from dcim.models import Device
from automation.choices import JobType
from automation.choices import JobStatus
from dcim.choices import DeviceStatusChoices
from automation.models import JobRun, AutomationJob
from automation.application import JobService, JobDispatcher, JobResultService
from automation.application import ReachabilityPersistenceService, ReachabilityService
from automation.workers.backup_worker import execute_backup
from accounts.services.settings_service import get_system_settings
from automation.workers.reachability_worker import execute_reachability


@shared_task(bind=True)
def run_reachability_job(self, run_id):
    run = JobRun.objects.select_related("job").get(id=run_id)

    run.status = JobStatus.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])

    try:
        checks = (run.params or {}).get("checks", {})
        payload = execute_reachability(run, checks=checks)

        # persist runtime status (DB writes live here/application)
        ReachabilityPersistenceService.persist(payload)

        # store payload in the run for audit/debug
        JobResultService.finalize_success(run, payload)

    except Exception as exc:
        JobResultService.finalize_failure(run, exc)
        raise
    finally:
        run.finished_at = timezone.now()
        run.save(update_fields=["finished_at"])


@shared_task
def run_scheduled_reachability():
    settings = get_system_settings()

    devices = Device.objects.filter(
        status=DeviceStatusChoices.STATUS_ACTIVE,
        tags__name="reachability_check_tag",
    ).distinct()

    if not devices.exists():
        return

    ReachabilityService.start_reachability_job(
        devices=devices,
        created_by=None,
        system_settings=settings,
    )


@shared_task(bind=True)
def run_backup_job(self, run_id):
    run = JobRun.objects.select_related("job").get(id=run_id)

    run.status = JobStatus.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])

    try:
        artifacts = execute_backup(run)
        JobResultService.finalize_success(run, artifacts)
    except Exception as exc:
        JobResultService.finalize_failure(run, exc)
        raise
    finally:
        run.finished_at = timezone.now()
        run.save(update_fields=["finished_at"])


@shared_task
def run_scheduled_config_backup():
    """
    Entry point for scheduled config backups.
    NO business logic beyond orchestration.
    """

    devices = Device.objects.filter(
        status=DeviceStatusChoices.STATUS_ACTIVE,
        tags__name="config_backup_tag"
    ).distinct()

    if not devices.exists():
        return "No devices with config_backup_tag found"


    job, run = JobService.create_backup_job(
        devices=devices,
        created_by=None,
    )

    JobDispatcher.dispatch_backup(run)

    return f"Scheduled config backup started: job={job.id}"


@shared_task
def cleanup_reachability_history(days: int = 7):
    cutoff = timezone.now() - timedelta(days=days)

    runs = JobRun.objects.filter(
        job__job_type=JobType.REACHABILITY,
        created_at__lt=cutoff,
    )

    job_ids = runs.values_list("job_id", flat=True)

    runs.delete()
    AutomationJob.objects.filter(
        id__in=job_ids,
        job_type=JobType.REACHABILITY,
    ).delete()


from .topology_collector import collect_topology_neighbors, cleanup_topology_neighbors  # noqa: E402,F401
