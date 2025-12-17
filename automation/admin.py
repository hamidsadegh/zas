from django.contrib import admin
from django import forms

from automation.models import AutomationJob, JobRun, DeviceTelemetry, AutomationSchedule


@admin.register(AutomationJob)
class AutomationJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job_type",
        "status",
        "created_at",
    )

    list_filter = ("job_type", "status")
    ordering = ("-created_at",)


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ("job", "status", "started_at", "finished_at")
    search_fields = ("job__name", "status")
    list_filter = ("status",)


@admin.register(DeviceTelemetry)
class DeviceTelemetryAdmin(admin.ModelAdmin):
    list_display = ("device", "timestamp", "cpu_usage", "memory_usage", "uptime")
    search_fields = ("device__name",)

class AutomationScheduleForm(forms.ModelForm):
    class Meta:
        model = AutomationSchedule
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        schedule_type = cleaned.get("schedule_type")
        interval_seconds = cleaned.get("interval_seconds")

        if schedule_type == AutomationSchedule.ScheduleType.INTERVAL:
            if not interval_seconds or interval_seconds <= 0:
                self.add_error(
                    "interval_seconds",
                    "Interval seconds must be a positive integer for interval schedules.",
                )

        # For crontab we could add extra validation later, but basic strings are OK for now.
        return cleaned


@admin.register(AutomationSchedule)
class AutomationScheduleAdmin(admin.ModelAdmin):
    form = AutomationScheduleForm

    list_display = (
        "name",
        "task_name",
        "schedule_type",
        "enabled",
        "schedule_summary",
        "created_at",
        "updated_at",
    )
    list_filter = ("schedule_type", "enabled", "task_name")
    search_fields = ("name", "task_name")
    readonly_fields = ("created_at", "updated_at", "periodic_task")

    fieldsets = (
        (None, {
            "fields": ("name", "task_name", "enabled"),
        }),
        ("Schedule", {
            "fields": (
                "schedule_type",
                "interval_seconds",
                ("minute", "hour", "day_of_month", "month_of_year", "day_of_week"),
            ),
        }),
        ("Internal", {
            "fields": ("periodic_task", "created_at", "updated_at"),
        }),
    )
