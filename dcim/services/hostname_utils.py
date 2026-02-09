import ipaddress
from typing import Optional

from dcim.models import Site


def normalize_hostname(hostname: str | None, *, site: Optional[Site] = None) -> str:
    value = (hostname or "").strip().lower().rstrip(".")
    if not value:
        return ""

    if "," in value:
        parts = [part.strip().lower().rstrip(".") for part in value.split(",") if part.strip()]
        if not parts:
            return ""
        value = parts[0]

    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass

    if any(token in value for token in (":", "/", " ")):
        return value

    domain = ""
    if site:
        domain = (site.domain or "").strip().lower().rstrip(".")
    if domain:
        if value.endswith(domain):
            return value

        base_domain = ""
        if "." in domain:
            base_domain = domain.split(".", 1)[1]

        if base_domain:
            value_labels = value.split(".")
            base_labels = base_domain.split(".")
            if (
                len(value_labels) == len(base_labels) + 1
                and value.endswith(base_domain)
            ):
                host = value[: -(len(base_domain) + 1)]
                return f"{host}.{domain}"

        if "." not in value:
            return f"{value}.{domain}"

    return value
