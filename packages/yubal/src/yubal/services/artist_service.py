"""Artist discovery: search for an artist and list their releases."""

import logging

from yubal.client import YTMusicProtocol
from yubal.exceptions import ArtistNotFoundError
from yubal.models.ytmusic import ArtistDiscography, ArtistRelease, ArtistSearchResult

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_LIMIT = 5


class ArtistDiscographyService:
    """Turn an artist into a list of downloadable release URLs.

    Each release URL is a YouTube Music album playlist URL
    (``playlist?list=OLAK5uy_...``) that can be passed directly to
    PlaylistDownloadService or the API job queue.

    Example:
        >>> service = ArtistDiscographyService(YTMusicClient())
        >>> artist = service.search("Daft Punk")[0]
        >>> discography = service.get_discography(artist.browse_id)
        >>> for url in service.release_urls(discography):
        ...     downloader.download_playlist_all(url)
    """

    def __init__(self, client: YTMusicProtocol) -> None:
        """Initialize the service.

        Args:
            client: YouTube Music API client.
        """
        self._client = client

    def search(
        self, query: str, limit: int = DEFAULT_SEARCH_LIMIT
    ) -> list[ArtistSearchResult]:
        """Search for artists by name.

        Args:
            query: Artist name.
            limit: Maximum number of results.

        Returns:
            Matching artists, best match first.

        Raises:
            ArtistNotFoundError: If no artist matches the query.
            UpstreamAPIError: If the API request fails.
        """
        results = self._client.search_artists(query, limit=limit)
        if not results:
            raise ArtistNotFoundError(f"No artists found for: {query}")
        return results

    def get_discography(
        self,
        channel_id: str,
        *,
        albums: bool = True,
        singles: bool = True,
    ) -> ArtistDiscography:
        """Fetch an artist's albums and/or singles.

        Args:
            channel_id: Artist channel ID (from search results).
            albums: Include albums.
            singles: Include singles and EPs.

        Returns:
            ArtistDiscography with the requested sections populated.

        Raises:
            ArtistNotFoundError: If the artist doesn't exist.
            UpstreamAPIError: If the API request fails.
        """
        discography = self._client.get_artist(channel_id)
        update: dict[str, list[ArtistRelease]] = {}
        if not albums:
            update["albums"] = []
        if not singles:
            update["singles"] = []
        return discography.model_copy(update=update) if update else discography

    @staticmethod
    def releases(discography: ArtistDiscography) -> list[ArtistRelease]:
        """All releases in download order (albums first, then singles)."""
        return [*discography.albums, *discography.singles]

    @classmethod
    def release_urls(cls, discography: ArtistDiscography) -> list[str]:
        """Playlist URLs for every release in the discography."""
        return [r.url for r in cls.releases(discography) if r.url]
