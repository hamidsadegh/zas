from netmiko import ConnectHandler
from ..models import Device

class SSHService:
    def __init__(self, device: Device):
        self.device = device
        self.conn_params = {
            'device_type': self._netmiko_platform(),
            'host': device.management_ip or device.ip_address,
            'username': device.username,
            'password': device.password,
            'port': device.ssh_port,
        }

    def _netmiko_platform(self):
        mapping = {
            'catalyst': 'cisco_ios',
            'nexus': 'cisco_nxos',
            'router': 'cisco_ios',
            'firewall': 'cisco_asa',
        }
        return mapping.get(self.device.device_type, 'autodetect')

    def run_command(self, command, timeout=30):
        with ConnectHandler(**self.conn_params) as conn:
            output = conn.send_command(command, timeout=timeout)
            return output

    def send_config(self, commands):
        with ConnectHandler(**self.conn_params) as conn:
            output = conn.send_config_set(commands)
            return output

