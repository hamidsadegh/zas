from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class IPAMIndexView(LoginRequiredMixin, TemplateView):
    template_name = "ipam/index.html"
