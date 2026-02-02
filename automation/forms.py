from django import forms

from automation.models import AutomationSchedule


class AutomationScheduleForm(forms.ModelForm):
    class Meta:
        model = AutomationSchedule
        fields = [
            "enabled",
            "schedule_type",
            "interval_seconds",
            "minute",
            "hour",
            "day_of_week",
            "day_of_month",
            "month_of_year",
        ]

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

        return cleaned
