# automation/ssh_consumer.py

import asyncssh
import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps


Device = apps.get_model("dcim", "Device")


class SSHSession(asyncssh.SSHClientSession):
    def __init__(self, on_data):
        self._on_data = on_data

    def data_received(self, data, datatype):
        if self._on_data:
            self._on_data(data)


class SSHConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1) Only authenticated users
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        self.user = user

        # 2) Load session & TACACS password
        session = self.scope.get("session")
        self.tacacs_password = None
        if session is not None:
            self.tacacs_password = session.get("tacacs_password")

        if not self.tacacs_password:
            # Tell frontend clearly what’s wrong
            await self.accept()
            await self.send(json.dumps({
                "error": "No TACACS credentials in session. Please re-login."
            }))
            await self.close()
            return

        # 3) Get device
        device_id = self.scope["url_route"]["kwargs"]["device_id"]
        try:
            def _get_device_with_flags():
                device = (
                    Device.objects.select_related("device_type")
                    .prefetch_related("tags")
                    .get(id=device_id)
                )
                is_aci = any(
                    tag.name.lower() == "aci_fabric"
                    for tag in device.tags.all()
                )
                platform = device.device_type.platform if device.device_type else None
                return device, is_aci, platform

            self.device, self.is_aci_fabric, self.device_platform = await asyncio.to_thread(
                _get_device_with_flags
            )
        except Device.DoesNotExist:
            await self.accept()
            await self.send(json.dumps({"error": "Device not found."}))
            await self.close()
            return

        # 4) Accept WebSocket and start SSH
        await self.accept()
        await self.start_ssh()

    async def start_ssh(self):
        try:
            username = self.user.username
            if self.is_aci_fabric:
                prefix = "apic#ISE\\\\"
                if not username.startswith(prefix):
                    username = f"{prefix}{username}"
            self.ssh_username = username

            # DEBUG (safe) – log what we’re going to try (NO password)
            # You can use logging instead of print in your project
            print(
                f"[SSHConsumer] Connecting to {self.device.management_ip} "
                f"as {self.ssh_username}"
            )

            self.conn = await asyncssh.connect(
                self.device.management_ip,
                username=self.ssh_username,
                password=self.tacacs_password,
                known_hosts=None,
            )

            self.channel, _ = await self.conn.create_session(
                lambda: SSHSession(self._on_data),
                term_type="xterm",
            )
            await self._disable_paging()

        except Exception as exc:
            # Log full error server-side
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("SSH connection error")

            # Send generic error to client
            await self.send(json.dumps({"error": f"SSH connection failed: {exc}"}))
            await self.close()

    async def _disable_paging(self):
        if not hasattr(self, "channel") or not self.channel:
            return
        platform = getattr(self, "device_platform", None)
        try:
            await asyncio.sleep(0.3)
        except Exception:
            pass
        try:
            self.channel.write("\n")
        except Exception:
            return
        # IOS/NX-OS paging off (fallback to generic if platform unknown)
        if platform in ("ios", "iosxe", "nxos") or platform is None:
            try:
                self.channel.write("terminal length 0\n")
                self.channel.write("terminal width 200\n")
            except Exception:
                pass

    def _on_data(self, data: str):
        # Called by asyncssh session when remote sends output
        asyncio.create_task(self.send(data))

    async def receive(self, text_data=None, bytes_data=None):
        # Keystrokes from browser terminal
        if hasattr(self, "channel") and self.channel:
            if text_data:
                payload = None
                if text_data.lstrip().startswith("{"):
                    try:
                        payload = json.loads(text_data)
                    except Exception:
                        payload = None
                if isinstance(payload, dict) and payload.get("type") == "resize":
                    cols = int(payload.get("cols") or 0)
                    rows = int(payload.get("rows") or 0)
                    if cols > 0 and rows > 0:
                        try:
                            self.channel.change_terminal_size(cols, rows)
                        except Exception:
                            pass
                    return
                self.channel.write(text_data)

    async def disconnect(self, code):
        if hasattr(self, "conn") and self.conn:
            self.conn.close()
