from rest_framework import serializers

from topology.models import TopologyNeighbor


class TopologyNeighborSerializer(serializers.ModelSerializer):
    local_interface = serializers.SerializerMethodField()
    neighbor_device_id = serializers.SerializerMethodField()
    neighbor_device_name = serializers.SerializerMethodField()

    class Meta:
        model = TopologyNeighbor
        fields = [
            "local_interface",
            "protocol",
            "neighbor_name",
            "neighbor_device_id",
            "neighbor_device_name",
            "neighbor_interface",
            "platform",
            "capabilities",
            "last_seen",
        ]

    def get_local_interface(self, obj):
        return obj.local_interface.name if obj.local_interface else ""

    def get_neighbor_device_id(self, obj):
        return str(obj.neighbor_device_id) if obj.neighbor_device_id else None

    def get_neighbor_device_name(self, obj):
        return obj.neighbor_device.name if obj.neighbor_device else None
