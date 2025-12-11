# automation/ssh_consumer.py

import asyncssh
import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps


Device = apps.get_model("dcim", "Device")


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
            self.device = await asyncio.to_thread(Device.objects.get, id=device_id)
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
            # DEBUG (safe) – log what we’re going to try (NO password)
            # You can use logging instead of print in your project
            print(
                f"[SSHConsumer] Connecting to {self.device.management_ip} "
                f"as {self.user.username}"
            )

            self.conn = await asyncssh.connect(
                self.device.management_ip,
                username=self.user.username,
                password=self.tacacs_password,
                known_hosts=None,
            )

            self.channel, _ = await self.conn.create_session(
                lambda: asyncssh.SSHClientSession(self._on_data),
                term_type="xterm",
            )

        except Exception as exc:
            # Log full error server-side
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("SSH connection error")

            # Send generic error to client
            await self.send(json.dumps({"error": f"SSH connection failed: {exc}"}))
            await self.close()

    def _on_data(self, data: str):
        # Called by asyncssh session when remote sends output
        asyncio.create_task(self.send(data))

    async def receive(self, text_data=None, bytes_data=None):
        # Keystrokes from browser terminal
        if hasattr(self, "channel") and self.channel:
            if text_data:
                self.channel.write(text_data)

    async def disconnect(self, code):
        if hasattr(self, "conn") and self.conn:
            self.conn.close()
