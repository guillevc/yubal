"""Cookie conversion utilities for ytmusicapi authentication.

Converts Netscape cookie format (used by yt-dlp) to ytmusicapi auth format.
"""

import hashlib
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Origin for SAPISIDHASH calculation
YTM_ORIGIN = "https://music.youtube.com"


def parse_netscape_cookies(cookies_path: Path) -> dict[str, str]:
    """Parse Netscape format cookies.txt into a dict.

    Args:
        cookies_path: Path to cookies.txt file.

    Returns:
        Dict mapping cookie name to value.
    """
    cookies: dict[str, str] = {}

    try:
        content = cookies_path.read_text()
    except OSError as e:
        logger.warning("Failed to read cookies file: %s", e)
        return cookies

    for line in content.splitlines():
        line = line.strip()
        # Skip comments and empty lines
        if not line or line.startswith("#"):
            continue

        # Netscape format: domain, flag, path, secure, expiry, name, value
        parts = line.split("\t")
        if len(parts) >= 7:
            name = parts[5]
            value = parts[6]
            cookies[name] = value

    return cookies


def build_cookie_header(cookies: dict[str, str]) -> str:
    """Build Cookie header string from cookie dict.

    Args:
        cookies: Dict mapping cookie name to value.

    Returns:
        Cookie header string (name=value; name2=value2; ...).
    """
    return "; ".join(f"{name}={value}" for name, value in cookies.items())


def get_sapisid(cookies: dict[str, str]) -> str | None:
    """Extract SAPISID value from cookies.

    Tries __Secure-3PAPISID first (newer), then SAPISID (older).

    Args:
        cookies: Dict mapping cookie name to value.

    Returns:
        SAPISID value or None if not found.
    """
    return cookies.get("__Secure-3PAPISID") or cookies.get("SAPISID")


def generate_sapisidhash(sapisid: str, origin: str = YTM_ORIGIN) -> str:
    """Generate SAPISIDHASH authorization value.

    Algorithm reverse-engineered from YouTube's auth system.
    See: https://stackoverflow.com/a/32065323/5726546

    Args:
        sapisid: SAPISID cookie value.
        origin: Origin URL for the hash.

    Returns:
        SAPISIDHASH authorization header value.
    """
    timestamp = str(int(time.time()))
    hash_input = f"{timestamp} {sapisid} {origin}"
    sha1_hash = hashlib.sha1(hash_input.encode("utf-8")).hexdigest()
    return f"SAPISIDHASH {timestamp}_{sha1_hash}"


def cookies_to_ytmusic_auth(cookies_path: Path) -> dict[str, str] | None:
    """Convert cookies.txt to ytmusicapi authentication headers.

    Args:
        cookies_path: Path to Netscape format cookies.txt file.

    Returns:
        Dict with auth headers for ytmusicapi, or None if auth not possible.
        The dict can be passed directly to YTMusic() constructor.
    """
    if not cookies_path.exists():
        logger.debug("Cookies file not found: %s", cookies_path)
        return None

    cookies = parse_netscape_cookies(cookies_path)
    if not cookies:
        logger.debug("No cookies parsed from file")
        return None

    sapisid = get_sapisid(cookies)
    if not sapisid:
        logger.warning("No SAPISID cookie found - authentication not possible")
        return None

    cookie_header = build_cookie_header(cookies)
    authorization = generate_sapisidhash(sapisid)

    # Return headers in the format ytmusicapi expects
    return {
        "Accept": "*/*",
        "Authorization": authorization,
        "Content-Type": "application/json",
        "X-Goog-AuthUser": "0",
        "x-origin": YTM_ORIGIN,
        "Cookie": cookie_header,
    }


def is_authenticated_cookies(cookies_path: Path) -> bool:
    """Check if cookies file contains YouTube Music authentication.

    Args:
        cookies_path: Path to cookies.txt file.

    Returns:
        True if file exists and contains SAPISID cookie.
    """
    if not cookies_path.exists():
        return False

    cookies = parse_netscape_cookies(cookies_path)
    return get_sapisid(cookies) is not None
