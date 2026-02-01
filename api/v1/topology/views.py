from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from topology.models import TopologyNeighbor

from .serializers import TopologyNeighborSerializer


class DeviceTopologyNeighborsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TopologyNeighborSerializer

    def get_queryset(self):
        device_id = self.kwargs["device_id"]
        return (
            TopologyNeighbor.objects.filter(device_id=device_id)
            .select_related("local_interface", "neighbor_device")
            .order_by("local_interface__name", "neighbor_name", "-last_seen")
        )
