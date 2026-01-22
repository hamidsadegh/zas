# automation/ssh_consumer.py

import asyncio
import json
import logging
import threading

import paramiko
from channels.generic.websocket import AsyncWebsocketConsumer
from django.apps import apps


Device = apps.get_model("dcim", "Device")
logger = logging.getLogger(__name__)


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

        self.pending_resize = None
        self._resize_event = asyncio.Event()
        self._closing = False
        self.loop = asyncio.get_running_loop()
        self.transport = None
        self.channel = None

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
        asyncio.create_task(self.start_ssh())

    async def start_ssh(self):
        try:
            username = self.user.username
            if self.is_aci_fabric:
                prefix = "apic#ISE\\\\"
                if not username.startswith(prefix):
                    username = f"{prefix}{username}"
            self.ssh_username = username

            # Wait briefly for an initial resize from the frontend.
            cols, rows = await self._get_initial_pty_size()
            logger.info("[SSHConsumer] Initial PTY size %sx%s", cols, rows)

            await asyncio.to_thread(self._open_channel, cols, rows)

            reader = threading.Thread(target=self._reader_loop, daemon=True)
            reader.start()

            await self._disable_paging()

        except Exception as exc:
            logger.exception("SSH connection error")
            await self.send(json.dumps({"error": f"SSH connection failed: {exc}"}))
            await self.close()

    async def _get_initial_pty_size(self):
        if not self._resize_event.is_set():
            try:
                await asyncio.wait_for(self._resize_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.info("[SSHConsumer] No initial resize event received; using default")
                pass
        return self.pending_resize or (80, 24)

    def _open_channel(self, cols, rows):
        host = str(self.device.management_ip)
        self.transport = paramiko.Transport((host, 22))
        self.transport.connect(
            username=self.ssh_username,
            password=self.tacacs_password,
        )

        self.channel = self.transport.open_session()
        logger.debug("Requesting PTY size %sx%s", cols, rows)
        self.channel.get_pty(term="xterm", width=cols, height=rows)
        self.channel.invoke_shell()
        self.channel.settimeout(1.0)

        if self.pending_resize:
            try:
                self.channel.resize_pty(
                    width=self.pending_resize[0],
                    height=self.pending_resize[1],
                )
            except Exception:
                pass

    def _reader_loop(self):
        while not self._closing and self.channel and not self.channel.closed:
            try:
                data = self.channel.recv(4096)
            except Exception:
                continue
            if not data:
                break
            text = data.decode(errors="ignore")
            asyncio.run_coroutine_threadsafe(self.send(text), self.loop)

    async def _disable_paging(self):
        if not self.channel:
            return
        await asyncio.sleep(0.3)
        await asyncio.to_thread(self._channel_send, "\n")

    def _channel_send(self, text):
        if not self.channel or self.channel.closed:
            return
        if isinstance(text, str):
            data = text.encode()
        else:
            data = text
        self.channel.send(data)

    async def receive(self, text_data=None, bytes_data=None):
        # Keystrokes from browser terminal
        if text_data is None and bytes_data:
            try:
                text_data = bytes_data.decode(errors="ignore")
            except Exception:
                text_data = None
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
                    self.pending_resize = (cols, rows)
                    self._resize_event.set()
                    logger.debug(
                        "[SSHConsumer] Resize received %sx%s (channel=%s)",
                        cols,
                        rows,
                        bool(self.channel),
                    )
                    if self.channel:
                        await asyncio.to_thread(
                            self.channel.resize_pty,
                            width=cols,
                            height=rows,
                        )
                return

            if self.channel:
                await asyncio.to_thread(self._channel_send, text_data)

    async def disconnect(self, code):
        self._closing = True
        if self.channel:
            await asyncio.to_thread(self.channel.close)
        if self.transport:
            await asyncio.to_thread(self.transport.close)
