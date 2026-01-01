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

    # positive terms: ALL must be present
    if flt.hostname_contains:
        required = _split_terms(flt.hostname_contains)
        if not all(term in hostname for term in required):
            return False

    # negative terms: NONE may be present
    if flt.hostname_not_contains:
        forbidden = _split_terms(flt.hostname_not_contains)
        if any(term in hostname for term in forbidden):
            return False

    return True
