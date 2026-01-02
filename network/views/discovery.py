from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from network.models.discovery import DiscoveryCandidate
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
        .annotate(count_site=models.Count("id")),
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
        "summary": summary,
    }
    return render(request, "network/discovery/candidates.html", context)


@login_required
@transaction.atomic
def discovery_candidates_action(request):
    if request.method != "POST":
        return redirect("network:discovery_candidates")

    action = request.POST.get("action")
    ids = request.POST.getlist("ids")

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
