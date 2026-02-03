import ipaddress
import logging
from types import SimpleNamespace

from celery import shared_task
from django.utils import timezone

from dcim.choices import DeviceStatusChoices
from dcim.models import Device
from network.models.discovery import (
    AutoAssignJob,
    AutoAssignJobItem,
    DiscoveryCandidate,
    DiscoveryRange,
    DiscoveryScanJob,
)
from network.services.auto_assignment_service import AutoAssignmentService
from network.services.discover_network import NetworkDiscoveryService
from network.services.sync_service import SyncService

logger = logging.getLogger(__name__)
SYNC_EXCLUDE_TAG = "no_sync"


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


@shared_task
def run_scheduled_sync_job(include_config: bool = False):
    devices = (
        Device.objects.filter(status=DeviceStatusChoices.STATUS_ACTIVE)
        .exclude(tags__name=SYNC_EXCLUDE_TAG)
        .select_related("site")
        .distinct()
    )
    if not devices.exists():
        return {"success": 0, "failed": 0, "skipped": 0}

    success = 0
    failed = 0

    for device in devices:
        try:
            service = SyncService(site=device.site)
            result = service.sync_device(device, include_config=include_config)
            if result.get("success"):
                success += 1
            else:
                failed += 1
                logger.warning("Scheduled sync failed for %s: %s", device.name, result.get("error"))
        except Exception as exc:
            failed += 1
            logger.exception("Scheduled sync crashed for %s: %s", device.name, exc)

    return {"success": success, "failed": failed, "skipped": 0}


@shared_task
def run_scheduled_discovery_scan_job():
    site_ids = (
        DiscoveryRange.objects.filter(enabled=True)
        .values_list("site_id", flat=True)
        .distinct()
    )
    if not site_ids:
        return {"scheduled": 0, "skipped": 0}

    scheduled = 0
    for site_id in site_ids:
        job = DiscoveryScanJob.objects.create(
            requested_by=None,
            site_id=site_id,
            scan_kind="all",
            scan_method="tcp",
            scan_port=22,
        )
        run_discovery_scan_job.delay(str(job.id))
        scheduled += 1

    return {"scheduled": scheduled, "skipped": 0}


@shared_task
def run_scheduled_auto_assign_job(include_config: bool = True):
    candidates = DiscoveryCandidate.objects.filter(accepted__isnull=True, classified=False)
    candidate_ids = [str(candidate_id) for candidate_id in candidates.values_list("id", flat=True)]
    if not candidate_ids:
        return {"scheduled": 0, "candidates": 0}

    job = AutoAssignJob.objects.create(
        requested_by=None,
        site=None,
        candidate_hostname="",
        limit=None,
        include_config=include_config,
        candidate_ids=candidate_ids,
        total_candidates=len(candidate_ids),
        status=AutoAssignJob.Status.PENDING,
    )
    run_auto_assign_job.delay(str(job.id), candidate_ids)
    return {"scheduled": 1, "candidates": len(candidate_ids)}
