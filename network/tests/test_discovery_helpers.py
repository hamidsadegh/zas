from types import SimpleNamespace
from unittest.mock import patch

import subprocess

import pytest

from network.services.discovery_filtering import hostname_matches_filter, hostname_passes_filters
from network.services.discovery_scanner import DiscoveryScanner


def test_hostname_matches_filter_forbidden_term_overrides_positive_match():
    flt = SimpleNamespace(hostname_contains="edge", hostname_not_contains="lab")

    assert hostname_matches_filter("edge-lab-sw01", flt) is False


def test_hostname_passes_filters_rejects_blank_hostname_when_filters_present():
    flt = SimpleNamespace(hostname_contains="edge", hostname_not_contains="")

    assert hostname_passes_filters("   ", [flt]) is False


def test_hostname_passes_filters_accepts_when_any_filter_matches():
    filters = [
        SimpleNamespace(hostname_contains="core", hostname_not_contains=""),
        SimpleNamespace(hostname_contains="edge", hostname_not_contains="lab"),
    ]

    assert hostname_passes_filters("edge-sw01", filters) is True


def test_ping_returns_false_on_timeout():
    scanner = DiscoveryScanner(max_workers=1)

    with patch(
        "network.services.discovery_scanner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ping", timeout=2),
    ):
        assert scanner._ping("192.0.2.50") is False


def test_scan_icmp_only_resolves_dns_for_alive_hosts():
    scanner = DiscoveryScanner(max_workers=1)

    with patch.object(scanner, "_ping", side_effect=[True, False]):
        with patch.object(scanner, "_resolve_dns", return_value="edge-sw01.example.com") as mock_dns:
            results = scanner.scan_icmp(["192.0.2.51", "192.0.2.52"])

    assert [result.alive for result in results] == [True, False]
    assert results[0].hostname == "edge-sw01.example.com"
    assert results[1].hostname is None
    mock_dns.assert_called_once_with("192.0.2.51")


def test_scan_tcp_records_method_port_and_hostname():
    scanner = DiscoveryScanner(max_workers=1)

    with patch.object(scanner, "_tcp_check", side_effect=[True, False]):
        with patch.object(scanner, "_resolve_dns", return_value="dist-sw01.example.com"):
            results = scanner.scan_tcp(["192.0.2.53", "192.0.2.54"], port=22)

    assert results[0].method == "tcp"
    assert results[0].port == 22
    assert results[0].hostname == "dist-sw01.example.com"
    assert results[1].alive is False


def test_tcp_check_returns_false_on_socket_error():
    scanner = DiscoveryScanner(max_workers=1)

    with patch("network.services.discovery_scanner.socket.create_connection", side_effect=OSError()):
        assert scanner._tcp_check("192.0.2.55", 22) is False
