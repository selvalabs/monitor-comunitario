from ipaddress import ip_address, ip_network

from starlette.requests import Request


def get_client_ip(request: Request, *, trusted_proxy_ips: str) -> str:
    """Return the client IP without trusting spoofable forwarding headers."""
    direct_ip = request.client.host if request.client else "unknown"
    if not trusted_proxy_ips or direct_ip == "unknown":
        return direct_ip

    try:
        direct_address = ip_address(direct_ip)
    except ValueError:
        return direct_ip

    trusted_networks = []
    for value in trusted_proxy_ips.split(","):
        value = value.strip()
        if not value:
            continue
        try:
            trusted_networks.append(ip_network(value, strict=False))
        except ValueError:
            continue

    if not any(direct_address in network for network in trusted_networks):
        return direct_ip

    forwarded_for = request.headers.get("x-forwarded-for", "")
    first_forwarded_ip = forwarded_for.split(",", 1)[0].strip()
    return first_forwarded_ip or direct_ip