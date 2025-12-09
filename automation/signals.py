# automation/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from automation.models import AutomationSchedule
from automation.services.scheduler_sync import sync_schedule, remove_schedule


@receiver(post_save, sender=AutomationSchedule)
def automation_schedule_saved(sender, instance: AutomationSchedule, **kwargs):
    sync_schedule(instance)


@receiver(post_delete, sender=AutomationSchedule)
def automation_schedule_deleted(sender, instance: AutomationSchedule, **kwargs):
    remove_schedule(instance)
