import contextlib

from netmiko import ConnectHandler
from netmiko.ssh_autodetect import SSHDetect

from automation.application.connection_service import ConnectionService


class NetmikoAdapter(contextlib.AbstractContextManager):
    """Thin wrapper around Netmiko ConnectHandler with site credentials."""

    def __init__(self, device):
        self.device = device
        self.connection = None

    def __enter__(self):
        params = ConnectionService.build_ssh_params(self.device)
        if params.get("device_type") == "autodetect":
            guesser = SSHDetect(**params)
            best_match = guesser.autodetect()
            params["device_type"] = best_match
        self.connection = ConnectHandler(**params)
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                pass

    def run_command(self, command: str) -> dict:
        """Return {'raw': str, 'parsed': list|dict|None, 'error': str|None}."""
        result = {"raw": "", "parsed": None, "error": None}
        try:
            output = self.connection.send_command(command, use_textfsm=True)
            if isinstance(output, str):
                result["raw"] = output
            else:
                result["parsed"] = output
                # Re-run without textfsm to preserve raw payload
                result["raw"] = self.connection.send_command(
                    command, use_textfsm=False
                )
        except Exception as exc:
            result["error"] = str(exc)
        return result
