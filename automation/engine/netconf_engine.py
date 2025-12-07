import socket
from contextlib import closing


class NetconfEngine:
    """
    Raw NETCONF connectivity engine (TCP 830 reachability).
    """

    def check(self, host, timeout=2.0):
        if not host:
            return False

        try:
            with closing(socket.create_connection((host, 830), timeout=timeout)):
                return True
        except OSError:
            return False
