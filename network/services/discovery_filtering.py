def _split_terms(value: str) -> list[str]:
    return [
        term.strip().lower()
        for term in value.split(",")
        if term.strip()
    ]


def hostname_matches_filter(hostname: str, flt) -> bool:
    """
    Returns True if hostname satisfies the filter rule.
    """
    hostname = (hostname or "").lower()

    # positive terms: ANY may be present
    if flt.hostname_contains:
        required = _split_terms(flt.hostname_contains)
        if any(term in hostname for term in required):
            return True

    # negative terms: NONE may be present
    if flt.hostname_not_contains:
        forbidden = _split_terms(flt.hostname_not_contains)
        if any(term in hostname for term in forbidden):
            return False

    return True


def hostname_passes_filters(hostname: str, filters) -> bool:
    """
    Returns True if hostname passes any enabled filter.
    If no filters are provided, allow all hostnames.
    """
    if not filters:
        return True
    if not (hostname or "").strip():
        return False
    return any(hostname_matches_filter(hostname, flt) for flt in filters)
