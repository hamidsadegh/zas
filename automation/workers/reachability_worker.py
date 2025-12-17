from automation.engine.reachability_engine import ReachabilityEngine


def execute_reachability(run, checks: dict) -> dict:
    devices = run.devices.all()
    engine = ReachabilityEngine()

    return engine.measure(
        devices=devices,
        check_ping=checks.get("ping", True),
        check_snmp=checks.get("snmp", True),
        check_ssh=checks.get("ssh", False),
        check_netconf=checks.get("netconf", False),
    )
