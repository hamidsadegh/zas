from django.contrib import admin
from django.utils import timezone
from django.contrib import messages

from automation.ssh_consumer import Device
from dcim.models import Tag, DeviceRuntimeStatus
from network.models.discovery import DiscoveryRange, DiscoveryFilter, DiscoveryCandidate


@admin.register(DiscoveryRange)
class DiscoveryRangeAdmin(admin.ModelAdmin):
    list_display = ("site", "cidr", "enabled", "scan_method", "scan_port", "description", "created_at")
    list_filter = ("site", "enabled", "scan_method")
    search_fields = ("cidr", "description", "site__name")
    ordering = ("site__name", "cidr")


@admin.register(DiscoveryFilter)
class DiscoveryFilterAdmin(admin.ModelAdmin):
    list_display = ("site", "enabled", "hostname_contains", "hostname_not_contains", "description", "created_at")
    list_filter = ("site", "enabled")
    search_fields = ("hostname_contains", "hostname_not_contains", "description", "site__name")
    ordering = ("site__name", "-created_at")


@admin.register(DiscoveryCandidate)
class DiscoveryCandidateAdmin(admin.ModelAdmin):
    list_display = (
        "site",
        "ip_address",
        "hostname",
        "reachable_ssh",
        "reachable_ping",
        "accepted",
        "classified",
        "last_seen",
    )
    list_filter = ("site", "accepted", "classified", "reachable_ssh", "reachable_ping")
    search_fields = ("ip_address", "hostname", "site__name")
    ordering = ("site__name", "-last_seen")
    
    actions = ["promote_to_device", "reject_candidates"]
    
    @admin.action(description="Promote selected candidates to Devices")
    def promote_to_device(self, request, queryset):
        tag_new, _ = Tag.objects.get_or_create(name="discovered-new")
        promoted = 0

        for c in queryset.select_related("site"):
            if c.accepted is False:
                continue  # explicitly rejected
            hostname = (c.hostname or "").lower()

            device, created = Device.objects.get_or_create(
                management_ip=c.ip_address,
                defaults={
                    "name": hostname or str(c.ip_address).replace(".", "-"),
                    "site": c.site,
                    "area": c.site.get_or_create_discovered_area(),
                    "source": "discovery",
                },
            )
            status, _ = DeviceRuntimeStatus.objects.get_or_create(device=device)
            status.reachable_ssh |= c.reachable_ssh
            status.reachable_ping |= c.reachable_ping
            status.last_check = c.last_seen or timezone.now()
            status.save()

            if created:
                device.tags.add(tag_new)

            c.classified = True
            c.accepted = True
            c.save(update_fields=["classified", "accepted"])
            promoted += 1

        self.message_user(request, f"Promoted {promoted} candidates.", level=messages.SUCCESS)


    @admin.action(description="Reject selected candidates")
    def reject_candidates(self, request, queryset):
        updated = queryset.update(classified=True, accepted=False)
        self.message_user(request, f"Rejected {updated} candidates.", level=messages.WARNING)
