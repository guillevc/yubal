"""Artist command: search an artist and download their albums and singles."""

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from yubal.cli.commands.download import (
    AsciiFilenamesOpt,
    CodecOpt,
    CookiesOpt,
    MaxItemsOpt,
    NoCoverOpt,
    NoM3uOpt,
    NoReplayGainOpt,
    QualityOpt,
    build_playlist_service,
    run_playlist_download,
)
from yubal.cli.formatting import print_section_header
from yubal.cli.logging import setup_logging
from yubal.client import YTMusicClient
from yubal.config import AudioCodec
from yubal.exceptions import CancellationError, YubalError
from yubal.models.ytmusic import ArtistRelease, ArtistSearchResult
from yubal.services import ArtistDiscographyService

logger = logging.getLogger("yubal")


def _print_matches(console: Console, matches: list[ArtistSearchResult]) -> None:
    print_section_header(console, "Artists")
    for i, match in enumerate(matches, start=1):
        console.print(
            f"  [cyan]{i}.[/cyan] {match.artist} [dim]({match.browse_id})[/dim]"
        )


def _print_releases(
    console: Console, title: str, releases: list[ArtistRelease]
) -> None:
    if not releases:
        return
    print_section_header(console, title, str(len(releases)))
    for r in releases:
        year = f"{r.year} " if r.year else ""
        kind = f" [dim]({r.type})[/dim]" if r.type else ""
        console.print(f"  • {year}{r.title}{kind}")


def artist_cmd(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(metavar="QUERY", help="Artist name.")],
    output: Annotated[Path, typer.Argument(metavar="OUTPUT_DIR")],
    pick: Annotated[
        int,
        typer.Option(min=1, help="Which search match to use (1 = top result)."),
    ] = 1,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip the confirmation prompt."),
    ] = False,
    no_albums: Annotated[
        bool, typer.Option("--no-albums", help="Skip albums.")
    ] = False,
    no_singles: Annotated[
        bool, typer.Option("--no-singles", help="Skip singles and EPs.")
    ] = False,
    codec: CodecOpt = AudioCodec.OPUS,
    quality: QualityOpt = 0,
    max_items: MaxItemsOpt = None,
    cookies: CookiesOpt = None,
    no_m3u: NoM3uOpt = False,
    no_cover: NoCoverOpt = False,
    no_replaygain: NoReplayGainOpt = False,
    ascii_filenames: AsciiFilenamesOpt = False,
) -> None:
    """Download an artist's albums and singles.

    Searches YouTube Music for QUERY, shows the top matches, and downloads
    every album and single of the chosen artist (top match by default).
    Each release goes through the same pipeline as `yubal download`, so
    existing files are skipped and re-running is safe.

    Examples:

        yubal artist "Daft Punk" ~/Music

        yubal artist "Daft Punk" ~/Music --no-singles --yes

        yubal artist "Nirvana" ~/Music --pick 2
    """
    console = Console()
    verbose = ctx.obj.get("verbose", False)
    setup_logging(verbose=verbose, console=console)

    if no_albums and no_singles:
        console.print(
            "[red]Error: --no-albums and --no-singles exclude everything[/red]"
        )
        raise typer.Exit(code=1)

    try:
        artists = ArtistDiscographyService(YTMusicClient(cookies_path=cookies))
        with console.status(f"Searching for '{query}'..."):
            matches = artists.search(query)
        _print_matches(console, matches)

        if pick > len(matches):
            console.print(
                f"[red]Error: --pick {pick} but only {len(matches)} matches[/red]"
            )
            raise typer.Exit(code=1)
        chosen = matches[pick - 1]

        with console.status(f"Fetching releases for {chosen.artist}..."):
            discography = artists.get_discography(
                chosen.browse_id, albums=not no_albums, singles=not no_singles
            )
        _print_releases(console, "Albums", discography.albums)
        _print_releases(console, "Singles & EPs", discography.singles)

        releases = [(r, url) for r in artists.releases(discography) if (url := r.url)]
        if not releases:
            console.print(f"[yellow]No releases found for {discography.name}[/yellow]")
            return

        console.print()
        if not yes and not typer.confirm(
            f"Download {len(releases)} releases by {discography.name} to {output}?",
            default=True,
        ):
            raise typer.Abort()

        service = build_playlist_service(
            output=output,
            codec=codec,
            quality=quality,
            max_items=max_items,
            cookies=cookies,
            no_m3u=no_m3u,
            no_cover=no_cover,
            no_replaygain=no_replaygain,
            ascii_filenames=ascii_filenames,
        )

        downloaded = skipped = failed = 0
        failed_releases: list[tuple[ArtistRelease, str]] = []
        for i, (release, url) in enumerate(releases, start=1):
            console.rule(f"[bold][{i}/{len(releases)}] {release.title}[/bold]")
            try:
                result = run_playlist_download(console, service, url, output)
            except (KeyboardInterrupt, CancellationError):
                raise
            except Exception as e:
                logger.error("Failed to download '%s': %s", release.title, e)
                failed_releases.append((release, str(e)))
                continue
            if result:
                downloaded += result.success_count
                skipped += result.skipped_count
                failed += result.failed_count

        print_section_header(console, "Artist summary", discography.name)
        console.print(
            f"  Releases: [green]{len(releases) - len(failed_releases)} OK[/green]  "
            f"[red]{len(failed_releases)} failed[/red]"
        )
        console.print(
            f"  Tracks:   [green]Downloaded: {downloaded}[/green]  "
            f"[yellow]Skipped: {skipped}[/yellow]  "
            f"[red]Failed: {failed}[/red]"
        )
        for release, error in failed_releases:
            console.print(f"    [red]• {release.title}: {error}[/red]")

        if failed_releases:
            raise typer.Exit(code=1)

    except (typer.Exit, typer.Abort):
        raise
    except YubalError as e:
        logger.error(str(e))
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from e
