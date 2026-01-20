"""Artist formatting utilities."""

from yubal.models.ytmusic import Artist


def format_artists(artists: list[Artist]) -> str:
    """Format artists list as 'Artist One; Artist Two'.

    Args:
        artists: List of Artist objects.

    Returns:
        Semicolon-separated artist names.
    """
    if not artists:
        return ""
    return "; ".join(a.name for a in artists if a.name)
