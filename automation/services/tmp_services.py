from ssh_service import SSHService
from snmp_service import SNMPService
from dcim.models import Device

class BackupService:
    """Handles configuration backup via SSH."""
    def run_backup(self, device: Device) -> str:
        ssh = SSHService(device)
        config = ssh.get_running_config()
        return config


class CommandService:
    """Handles command execution on devices."""
    def run_command(self, device: Device, command: str) -> str:
        ssh = SSHService(device)
        output = ssh.send_command(command)
        return output


class TelemetryService:
    """Collects telemetry using SNMP or SSH."""
    def collect(self, device: Device) -> dict:
        snmp = SNMPService(device)
        return snmp.get_basic_telemetry()
