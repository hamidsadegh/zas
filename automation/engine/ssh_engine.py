# automation/engine/ssh_engine.py

from typing import Iterable, Dict, Any
from netmiko import ConnectHandler


class SSHEngine:
    """
    Pure SSH adapter.
    No ORM. No Django. No business logic.
    """

    def __init__(self, conn_params: Dict[str, Any]):
        self.conn_params = conn_params

    def run_command(self, command: str) -> str:
        with ConnectHandler(**self.conn_params) as conn:
            return conn.send_command(command)

    def send_config(self, commands: Iterable[str]) -> str:
        with ConnectHandler(**self.conn_params) as conn:
            return conn.send_config_set(list(commands))
