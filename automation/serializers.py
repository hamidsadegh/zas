from rest_framework import serializers
from .models import AutomationJob, JobRun, DeviceTelemetry


class AutomationJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationJob
        fields = '__all__'


class JobRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRun
        fields = '__all__'


class DeviceTelemetrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceTelemetry
        fields = '__all__'
