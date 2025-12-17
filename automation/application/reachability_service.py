from django.utils import timezone

from automation.application.job_service import JobService
from automation.application.job_dispatcher import JobDispatcher
from accounts.services.settings_service import update_reachability_last_run


class ReachabilityService:
    @staticmethod
    def start_reachability_job(*, devices, created_by, system_settings):
        checks = {
            "ping": system_settings.reachability_ping_enabled,
            "snmp": system_settings.reachability_snmp_enabled,
            "ssh": system_settings.reachability_ssh_enabled,
            "netconf": system_settings.reachability_netconf_enabled,
        }

        job, run = JobService.create_reachability_job(
            devices=devices,
            created_by=None,
            params={"checks": checks},
        )

        update_reachability_last_run(system_settings, timezone.now())

        JobDispatcher.dispatch_reachability(run)

        return job
