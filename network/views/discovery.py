import ipaddress
from types import SimpleNamespace

from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from network.models.discovery import (
    AutoAssignJob,
    AutoAssignJobItem,
    DiscoveryCandidate,
    DiscoveryFilter,
    DiscoveryRange,
    DiscoveryScanJob,
)
from network.services.discover_network import NetworkDiscoveryService
from network.tasks import run_auto_assign_job, run_discovery_scan_job
from dcim.models import (
    Area,
    Device,
    DeviceRole,
    DeviceRuntimeStatus,
    DeviceType,
    Rack,
    Site,
    Tag,
)


class CandidateDeviceForm(forms.ModelForm):
    """Creation form constrained to a discovery candidate."""

    class Meta:
        model = Device
        fields = [
            "name",
            "management_ip",
            "site",
            "area",
            "rack",
            "role",
            "device_type",
            "status",
            "inventory_number",
            "tags",
            "position",
        ]

    def __init__(self, candidate, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.candidate = candidate

        self.fields["name"].initial = candidate.hostname or str(candidate.ip_address).replace(".", "-")
        self.fields["name"].required = True

        self.fields["management_ip"].initial = candidate.ip_address
        self.fields["management_ip"].disabled = True
        self.fields["management_ip"].required = False

        self.fields["site"].initial = candidate.site
        self.fields["site"].queryset = Site.objects.filter(id=candidate.site_id)
        self.fields["site"].disabled = True
        self.fields["site"].required = False

        self.fields["area"].queryset = Area.objects.filter(site=candidate.site).order_by("name")
        self.fields["area"].required = True

        area_id = self.data.get("area") or (self.initial.get("area").id if self.initial.get("area") else None)
        rack_id = self.data.get("rack") or (self.initial.get("rack").id if self.initial.get("rack") else None)

        if area_id:
            self.fields["rack"].queryset = Rack.objects.filter(area_id=area_id).order_by("name")
        else:
            self.fields["rack"].queryset = Rack.objects.none()

        self.fields["role"].required = True
        self.fields["device_type"].required = False
        self.fields["device_type"].queryset = DeviceType.objects.all().order_by("vendor__name", "model")
        self.fields["status"].required = True
        self.fields["status"].initial = Device._meta.get_field("status").default
        self.fields["inventory_number"].required = False
        self.fields["tags"].required = False
        self.fields["tags"].queryset = Tag.objects.all().order_by("name")
        self.fields["position"].required = False
        self.fields["area"].widget.attrs["data-racks-url"] = reverse("racks_for_area")
        self.fields["rack"].widget.attrs["data-current"] = str(rack_id) if rack_id else ""

        self.order_fields(
            [
                "name",
                "management_ip",
                "site",
                "area",
                "rack",
                "position",
                "role",
                "device_type",
                "status",
                "inventory_number",
                "tags",
            ]
        )

    def clean(self):
        cleaned = super().clean()
        area = cleaned.get("area")
        rack = cleaned.get("rack")
        position = cleaned.get("position")

        if area and area.site_id != self.candidate.site_id:
            self.add_error("area", "Area must belong to the same site as the candidate.")

        if rack and area and rack.area_id != area.id:
            self.add_error("rack", "Rack must belong to the selected area.")

        if position and not rack:
            self.add_error("position", "Set a rack before assigning a position.")

        return cleaned


@login_required
def discovery_dashboard(request):
    qs = DiscoveryCandidate.objects.select_related("site")
    context = {
        "total": qs.count(),
        "exact_matches": qs.filter(accepted=True).count(),
        "mismatches": qs.filter(accepted=False).count(),
        "new_or_unclassified": qs.filter(accepted__isnull=True).count(),
        "unclassified": qs.filter(classified=False).count(),
        "ssh_ok": qs.filter(reachable_ssh=True).count(),
        "ping_ok": qs.filter(reachable_ping=True).count(),
        "last_seen": qs.order_by("-last_seen").first(),
        "site_breakdown": qs.values("site__id", "site__name")
        .order_by("site__name")
        .annotate(
            count_site=models.Count("id"),
            unclassified_count=models.Count("id", filter=models.Q(classified=False)),
        ),
    }
    return render(request, "network/discovery/discovery_dashboard.html", context)


@login_required
def discovery_candidates(request):
    qs = (
        DiscoveryCandidate.objects.select_related("site")
        .annotate(
            status_order=models.Case(
                models.When(accepted=False, then=models.Value(0)),
                models.When(accepted__isnull=True, then=models.Value(1)),
                models.When(accepted=True, then=models.Value(2)),
                default=models.Value(3),
                output_field=models.IntegerField(),
            )
        )
        .order_by("status_order", "-last_seen")
    )

    site_filter = request.GET.get("site", "all")
    status_filter = request.GET.get("status", "all")
    ssh_only = request.GET.get("ssh_only") == "1"
    search_query = request.GET.get("search", "").strip()
    page_number = request.GET.get("page", 1)

    if site_filter != "all":
        qs = qs.filter(site_id=site_filter)

    if status_filter == "exact":
        qs = qs.filter(accepted=True)
    elif status_filter == "mismatch":
        qs = qs.filter(accepted=False)
    elif status_filter == "new":
        qs = qs.filter(accepted__isnull=True)

    if ssh_only:
        qs = qs.filter(reachable_ssh=True)

    if search_query:
        qs = qs.filter(
            models.Q(ip_address__icontains=search_query)
            | models.Q(hostname__icontains=search_query)
            | models.Q(site__name__icontains=search_query)
        )

    paginator = Paginator(qs, 25)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    site_choices = [("all", "All sites")]
    for site in Site.objects.order_by("name"):
        site_choices.append((str(site.id), site.name))

    status_choices = (
        ("all", "All statuses"),
        ("exact", "Exact matches"),
        ("mismatch", "Mismatches"),
        ("new", "New / unclassified"),
    )

    all_candidates = DiscoveryCandidate.objects.all()
    summary = {
        "total": all_candidates.count(),
        "exact": all_candidates.filter(accepted=True).count(),
        "mismatch": all_candidates.filter(accepted=False).count(),
        "new": all_candidates.filter(accepted__isnull=True).count(),
        "filtered": qs.count(),
    }
    context = {
        "candidates": page_obj,
        "page_obj": page_obj,
        "site_choices": site_choices,
        "status_choices": status_choices,
        "site_filter": site_filter,
        "status_filter": status_filter,
        "ssh_only": ssh_only,
        "search_query": search_query,
        "summary": summary,
    }
    return render(request, "network/discovery/candidates.html", context)


@login_required
def discovery_candidates_action(request):
    if request.method != "POST":
        return redirect("network:discovery_candidates")

    action = request.POST.get("action")
    ids = request.POST.getlist("ids")

    if action == "auto_assign":
        include_config_value = request.POST.get("include_config")
        include_config = True if ids and include_config_value is None else bool(include_config_value)
        site_id = request.POST.get("auto_site_id")
        candidate_hostname = (request.POST.get("candidate_hostname") or "").strip()
        limit_raw = request.POST.get("limit") or ""

        qs = DiscoveryCandidate.objects.filter(accepted__isnull=True, classified=False)
        if ids:
            qs = qs.filter(id__in=ids)
        if site_id and site_id != "all":
            qs = qs.filter(site_id=site_id)
        if candidate_hostname:
            qs = qs.filter(hostname__icontains=candidate_hostname)
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            limit = None
        if limit and limit > 0:
            qs = qs[:limit]

        candidates = list(qs)
        if not candidates:
            messages.info(request, "No eligible candidates to auto-assign.")
            return redirect("network:discovery_candidates")

        candidate_ids = [str(candidate.id) for candidate in candidates]
        job = AutoAssignJob.objects.create(
            requested_by=request.user if request.user.is_authenticated else None,
            site_id=site_id if site_id and site_id != "all" else None,
            candidate_hostname=candidate_hostname,
            limit=limit,
            include_config=include_config,
            candidate_ids=candidate_ids,
            total_candidates=len(candidate_ids),
            status=AutoAssignJob.Status.PENDING,
        )
        run_auto_assign_job.delay(str(job.id), candidate_ids)
        messages.info(
            request,
            f"Auto-assign started for {len(candidate_ids)} candidate(s). Job {job.id}.",
        )
        return redirect("network:discovery_candidates")

    if not ids:
        messages.warning(request, "No candidates selected.")
        return redirect("network:discovery_candidates")

    qs = DiscoveryCandidate.objects.filter(id__in=ids).select_related("site")

    locked = qs.filter(accepted=True).count()
    actionable = qs.exclude(accepted=True)

    if locked:
        messages.info(
            request,
            f"Ignored {locked} exact match entr{'y' if locked == 1 else 'ies'} (actions are disabled for exact matches).",
        )

    if action == "ignore":
        updated = actionable.update(classified=True, accepted=False)
        messages.warning(request, f"Marked {updated} candidates as ignored.")
        return redirect("network:discovery_candidates")

    if action == "resolve":
        count = actionable.count()
        messages.info(request, f"Resolve mismatch placeholder invoked for {count} candidate(s).")
        return redirect("network:discovery_candidates")

    if action == "create_device":
        count = actionable.count()
        messages.info(request, f"Create device placeholder invoked for {count} candidate(s).")
        return redirect("network:discovery_candidates")

    messages.error(request, "Unknown action.")
    return redirect("network:discovery_candidates")


@login_required
def auto_assign_jobs(request):
    status_filter = (request.GET.get("status") or "running").strip().lower()
    allowed_statuses = {"running", "pending", "completed", "failed", "all"}
    if status_filter not in allowed_statuses:
        status_filter = "running"

    jobs = AutoAssignJob.objects.select_related("site", "requested_by")
    if request.user.is_authenticated:
        jobs = jobs.filter(requested_by=request.user)
    if status_filter != "all":
        jobs = jobs.filter(status=status_filter)

    report_job_id = (request.GET.get("job") or "").strip()
    report_job = None
    report_items = None
    if report_job_id:
        report_job = jobs.filter(id=report_job_id).first()
        if report_job:
            report_items = (
                AutoAssignJobItem.objects.filter(job=report_job)
                .select_related("device", "site")
                .order_by("created_at")
            )

    paginator = Paginator(jobs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "jobs": page_obj,
        "status_filter": status_filter,
        "status_choices": [
            ("running", "Running"),
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("all", "All"),
        ],
        "report_job": report_job,
        "report_items": report_items,
        "report_job_id": report_job_id,
    }
    return render(request, "network/discovery/auto_assign_jobs.html", context)


@login_required
def discovery_candidate_detail(request, pk):
    candidate = get_object_or_404(
        DiscoveryCandidate.objects.select_related("site"), pk=pk
    )

    hostname = (candidate.hostname or "").lower()
    device_by_ip = Device.objects.filter(
        site=candidate.site, management_ip=candidate.ip_address
    ).first()
    device_by_name = (
        Device.objects.filter(site=candidate.site, name__iexact=hostname).first()
        if hostname
        else None
    )

    if candidate.accepted is True:
        classification = "exact"
        explanation = "Exact match: IP and hostname already known."
        matching_device = device_by_ip or device_by_name
    elif candidate.accepted is False:
        classification = "mismatch"
        matching_device = device_by_ip or device_by_name
        if device_by_ip and device_by_name and device_by_ip.id != device_by_name.id:
            explanation = f"Mismatch: IP belongs to {device_by_ip.name}, hostname belongs to {device_by_name.name}."
        elif device_by_ip:
            explanation = f"Mismatch: IP belongs to {device_by_ip.name}."
        elif device_by_name:
            explanation = f"Mismatch: Hostname belongs to {device_by_name.name}."
        else:
            explanation = "Mismatch: Candidate conflicts with existing device records."
    else:
        matching_device = None
        classification = "new" if candidate.classified else "unclassified"
        explanation = "New: no matching device found." if candidate.classified else "Unclassified: pending review."

    context = {
        "candidate": candidate,
        "classification": classification,
        "explanation": explanation,
        "device_by_ip": device_by_ip,
        "device_by_name": device_by_name,
        "matching_device": matching_device,
    }
    return render(request, "network/discovery/detail.html", context)


@login_required
@transaction.atomic
def resolve_discovery_mismatch(request, pk):
    candidate = get_object_or_404(
        DiscoveryCandidate.objects.select_related("site"), pk=pk
    )

    if candidate.accepted is not False:
        messages.error(
            request,
            "This candidate is not marked as a mismatch.",
        )
        return redirect("network:discovery_candidates")

    hostname = (candidate.hostname or "").lower()
    device_by_ip = Device.objects.filter(
        site=candidate.site, management_ip=candidate.ip_address
    ).first()
    device_by_name = (
        Device.objects.filter(site=candidate.site, name__iexact=hostname).first()
        if hostname
        else None
    )

    if not device_by_ip and not device_by_name:
        messages.error(
            request,
            "No conflicting device was found. Please refresh discovery results.",
        )
        return redirect("network:discovery_candidates")

    ip_mismatch = device_by_name and device_by_name.management_ip != candidate.ip_address
    hostname_mismatch = device_by_ip and hostname and device_by_ip.name.lower() != hostname

    if device_by_ip and device_by_name and device_by_ip.id != device_by_name.id:
        explanation = (
            f"IP belongs to {device_by_ip.name}, hostname belongs to {device_by_name.name}."
        )
    elif hostname_mismatch and device_by_ip:
        explanation = "The discovered hostname differs from the hostname stored for this device."
    elif ip_mismatch and device_by_name:
        explanation = "The discovered IP differs from the management IP stored for this device."
    else:
        explanation = "Discovered attributes differ from existing inventory."

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "cancel":
            return redirect("network:discovery_candidates")

        if action == "ignore":
            candidate.classified = True
            candidate.accepted = False
            candidate.save(update_fields=["classified", "accepted"])
            messages.success(request, "Candidate marked as false positive. Inventory unchanged.")
            return redirect("network:discovery_candidates")

        if action == "update":
            changed = False

            if hostname_mismatch and device_by_ip:
                device_by_ip.name = candidate.hostname or device_by_ip.name
                device_by_ip.save(update_fields=["name"])
                status, _ = DeviceRuntimeStatus.objects.get_or_create(device=device_by_ip)
                status.reachable_ssh |= candidate.reachable_ssh
                status.reachable_ping |= candidate.reachable_ping
                status.last_check = candidate.last_seen or status.last_check
                status.save()
                changed = True

            if ip_mismatch and device_by_name:
                device_by_name.management_ip = candidate.ip_address
                device_by_name.save(update_fields=["management_ip"])
                status, _ = DeviceRuntimeStatus.objects.get_or_create(device=device_by_name)
                status.reachable_ssh |= candidate.reachable_ssh
                status.reachable_ping |= candidate.reachable_ping
                status.last_check = candidate.last_seen or status.last_check
                status.save()
                changed = True

            if not changed:
                messages.info(request, "No changes applied; fields already match.")

            candidate.classified = True
            candidate.accepted = True
            candidate.save(update_fields=["classified", "accepted"])
            messages.success(request, "Device updated to match discovery. Candidate resolved.")
            return redirect("network:discovery_candidates")

        messages.error(request, "Unknown action.")
        return redirect("network:discovery_candidates")

    context = {
        "candidate": candidate,
        "device_by_ip": device_by_ip,
        "device_by_name": device_by_name,
        "primary_device": device_by_ip or device_by_name,
        "has_multiple_conflicts": device_by_ip and device_by_name and device_by_ip.id != device_by_name.id,
        "ip_mismatch": ip_mismatch,
        "hostname_mismatch": hostname_mismatch,
        "explanation": explanation,
    }
    return render(request, "network/discovery/resolve_mismatch.html", context)


@login_required
@transaction.atomic
def create_device_from_candidate(request, pk):
    candidate = get_object_or_404(
        DiscoveryCandidate.objects.select_related("site"), pk=pk
    )

    if candidate.accepted is not None:
        messages.warning(
            request,
            "This candidate has already been reviewed.",
        )
        return redirect("network:discovery_candidates")

    form = CandidateDeviceForm(candidate, request.POST or None)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "cancel":
            return redirect("network:discovery_candidates")

        if action == "ignore":
            candidate.classified = True
            candidate.accepted = False
            candidate.save(update_fields=["classified", "accepted"])
            messages.info(request, "Candidate marked as ignored. No device assigned.")
            return redirect("network:discovery_candidates")

        if action == "create":
            if form.is_valid():
                name = form.cleaned_data["name"]

                if Device.objects.filter(name__iexact=name).exists():
                    form.add_error("name", "A device with this name already exists.")
                if Device.objects.filter(management_ip=candidate.ip_address).exists():
                    form.add_error(None, "A device with this management IP already exists.")

                if not form.errors:
                    device = form.save(commit=False)
                    device.site = candidate.site
                    device.management_ip = candidate.ip_address
                    device.source = "discovery"
                    device.last_seen = candidate.last_seen
                    device.save()
                    form.save_m2m()

                    tag_new, _ = Tag.objects.get_or_create(name="discovered-new")
                    device.tags.add(tag_new)
                    device_name = (device.name or "").lower()
                    if "mgmt" in device_name or "bmsw" in device_name:
                        tag_management, _ = Tag.objects.get_or_create(name="management")
                        device.tags.add(tag_management)

                    status, _ = DeviceRuntimeStatus.objects.get_or_create(device=device)
                    status.reachable_ping |= candidate.reachable_ping
                    status.reachable_ssh |= candidate.reachable_ssh
                    status.last_check = candidate.last_seen or status.last_check
                    status.save()

                    candidate.classified = True
                    candidate.accepted = True
                    candidate.save(update_fields=["classified", "accepted"])

                    messages.success(request, "Device assigned from discovery candidate.")
                    return redirect("device_detail", pk=device.id)

        messages.error(request, "Please correct the errors below.")

    context = {
        "candidate": candidate,
        "form": form,
    }
    return render(request, "network/discovery/assign_device.html", context)


@login_required
def discovery_scan(request):
    sites = list(Site.objects.order_by("name"))
    if not sites:
        messages.error(request, "No sites available for discovery scanning.")
        return render(
            request,
            "network/discovery/scan_network.html",
            {"sites": [], "site": None, "ranges": [], "filters": []},
        )

    site_id = request.GET.get("site") or request.POST.get("site_id")
    site = next((s for s in sites if str(s.id) == str(site_id)), None) or sites[0]

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_range":
            cidr = (request.POST.get("cidr") or "").strip()
            scan_method = request.POST.get("scan_method") or "tcp"
            scan_port = int(request.POST.get("scan_port") or 22)
            description = (request.POST.get("description") or "").strip()
            enabled = request.POST.get("enabled") == "on"
            if cidr:
                DiscoveryRange.objects.update_or_create(
                    site=site,
                    cidr=cidr,
                    defaults={
                        "scan_method": scan_method,
                        "scan_port": scan_port,
                        "description": description,
                        "enabled": enabled,
                    },
                )
                messages.success(request, f"Discovery range {cidr} saved.")
            else:
                messages.error(request, "CIDR is required for a discovery range.")
            return redirect(f"{reverse('network:discovery_scan')}?site={site.id}")

        if action == "update_range":
            range_id = request.POST.get("range_id")
            discovery_range = DiscoveryRange.objects.filter(id=range_id, site=site).first()
            if discovery_range:
                discovery_range.cidr = (request.POST.get("cidr") or "").strip()
                discovery_range.scan_method = request.POST.get("scan_method") or "tcp"
                discovery_range.scan_port = int(request.POST.get("scan_port") or 22)
                discovery_range.description = (request.POST.get("description") or "").strip()
                discovery_range.enabled = request.POST.get("enabled") == "on"
                discovery_range.save()
                messages.success(request, "Discovery range updated.")
            else:
                messages.error(request, "Discovery range not found.")
            return redirect(f"{reverse('network:discovery_scan')}?site={site.id}")

        if action == "delete_range":
            range_id = request.POST.get("range_id")
            DiscoveryRange.objects.filter(id=range_id, site=site).delete()
            messages.success(request, "Discovery range removed.")
            return redirect(f"{reverse('network:discovery_scan')}?site={site.id}")

        if action == "add_filter":
            include = (request.POST.get("hostname_contains") or "").strip()
            exclude = (request.POST.get("hostname_not_contains") or "").strip()
            description = (request.POST.get("description") or "").strip()
            enabled = request.POST.get("enabled") == "on"
            DiscoveryFilter.objects.create(
                site=site,
                hostname_contains=include,
                hostname_not_contains=exclude,
                description=description,
                enabled=enabled,
            )
            messages.success(request, "Discovery filter added.")
            return redirect(f"{reverse('network:discovery_scan')}?site={site.id}")

        if action == "update_filter":
            filter_id = request.POST.get("filter_id")
            discovery_filter = DiscoveryFilter.objects.filter(id=filter_id, site=site).first()
            if discovery_filter:
                discovery_filter.hostname_contains = (request.POST.get("hostname_contains") or "").strip()
                discovery_filter.hostname_not_contains = (request.POST.get("hostname_not_contains") or "").strip()
                discovery_filter.description = (request.POST.get("description") or "").strip()
                discovery_filter.enabled = request.POST.get("enabled") == "on"
                discovery_filter.save()
                messages.success(request, "Discovery filter updated.")
            else:
                messages.error(request, "Discovery filter not found.")
            return redirect(f"{reverse('network:discovery_scan')}?site={site.id}")

        if action == "delete_filter":
            filter_id = request.POST.get("filter_id")
            DiscoveryFilter.objects.filter(id=filter_id, site=site).delete()
            messages.success(request, "Discovery filter removed.")
            return redirect(f"{reverse('network:discovery_scan')}?site={site.id}")

        if action == "scan":
            scan_kind = request.POST.get("scan_kind") or "all"
            scan_method = request.POST.get("scan_method") or "tcp"
            scan_port = int(request.POST.get("scan_port") or 22)

            scan_params = {}
            try:
                if scan_kind == "single":
                    ip_value = (request.POST.get("single_ip") or "").strip()
                    ipaddress.ip_address(ip_value)
                    scan_params["single_ip"] = ip_value
                elif scan_kind == "cidr":
                    cidr_value = (request.POST.get("cidr") or "").strip()
                    ipaddress.ip_network(cidr_value, strict=False)
                    scan_params["cidr"] = cidr_value
                elif scan_kind == "range":
                    start_ip = ipaddress.ip_address((request.POST.get("start_ip") or "").strip())
                    end_ip = ipaddress.ip_address((request.POST.get("end_ip") or "").strip())
                    if start_ip.version != end_ip.version:
                        raise ValueError("Start and end IP versions must match.")
                    if int(start_ip) > int(end_ip):
                        raise ValueError("Start IP must be before end IP.")
                    scan_params["start_ip"] = str(start_ip)
                    scan_params["end_ip"] = str(end_ip)
                elif scan_kind != "all":
                    raise ValueError("Unsupported scan type.")
            except Exception as exc:
                messages.error(request, f"Scan failed: {exc}")
                return redirect(f"{reverse('network:discovery_scan')}?site={site.id}")

            job = DiscoveryScanJob.objects.create(
                requested_by=request.user,
                site=site,
                scan_kind=scan_kind,
                scan_method=scan_method,
                scan_port=scan_port,
                scan_params=scan_params,
            )
            run_discovery_scan_job.delay(str(job.id))
            messages.success(request, "Discovery scan started. This can take a few minutes.")
            return redirect(f"{reverse('network:discovery_scan')}?site={site.id}&job={job.id}")

    ranges = DiscoveryRange.objects.filter(site=site).order_by("cidr")
    filters = DiscoveryFilter.objects.filter(site=site).order_by("id")

    context = {
        "sites": sites,
        "site": site,
        "ranges": ranges,
        "filters": filters,
        "scan_job": None,
        "scan_status_url": None,
        "scan_results_url": None,
    }
    job_id = request.GET.get("job")
    if job_id:
        scan_job = DiscoveryScanJob.objects.filter(id=job_id).first()
        if scan_job:
            context["scan_job"] = scan_job
            context["scan_status_url"] = reverse("network:discovery_scan_status", args=[scan_job.id])
            context["scan_results_url"] = reverse("network:discovery_scan_results", args=[scan_job.id])
    return render(request, "network/discovery/scan_network.html", context)


@login_required
def discovery_scan_status(request, job_id):
    job = get_object_or_404(DiscoveryScanJob, id=job_id)
    return JsonResponse(
        {
            "id": str(job.id),
            "status": job.status,
            "scan_kind": job.scan_kind,
            "total_ranges": job.total_ranges,
            "processed_ranges": job.processed_ranges,
            "alive": job.alive_count,
            "exact": job.exact_count,
            "mismatch": job.mismatch_count,
            "new": job.new_count,
            "error": job.error_message,
        }
    )


@login_required
def discovery_scan_results(request, job_id):
    job = get_object_or_404(DiscoveryScanJob, id=job_id)
    candidates = DiscoveryCandidate.objects.filter(site=job.site)

    if job.started_at:
        candidates = candidates.filter(last_seen__gte=job.started_at)
    if job.completed_at:
        candidates = candidates.filter(last_seen__lte=job.completed_at)

    items = []
    for candidate in candidates.order_by("hostname", "ip_address"):
        if candidate.classified and candidate.accepted is True:
            status = "exact"
        elif candidate.classified and candidate.accepted is False:
            status = "mismatch"
        else:
            status = "new/unclassified"

        items.append(
            {
                "id": str(candidate.id),
                "hostname": candidate.hostname or "",
                "ip_address": str(candidate.ip_address),
                "status": status,
                "detail_url": reverse("network:discovery_candidate_detail", args=[candidate.id]),
            }
        )

    return JsonResponse(
        {
            "id": str(job.id),
            "status": job.status,
            "count": len(items),
            "items": items,
        }
    )
