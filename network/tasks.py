import logging

from celery import shared_task
from django.utils import timezone

from network.models.discovery import AutoAssignJob, AutoAssignJobItem, DiscoveryCandidate
from network.services.auto_assignment_service import AutoAssignmentService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_auto_assign_job(self, job_id: str, candidate_ids: list[str]) -> None:
    try:
        job = AutoAssignJob.objects.get(id=job_id)
    except AutoAssignJob.DoesNotExist:
        logger.error("Auto-assign job %s not found.", job_id)
        return

    job.status = AutoAssignJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    success = 0
    failed = 0
    candidates = DiscoveryCandidate.objects.filter(id__in=candidate_ids).select_related("site")
    candidate_map = {str(candidate.id): candidate for candidate in candidates}

    try:
        for candidate_id in candidate_ids:
            candidate = candidate_map.get(str(candidate_id))
            if not candidate:
                failed += 1
                AutoAssignJobItem.objects.create(
                    job=job,
                    success=False,
                    error_message="Candidate not found.",
                )
                continue

            try:
                result = AutoAssignmentService(candidate, include_config=job.include_config).assign()
            except Exception as exc:
                logger.exception("Auto-assignment crashed for candidate %s", candidate)
                result = {"success": False, "error": str(exc), "device": None}

            if result.get("success"):
                success += 1
            else:
                failed += 1

            AutoAssignJobItem.objects.create(
                job=job,
                candidate=candidate,
                site=candidate.site,
                hostname=candidate.hostname or "",
                ip_address=candidate.ip_address,
                success=bool(result.get("success")),
                device=result.get("device"),
                error_message=result.get("error") or "",
            )

        job.status = AutoAssignJob.Status.COMPLETED
    except Exception as exc:
        logger.exception("Auto-assign job %s failed.", job_id)
        job.status = AutoAssignJob.Status.FAILED
        job.error_message = str(exc)
    finally:
        job.success_count = success
        job.failure_count = failed
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "success_count",
                "failure_count",
                "completed_at",
                "error_message",
            ]
        )
