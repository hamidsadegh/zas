import pytest

from automation.choices import JobType, JobStatus
from automation.application import job_service


@pytest.mark.django_db
def test_job_service_creates_backup_job(devices, user):
    job, run = job_service.JobService.create_backup_job(
        devices=devices,
        created_by=user,
    )

    assert job.job_type == JobType.CONFIG_BACKUP
    assert run.status == JobStatus.PENDING
    assert run.devices.count() == devices.count()

