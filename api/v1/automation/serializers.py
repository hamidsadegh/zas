from celery import current_app
from rest_framework import serializers

from automation.models import (
    AutomationJob,
    AutomationSchedule,
    DeviceTelemetry,
    JobRun,
)


class AutomationScheduleSerializer(serializers.ModelSerializer):
    schedule_summary = serializers.ReadOnlyField()

    class Meta:
        model = AutomationSchedule
        fields = [
            "id",
            "name",
            "task_name",
            "enabled",
            "schedule_type",
            "interval_seconds",
            "minute",
            "hour",
            "day_of_week",
            "day_of_month",
            "month_of_year",
            "schedule_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")

    def validate_task_name(self, value: str) -> str:
        tasks = current_app.tasks.keys()
        if value not in tasks:
            raise serializers.ValidationError(
                f"Task '{value}' is not registered in Celery. Available example: "
                f"{next(iter(tasks))!r}"
            )
        return value

    def validate(self, attrs):
        schedule_type = attrs.get(
            "schedule_type",
            getattr(
                self.instance,
                "schedule_type",
                AutomationSchedule.ScheduleType.INTERVAL,
            ),
        )
        interval_seconds = attrs.get(
            "interval_seconds",
            getattr(self.instance, "interval_seconds", None),
        )

        if schedule_type == AutomationSchedule.ScheduleType.INTERVAL:
            if not interval_seconds or interval_seconds <= 0:
                raise serializers.ValidationError(
                    {
                        "interval_seconds": (
                            "Must be a positive integer for interval schedules."
                        )
                    }
                )

        return attrs


class AutomationJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationJob
        fields = "__all__"


class JobRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRun
        fields = "__all__"


class DeviceTelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceTelemetry
        fields = "__all__"
