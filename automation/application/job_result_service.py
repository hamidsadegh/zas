# automation/application/job_result_service.py

from automation.choices import JobStatus

class JobResultService:
    @staticmethod
    def finalize_success(run, artifacts):
        run.status = JobStatus.SUCCESS
        run.result = {"artifacts": artifacts}
        run.save(update_fields=["status", "result"])

        job = run.job
        job.status = JobStatus.SUCCESS
        job.save(update_fields=["status"])

    @staticmethod
    def finalize_failure(run, error):
        run.status = JobStatus.FAILED
        run.result = {"error": str(error)}
        run.save(update_fields=["status", "result"])

        job = run.job
        job.status = JobStatus.FAILED
        job.save(update_fields=["status"])
