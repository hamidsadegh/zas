from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from accounts.models.system_settings import SystemSettings
from accounts.services.settings_service import get_system_settings
from dcim.forms.device_forms import OtherSettingsForm, ReachabilitySettingsForm, TacacsSettingsForm


class SystemSettingsView(LoginRequiredMixin, View):
    template_name = "settings/system_settings.html"

    def get_settings(self):
        return get_system_settings()

    def get_context(self, settings_obj, **forms):
        return {
            "tacacs_form": forms.get("tacacs_form") or TacacsSettingsForm(instance=settings_obj),
            "reachability_form": forms.get("reachability_form")
            or ReachabilitySettingsForm(instance=settings_obj),
            "other_form": forms.get("other_form") or OtherSettingsForm(instance=settings_obj),
            "settings_obj": settings_obj,
        }

    def get(self, request):
        settings_obj = self.get_settings()
        return render(request, self.template_name, self.get_context(settings_obj))

    def post(self, request):
        settings_obj = self.get_settings()
        section = request.POST.get("section")

        tacacs_form = TacacsSettingsForm(instance=settings_obj)
        reachability_form = ReachabilitySettingsForm(instance=settings_obj)
        other_form = OtherSettingsForm(instance=settings_obj)

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
                messages.success(request, "Reachability settings saved.")
                return redirect("system_settings")
        elif section == "other":
            other_form = OtherSettingsForm(request.POST, instance=settings_obj)
            if other_form.is_valid():
                other_form.save()
                messages.success(request, "Other settings saved.")
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
                other_form=other_form,
            ),
        )

