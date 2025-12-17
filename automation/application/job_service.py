from django.db import transaction
from automation.models.automation_job import AutomationJob
from automation.models.job_run import JobRun
from automation.choices import JobType, JobStatus


class JobService:
    @staticmethod
    @transaction.atomic
    def create_backup_job(*, devices, created_by):
        job = AutomationJob.objects.create(
            job_type=JobType.CONFIG_BACKUP,
            status=JobStatus.PENDING,
            created_by=created_by,
        )

        run = JobRun.objects.create(
            job=job,
            status=JobStatus.PENDING,
        )

        run.devices.set(devices)

        return job, run
    
    @staticmethod
    @transaction.atomic
    def create_reachability_job(*, devices, created_by, params=None):
        job = AutomationJob.objects.create(
            job_type=JobType.REACHABILITY,
            status=JobStatus.PENDING,
            created_by=created_by,
        )
        run = JobRun.objects.create(
            job=job,
            status=JobStatus.PENDING,
            params=params or {},
        )
        run.devices.set(devices)
        return job, run
