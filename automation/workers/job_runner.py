from django.utils import timezone

from automation.models import JobRun
from automation.workers.ssh_worker import run_ssh_job
from automation.workers.backup_worker import run_backup_job
from automation.workers.reachability_worker import run_reachability_job


def execute_job(job_run: JobRun, reachability_checks=None, system_settings=None):
    """
    Delegates a JobRun to the correct worker based on job_type.
    Updates JobRun lifecycle fields.
    """

    job = job_run.job
    job_run.status = JobRun.STATUS_RUNNING
    job_run.started_at = timezone.now()
    job_run.save(update_fields=["status", "started_at"])

    try:
        if job.job_type == "cli":
            log = run_ssh_job(job_run)

        elif job.job_type == "backup":
            log = run_backup_job(job_run)

        elif job.job_type == "reachability":
            log = run_reachability_job(
                job_run=job_run,
                reachability_checks=reachability_checks,
                system_settings=system_settings,
            )

        else:
            log = f"Unknown job type: {job.job_type}"

        job_run.log = log
        job_run.status = JobRun.STATUS_SUCCESS

    except Exception as exc:
        job_run.log = f"Error: {exc}"
        job_run.status = JobRun.STATUS_FAILED

    job_run.finished_at = timezone.now()
    job_run.save(update_fields=["log", "status", "finished_at"])
