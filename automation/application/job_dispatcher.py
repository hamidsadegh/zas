# automation/application/job_dispatcher.py
from automation.choices import JobStatus

class JobDispatcher:
    @staticmethod
    def dispatch_backup(run):
        from automation.tasks import run_backup_job
        run.status = JobStatus.QUEUED
        run.save(update_fields=["status"])

        run_backup_job.delay(run.id)
    
    @staticmethod
    def dispatch_reachability(run):
        from automation.tasks import run_reachability_job
        run.status = JobStatus.QUEUED
        run.save(update_fields=["status"])
        run_reachability_job.delay(run.id)
