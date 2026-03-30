import ipaddress
import socket
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, ValidationError


def validate_url(url: str) -> str | None:
    """Returns error message if URL is invalid, None if valid."""
    try:
        AnyHttpUrl(url)
    except ValidationError:
        return "Invalid URL format"

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "URL scheme must be http or https"

    hostname = parsed.hostname
    if not hostname:
        return "Invalid hostname"

    try:
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local:
            return "Access to private or local network is forbidden"
    except socket.gaierror:
        pass  # If resolution fails here, playwright will natively fail too, but it's not a direct IP SSRF block issue.
    except ValueError:
        pass  # If not a valid IP string format (should not happen with gethostbyname)

    return None
