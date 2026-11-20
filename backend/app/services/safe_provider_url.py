"""Never forward OAuth credentials or file bytes to arbitrary resumable-upload hosts."""

from urllib.parse import urlsplit


def google_upload_url(url):
    if not isinstance(url, str) or any(ord(c) < 32 for c in url):
        raise ValueError("Invalid upload destination")
    parts = urlsplit(url)
    host = parts.hostname or ""
    if (
        parts.scheme != "https"
        or not (host == "googleapis.com" or host.endswith(".googleapis.com"))
        or parts.username
        or parts.password
        or parts.port not in {None, 443}
        or parts.fragment
    ):
        raise ValueError("Invalid upload destination")
    return url
