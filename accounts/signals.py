from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver

@receiver(user_logged_out)
def clear_tacacs_password(sender, request, user, **kwargs):
    if request and "tacacs_password" in request.session:
        del request.session["tacacs_password"]
