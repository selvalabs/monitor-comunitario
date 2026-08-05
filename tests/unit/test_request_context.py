from starlette.requests import Request

from monitor_comunitario.services.request_context import get_client_ip


def make_request(client_host: str, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "client": (client_host, 1234),
        "scheme": "http",
        "server": ("testserver", 80),
    })


def test_client_ip_ignores_forwarded_header_without_trusted_proxy() -> None:
    request = make_request("10.0.0.2", "203.0.113.10")

    assert get_client_ip(request, trusted_proxy_ips="") == "10.0.0.2"


def test_client_ip_uses_first_forwarded_address_from_trusted_proxy() -> None:
    request = make_request("10.0.0.2", "203.0.113.10, 10.0.0.3")

    assert get_client_ip(request, trusted_proxy_ips="10.0.0.2") == "203.0.113.10"


def test_client_ip_accepts_trusted_proxy_network() -> None:
    request = make_request("10.0.0.2", "203.0.113.10")

    assert get_client_ip(request, trusted_proxy_ips="10.0.0.0/24") == "203.0.113.10"


def test_client_ip_falls_back_when_forwarded_header_is_empty() -> None:
    request = make_request("10.0.0.2", "  ")

    assert get_client_ip(request, trusted_proxy_ips="10.0.0.2") == "10.0.0.2"