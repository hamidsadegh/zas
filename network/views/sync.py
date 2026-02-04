from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from dcim.models import Device
from network.services.sync_service import SyncService


@login_required
def sync_device(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method != "POST":
        return redirect("device_detail", pk=device.id)

    include_config = False # request.POST.get("no_config") != "1"
    service = SyncService(site=device.site)
    result = service.sync_device(device, include_config=include_config)
    if result.get("skipped"):
        messages.warning(request, f"Sync skipped for {device.name}: {result.get('error')}")
    elif result.get("success"):
        messages.success(request, f"Sync triggered for {device.name}.")
    else:
        messages.error(request, f"Sync failed for {device.name}: {result.get('error')}")
    return redirect("device_detail", pk=device.id)
