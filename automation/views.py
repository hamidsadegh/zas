from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from automation.forms import AutomationScheduleForm
from automation.models import AutomationSchedule, AutomationTaskDefinition
from automation.services.scheduler_sync import sync_schedule
from zas.celery import app as celery_app

SCHEDULE_OVERRIDE_TASKS = {
    "automation.tasks.run_scheduled_reachability",
    "automation.tasks.run_scheduled_config_backup",
}


class TaskListView(LoginRequiredMixin, View):
    template_name = "automation/task_list.html"

    def get(self, request):
        tasks = list(AutomationTaskDefinition.objects.all())
        task_names = [task.task_name for task in tasks]
        schedule_map = {
            schedule.task_name: schedule
            for schedule in AutomationSchedule.objects.filter(task_name__in=task_names).select_related("periodic_task")
        }
        registered_tasks = set(celery_app.tasks.keys())

        rows = []
        scheduled_count = 0
        enabled_count = 0
        manual_count = 0
        missing_count = 0

        for task in tasks:
            schedule = schedule_map.get(task.task_name)
            is_registered = task.task_name in registered_tasks
            if schedule:
                scheduled_count += 1
                if schedule.enabled:
                    enabled_count += 1
            if not task.supports_schedule:
                manual_count += 1
            if not is_registered:
                missing_count += 1

            rows.append(
                {
                    "task": task,
                    "schedule": schedule,
                    "is_registered": is_registered,
                }
            )

        context = {
            "rows": rows,
            "scheduled_count": scheduled_count,
            "enabled_count": enabled_count,
            "manual_count": manual_count,
            "missing_count": missing_count,
            "total_count": len(tasks),
            "schedule_override_tasks": sorted(SCHEDULE_OVERRIDE_TASKS),
        }
        return render(request, self.template_name, context)


class TaskScheduleView(LoginRequiredMixin, View):
    template_name = "automation/task_schedule_form.html"

    def _get_schedule(self, task):
        schedule = (
            AutomationSchedule.objects.filter(task_name=task.task_name, name=task.name)
            .select_related("periodic_task")
            .first()
        )
        if schedule:
            return schedule
        return (
            AutomationSchedule.objects.filter(task_name=task.task_name)
            .select_related("periodic_task")
            .first()
        )

    def get(self, request, task_id):
        task = get_object_or_404(AutomationTaskDefinition, id=task_id)
        if not task.supports_schedule:
            messages.info(request, "This task is triggered by workflows and cannot be scheduled here.")
            return redirect("automation:task_list")
        if (
            task.managed_by != AutomationTaskDefinition.ManagedBy.UI
            and task.task_name not in SCHEDULE_OVERRIDE_TASKS
        ):
            messages.info(request, "This task schedule is managed elsewhere.")
            return redirect("automation:task_list")

        schedule = self._get_schedule(task)
        initial = {}
        if schedule is None:
            initial = {
                "schedule_type": AutomationSchedule.ScheduleType.INTERVAL,
                "interval_seconds": 3600,
                "enabled": True,
            }
        form = AutomationScheduleForm(instance=schedule, initial=initial)

        context = {
            "task": task,
            "schedule": schedule,
            "form": form,
        }
        return render(request, self.template_name, context)

    def post(self, request, task_id):
        task = get_object_or_404(AutomationTaskDefinition, id=task_id)
        if not task.supports_schedule:
            messages.info(request, "This task is triggered by workflows and cannot be scheduled here.")
            return redirect("automation:task_list")
        if (
            task.managed_by != AutomationTaskDefinition.ManagedBy.UI
            and task.task_name not in SCHEDULE_OVERRIDE_TASKS
        ):
            messages.info(request, "This task schedule is managed elsewhere.")
            return redirect("automation:task_list")

        schedule = self._get_schedule(task)
        form = AutomationScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.name = task.name
            schedule.task_name = task.task_name
            schedule.save()
            try:
                sync_schedule(schedule)
            except ValueError as exc:
                form.add_error(None, str(exc))
                return render(
                    request,
                    self.template_name,
                    {"task": task, "schedule": schedule, "form": form},
                )

            messages.success(request, "Schedule updated.")
            return redirect("automation:task_list")

        return render(
            request,
            self.template_name,
            {"task": task, "schedule": schedule, "form": form},
        )
