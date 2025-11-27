from django.contrib import admin
from automation.models import AutomationJob, JobRun, DeviceTelemetry


@admin.register(AutomationJob)
class AutomationJobAdmin(admin.ModelAdmin):
    list_display = ("name", "job_type", "created_at")
    search_fields = ("name", "job_type")


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ("job", "status", "started_at", "finished_at")
    search_fields = ("job__name", "status")
    list_filter = ("status",)


@admin.register(DeviceTelemetry)
class DeviceTelemetryAdmin(admin.ModelAdmin):
    list_display = ("device", "timestamp", "cpu_usage", "memory_usage", "uptime")
    search_fields = ("device__name",)
