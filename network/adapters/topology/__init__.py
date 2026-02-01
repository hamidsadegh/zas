import re


def _finalize_neighbor(current, neighbors, protocol):
    if not current:
        return
    neighbor_name = current.get("neighbor_name", "").strip()
    local_interface = current.get("local_interface", "").strip()
    if not neighbor_name or not local_interface:
        return
    neighbors.append(
        {
            "local_interface": local_interface,
            "neighbor_name": neighbor_name,
            "neighbor_interface": current.get("neighbor_interface", "").strip(),
            "platform": current.get("platform", "").strip(),
            "capabilities": current.get("capabilities", "").strip(),
            "protocol": protocol,
        }
    )


def _parse_cdp_summary(raw_output: str) -> list[dict]:
    neighbors = []
    pending_device = ""
    in_table = False

    for line in (raw_output or "").splitlines():
        if "Device ID" in line and "Local Intrfce" in line:
            in_table = True
            continue
        if not in_table:
            continue
        if not line.strip() or line.startswith("Total cdp entries"):
            continue

        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) == 1:
            pending_device = cols[0].strip()
            continue

        if len(cols) >= 6:
            device_id, local, hold, caps, platform, port_id = cols[:6]
        elif len(cols) == 5 and pending_device:
            device_id = pending_device
            local, hold, caps, platform, port_id = cols
        else:
            continue

        pending_device = ""
        neighbors.append(
            {
                "local_interface": local.strip(),
                "neighbor_name": device_id.strip(),
                "neighbor_interface": port_id.strip(),
                "platform": platform.strip(),
                "capabilities": caps.strip(),
                "protocol": "cdp",
            }
        )

    return neighbors


def parse_cdp_neighbors(raw_output: str) -> list[dict]:
    if not raw_output:
        return []
    if "Device ID" in raw_output and "Local Intrfce" in raw_output:
        summary = _parse_cdp_summary(raw_output)
        if summary:
            return summary

    neighbors = []
    current = {}

    for line in (raw_output or "").splitlines():
        line = line.strip()
        if not line or line.startswith("Capability Codes") or line.startswith("Total cdp entries"):
            continue

        if line.lower().startswith("device id"):
            _finalize_neighbor(current, neighbors, "cdp")
            current = {}
            current["neighbor_name"] = line.split("Device ID:", 1)[-1].strip()
            continue

        if line.startswith("Interface:"):
            match = re.search(r"Interface:\s*([^,]+),\s*Port ID.*?:\s*(.+)$", line)
            if match:
                current["local_interface"] = match.group(1).strip()
                current["neighbor_interface"] = match.group(2).strip()
                continue

        if line.startswith("Port ID"):
            current["neighbor_interface"] = line.split(":", 1)[-1].strip()
            continue

        if line.startswith("Platform:"):
            platform_part = line.split("Platform:", 1)[-1].strip()
            if "Capabilities:" in platform_part:
                platform, capabilities = platform_part.split("Capabilities:", 1)
                current["platform"] = platform.rstrip(",").strip()
                current["capabilities"] = capabilities.strip()
            else:
                current["platform"] = platform_part.strip()
            continue

        if line.startswith("Capabilities:"):
            current["capabilities"] = line.split("Capabilities:", 1)[-1].strip()
            continue

        if line.startswith("Local Interface:"):
            current["local_interface"] = line.split(":", 1)[-1].strip()
            continue

    _finalize_neighbor(current, neighbors, "cdp")
    return neighbors


def parse_lldp_neighbors(raw_output: str) -> list[dict]:
    if not raw_output:
        return []
    if "Device ID" in raw_output and "Local Intf" in raw_output:
        neighbors = []
        for line in (raw_output or "").splitlines():
            if not line.strip() or line.startswith("Total entries displayed"):
                continue
            if line.strip().startswith("Device ID") or line.strip().startswith("Capability codes"):
                continue
            cols = re.split(r"\s{2,}", line.strip())
            if len(cols) < 5:
                continue
            device_id, local_intf, hold, caps, port_id = cols[:5]
            neighbors.append(
                {
                    "local_interface": local_intf.strip(),
                    "neighbor_name": device_id.strip(),
                    "neighbor_interface": port_id.strip(),
                    "platform": "",
                    "capabilities": caps.strip(),
                    "protocol": "lldp",
                }
            )
        if neighbors:
            return neighbors

    neighbors = []
    current = {}

    for line in (raw_output or "").splitlines():
        line = line.strip()
        if not line or line.startswith("Total entries displayed"):
            continue

        if line.startswith("Chassis id:"):
            if current.get("local_interface") or current.get("neighbor_name"):
                _finalize_neighbor(current, neighbors, "lldp")
                current = {}
            if not current.get("neighbor_name"):
                current["neighbor_name"] = line.split(":", 1)[-1].strip()
            continue

        if line.startswith("Local Intf:") or line.startswith("Local Interface:") or line.startswith("Local Port id:"):
            _finalize_neighbor(current, neighbors, "lldp")
            current = {}
            current["local_interface"] = line.split(":", 1)[-1].strip()
            continue

        if line.startswith("Port id:") or line.startswith("Port ID:"):
            current["neighbor_interface"] = line.split(":", 1)[-1].strip()
            continue

        if line.startswith("System Name:"):
            current["neighbor_name"] = line.split(":", 1)[-1].strip()
            continue

        if line.startswith("Chassis id:") and not current.get("neighbor_name"):
            current["neighbor_name"] = line.split(":", 1)[-1].strip()
            continue

        if line.startswith("System Capabilities:"):
            current["capabilities"] = line.split(":", 1)[-1].strip()
            continue

        if line.startswith("Model Number:"):
            model = line.split(":", 1)[-1].strip()
            if model and model.lower() != "not advertised":
                current["platform"] = model
            continue

        if line.startswith("System Description:"):
            desc = line.split(":", 1)[-1].strip()
            match = re.search(r"(?:[Mm]odel|PID)\s*[:=]\s*([A-Za-z0-9-]+)", desc)
            if match:
                current["platform"] = match.group(1).strip()
            continue

    _finalize_neighbor(current, neighbors, "lldp")
    return neighbors
