from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Q
from dcim.models.device import Device
from dcim.models.interface import Interface
from dcim.models.vendor import Vendor
from django.views import View


# -----------------------
# Home View
# -----------------------
@login_required
def home(request):
    """Home dashboard page with quick health metrics"""
    device_stats = Device.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status="active")),
        inactive=Count("id", filter=Q(status="inactive")),
        maintenance=Count("id", filter=Q(status="maintenance")),
        unknown=Count("id", filter=Q(status="unknown")),
    )

    interface_stats = Interface.objects.aggregate(
        total=Count("id"),
        up=Count("id", filter=Q(status="up")),
        down=Count("id", filter=Q(status="down")),
        disabled=Count("id", filter=Q(status="disabled")),
    )

    recent_devices = (
        Device.objects.select_related("area", "vendor", "device_type")
        .order_by("-created_at")[:5]
    )

    recent_checks = (
        Device.objects.select_related("runtime")
        .filter(runtime__last_check__isnull=False)
        .order_by("-runtime__last_check")[:5]
    )

    top_vendors = (
        Vendor.objects.annotate(device_count=Count("devices"))
        .order_by("-device_count")[:5]
    )

    context = {
        "device_stats": device_stats,
        "interface_stats": interface_stats,
        "recent_devices": recent_devices,
        "recent_checks": recent_checks,
        "top_vendors": top_vendors,
    }
    return render(request, "core/templates/core/home.html", context)


