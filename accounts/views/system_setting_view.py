from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from accounts.services.settings_service import get_system_settings
from automation.services.scheduler_sync import sync_reachability_from_system_settings
from automation.models.schedule import AutomationSchedule
from dcim.models.device_config import DeviceConfiguration
from accounts.forms.settings_form import (
    AllowLocalSuperusersForm,
    ReachabilitySettingsForm,
    TacacsSettingsForm,
)


class SystemSettingsView(LoginRequiredMixin, View):
    template_name = "settings/system_settings.html"

    def get_settings(self):
        return get_system_settings()

    def get_context(self, settings_obj, **forms):
        backup_schedule = AutomationSchedule.objects.filter(name="Nightly Configuration Backup").select_related(
            "periodic_task"
        ).first()
        latest_backup = (
            DeviceConfiguration.objects.filter(success=True)
            .order_by("-collected_at")
            .first()
        )
        return {
            "tacacs_form": forms.get("tacacs_form") or TacacsSettingsForm(instance=settings_obj),
            "reachability_form": forms.get("reachability_form")
            or ReachabilitySettingsForm(instance=settings_obj),
            "superusers_form": forms.get("superusers_form") or AllowLocalSuperusersForm(instance=settings_obj),
            "settings_obj": settings_obj,
            "backup_schedule": backup_schedule,
            "latest_backup": latest_backup,
        }

    def get(self, request):
        settings_obj = self.get_settings()
        return render(request, self.template_name, self.get_context(settings_obj))

    def post(self, request):
        settings_obj = self.get_settings()
        section = request.POST.get("section")

        tacacs_form = TacacsSettingsForm(instance=settings_obj)
        reachability_form = ReachabilitySettingsForm(instance=settings_obj)
        superusers_form = AllowLocalSuperusersForm(instance=settings_obj)

        if section == "tacacs":
            tacacs_form = TacacsSettingsForm(request.POST, instance=settings_obj)
            if tacacs_form.is_valid():
                tacacs_form.save()
                messages.success(request, "TACACS+ settings saved.")
                return redirect("system_settings")
        elif section == "reachability":
            reachability_form = ReachabilitySettingsForm(request.POST, instance=settings_obj)
            if reachability_form.is_valid():
                reachability_form.save()
                sync_reachability_from_system_settings(settings_obj)
                messages.success(request, "Reachability settings saved.")
                return redirect("system_settings")
        elif section == "superusers":
            superusers_form = AllowLocalSuperusersForm(request.POST, instance=settings_obj)
            if superusers_form.is_valid():
                superusers_form.save()
                messages.success(request, "Superusers settings saved.")
                return redirect("system_settings")
        else:
            messages.error(request, "Unknown settings section.")
            return redirect("system_settings")

        messages.error(request, "Please fix the highlighted errors.")
        return render(
            request,
            self.template_name,
            self.get_context(
                settings_obj,
                tacacs_form=tacacs_form,
                reachability_form=reachability_form,
                superusers_form=superusers_form,
            ),
        )
