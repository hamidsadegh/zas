import ipaddress
from typing import Optional

from dcim.models import Site


def normalize_hostname(hostname: str | None, *, site: Optional[Site] = None) -> str:
    value = (hostname or "").strip().lower().rstrip(".")
    if not value:
        return ""

    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass

    if any(token in value for token in (":", "/", " ")):
        return value

    if "." in value:
        return value

    domain = ""
    if site:
        domain = (site.domain or "").strip().lower().rstrip(".")
    if domain:
        return f"{value}.{domain}"
    return value
