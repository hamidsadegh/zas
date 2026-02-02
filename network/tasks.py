import ipaddress
import logging
from types import SimpleNamespace

from celery import shared_task
from django.utils import timezone

from network.models.discovery import (
    AutoAssignJob,
    AutoAssignJobItem,
    DiscoveryCandidate,
    DiscoveryScanJob,
)
from network.services.auto_assignment_service import AutoAssignmentService
from network.services.discover_network import NetworkDiscoveryService

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


@shared_task(bind=True)
def run_discovery_scan_job(self, job_id: str) -> None:
    try:
        job = DiscoveryScanJob.objects.get(id=job_id)
    except DiscoveryScanJob.DoesNotExist:
        logger.error("Discovery scan job %s not found.", job_id)
        return

    if not job.site:
        job.status = DiscoveryScanJob.Status.FAILED
        job.error_message = "Job has no site assigned."
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
        return

    job.status = DiscoveryScanJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    service = NetworkDiscoveryService(site=job.site)
    alive = 0
    processed = 0

    try:
        if job.scan_kind == "all":
            ranges = list(service._get_ranges())
        else:
            ranges = []
            method = job.scan_method or "tcp"
            port = job.scan_port or 22
            params = job.scan_params or {}

            if job.scan_kind == "single":
                ip_value = (params.get("single_ip") or "").strip()
                ip_obj = ipaddress.ip_address(ip_value)
                prefix = 32 if ip_obj.version == 4 else 128
                ranges = [
                    SimpleNamespace(
                        cidr=f"{ip_obj}/{prefix}",
                        scan_method=method,
                        scan_port=port,
                    )
                ]
            elif job.scan_kind == "cidr":
                cidr_value = (params.get("cidr") or "").strip()
                network = ipaddress.ip_network(cidr_value, strict=False)
                ranges = [
                    SimpleNamespace(
                        cidr=str(network),
                        scan_method=method,
                        scan_port=port,
                    )
                ]
            elif job.scan_kind == "range":
                start_ip = ipaddress.ip_address((params.get("start_ip") or "").strip())
                end_ip = ipaddress.ip_address((params.get("end_ip") or "").strip())
                if start_ip.version != end_ip.version:
                    raise ValueError("Start and end IP versions must match.")
                if int(start_ip) > int(end_ip):
                    raise ValueError("Start IP must be before end IP.")
                ranges = [
                    SimpleNamespace(
                        cidr=str(net),
                        scan_method=method,
                        scan_port=port,
                    )
                    for net in ipaddress.summarize_address_range(start_ip, end_ip)
                ]
            else:
                raise ValueError("Unsupported scan type.")

        job.total_ranges = len(ranges)
        job.save(update_fields=["total_ranges"])

        for dr in ranges:
            alive += service._scan_range(dr)
            processed += 1
            job.processed_ranges = processed
            job.alive_count = alive
            job.save(update_fields=["processed_ranges", "alive_count"])

        updated_candidates = DiscoveryCandidate.objects.filter(
            site=job.site,
            classified=False,
            last_seen=service.now,
        )
        exact, mismatch, new = service._classify(updated_candidates)

        job.exact_count = exact
        job.mismatch_count = mismatch
        job.new_count = new
        job.status = DiscoveryScanJob.Status.COMPLETED
    except Exception as exc:
        logger.exception("Discovery scan job %s failed.", job_id)
        job.status = DiscoveryScanJob.Status.FAILED
        job.error_message = str(exc)
    finally:
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "processed_ranges",
                "alive_count",
                "exact_count",
                "mismatch_count",
                "new_count",
                "completed_at",
                "error_message",
                "total_ranges",
            ]
        )
