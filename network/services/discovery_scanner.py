import os
import platform
import socket
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Iterable, List, Dict


@dataclass(frozen=True)
class ScanResult:
    ip: str
    alive: bool
    hostname: str | None = None
    method: str = "unknown"   # icmp / tcp
    port: int | None = None


class DiscoveryScanner:
    def __init__(
        self,
        *,
        connect_timeout: int = 1,
        ping_count: int = 2,
        max_workers: int | None = None,
    ):
        self.connect_timeout = connect_timeout
        self.ping_count = ping_count
        self.ping_timeout = max(1, ping_count * 2)
        self.is_windows = platform.system().lower() == "windows"
        self.max_workers = max_workers or max(8, (os.cpu_count() or 1) * 8)

    # ---------- low-level checks ----------

    def _ping(self, ip: str) -> bool:
        count_flag = "-n" if self.is_windows else "-c"
        cmd = ["ping", count_flag, str(self.ping_count), ip]
        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.ping_timeout,
                check=False,
            )
            return completed.returncode == 0
        except subprocess.TimeoutExpired:
            return False

    def _tcp_check(self, ip: str, port: int) -> bool:
        try:
            with socket.create_connection((ip, port), timeout=self.connect_timeout):
                return True
        except OSError:
            return False

    def _resolve_dns(self, ip: str) -> str | None:
        try:
            return socket.getnameinfo((ip, 0), socket.NI_NAMEREQD)[0].lower()
        except Exception:
            return None

    # ---------- public API ----------

    def scan_icmp(self, ips: Iterable[str]) -> List[ScanResult]:
        results: List[ScanResult] = []
        lock = threading.Lock()

        def worker(ip: str):
            alive = self._ping(ip)
            hostname = self._resolve_dns(ip) if alive else None
            with lock:
                results.append(
                    ScanResult(
                        ip=ip,
                        alive=alive,
                        hostname=hostname,
                        method="icmp",
                    )
                )

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            pool.map(worker, ips)

        return results

    def scan_tcp(self, ips: Iterable[str], port: int) -> List[ScanResult]:
        results: List[ScanResult] = []
        lock = threading.Lock()

        def worker(ip: str):
            alive = self._tcp_check(ip, port)
            hostname = self._resolve_dns(ip) if alive else None
            with lock:
                results.append(
                    ScanResult(
                        ip=ip,
                        alive=alive,
                        hostname=hostname,
                        method="tcp",
                        port=port,
                    )
                )

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            pool.map(worker, ips)

        return results
