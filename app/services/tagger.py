"""Music tagging and organization using beets CLI."""
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.constants import AUDIO_EXTENSIONS


@dataclass
class TagResult:
    """Result of a tagging operation."""

    success: bool
    source_dir: Path
    dest_dir: Optional[Path] = None
    album_name: Optional[str] = None
    artist_name: Optional[str] = None
    track_count: int = 0
    error: Optional[str] = None


@dataclass
class LibraryHealth:
    """Result of a library health check."""

    healthy: bool
    library_album_count: int
    database_album_count: int
    message: str


class Tagger:
    """Handles music tagging and organization via beets CLI."""

    def __init__(self, beets_config: Path, library_dir: Path, beets_db: Path):
        self.beets_config = beets_config
        self.library_dir = library_dir
        self.beets_db = beets_db

    def _get_beet_command(self) -> list[str]:
        """Get the command to run beets using the current Python."""
        # Use python -m to avoid shebang issues with venv scripts
        return [sys.executable, "-m", "beets"]

    def _get_beets_env(self) -> dict[str, str]:
        """Get environment variables for running beets commands."""
        env = os.environ.copy()
        env["BEETSDIR"] = str(self.beets_config.parent)
        return env

    def tag_album(self, source_dir: Path, copy: bool = False) -> TagResult:
        """
        Tag and organize an album using beets.

        Runs beets import in quiet mode to automatically tag
        and move files to the organized library.

        Args:
            source_dir: Directory containing downloaded audio files
            copy: If True, copy files to library instead of moving (originals stay tagged in place)

        Returns:
            TagResult with success status and final location
        """
        # Check source directory has files
        audio_files = self._find_audio_files(source_dir)
        if not audio_files:
            return TagResult(
                success=False,
                source_dir=source_dir,
                error="No audio files found in source directory",
            )

        try:
            result = self._run_beets_import(source_dir, copy=copy)

            if result.returncode != 0:
                return TagResult(
                    success=False,
                    source_dir=source_dir,
                    error=f"Beets import failed: {result.stderr}",
                )

            # Find where the album was imported
            dest_dir = self._find_imported_album(source_dir)
            track_count = len(audio_files)

            return TagResult(
                success=True,
                source_dir=source_dir,
                dest_dir=dest_dir,
                track_count=track_count,
            )

        except subprocess.TimeoutExpired:
            return TagResult(
                success=False,
                source_dir=source_dir,
                error="Beets import timed out after 5 minutes",
            )
        except FileNotFoundError as e:
            return TagResult(
                success=False,
                source_dir=source_dir,
                error=f"Beets module not found. Error: {e}",
            )
        except Exception as e:
            return TagResult(
                success=False,
                source_dir=source_dir,
                error=f"Unexpected error during tagging: {str(e)}",
            )

    def _run_beets_import(self, source_dir: Path, copy: bool = False) -> subprocess.CompletedProcess[str]:
        """
        Execute beets import command.

        Uses quiet mode (-q) for non-interactive import.
        Uses move mode to relocate files to library (unless copy is True).
        """
        # Ensure library directory exists (beets prompts otherwise)
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.beets_db.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._get_beet_command() + [
            "--config",
            str(self.beets_config),
            "import",
        ]

        # --copy: copy files to library instead of moving (originals stay in place, tagged)
        if copy:
            cmd.append("--copy")

        cmd.append(str(source_dir))

        print(f"Running beets: {' '.join(cmd)}")

        # Use Popen to stream output in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr into stdout
            text=True,
            env=self._get_beets_env(),
            cwd=str(self.beets_config.parent.parent),
        )

        stdout_lines = []
        for line in process.stdout:
            line = line.rstrip()
            print(f"  [beets] {line}")
            stdout_lines.append(line)

        process.wait(timeout=300)
        print(f"Beets returncode: {process.returncode}")

        # Return a CompletedProcess-like result for compatibility
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout="\n".join(stdout_lines),
            stderr="",
        )

    def _find_audio_files(self, directory: Path) -> list[Path]:
        """Find all audio files in a directory."""
        return [
            f for f in directory.iterdir()
            if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
        ]

    def _get_album_metadata(self, audio_file: Path) -> tuple[Optional[str], Optional[str]]:
        """Extract album and artist from an audio file using ffprobe."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(audio_file)],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout)
            tags = data.get("format", {}).get("tags", {})
            return tags.get("album"), tags.get("artist")
        except Exception as e:
            print(f"  [warning] Failed to read metadata from {audio_file.name}: {e}")
            return None, None

    def _album_exists_in_library(self, album: str, artist: str) -> Optional[Path]:
        """Check if an album already exists in the beets library."""
        if not album:
            return None

        # Query beets for the album
        cmd = self._get_beet_command() + [
            "--config", str(self.beets_config),
            "ls", "-a", "-p",  # -a for albums, -p for path
            f"album:{album}",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=self._get_beets_env(), timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                # Return the first matching album path
                paths = result.stdout.strip().split("\n")
                if paths and paths[0]:
                    return Path(paths[0])
        except Exception as e:
            print(f"  [warning] Failed to check if album exists: {e}")

        return None

    def _find_imported_album(self, source_dir: Path) -> Optional[Path]:
        """
        Find where beets moved the album in the library.

        Since beets organizes by artist/album, we look for recently
        modified directories in the library.
        """
        if not self.library_dir.exists():
            return None

        # Find the most recently modified album directory
        newest_dir = None
        newest_time = 0

        for artist_dir in self.library_dir.iterdir():
            if not artist_dir.is_dir():
                continue
            for album_dir in artist_dir.iterdir():
                if not album_dir.is_dir():
                    continue
                mtime = album_dir.stat().st_mtime
                if mtime > newest_time:
                    newest_time = mtime
                    newest_dir = album_dir

        return newest_dir

    def _count_library_albums(self) -> int:
        """Count albums in the library folder (Artist/Album structure)."""
        if not self.library_dir.exists():
            return 0
        count = 0
        for artist_dir in self.library_dir.iterdir():
            if artist_dir.is_dir():
                for album_dir in artist_dir.iterdir():
                    if album_dir.is_dir() and self._find_audio_files(album_dir):
                        count += 1
        return count

    def check_library_health(self) -> LibraryHealth:
        """
        Check if the beets database is in sync with the library folder.

        Returns:
            LibraryHealth with sync status and counts
        """
        library_album_count = self._count_library_albums()
        database_album_count = self._count_database_albums()

        # Determine health status
        if library_album_count == 0 and database_album_count == 0:
            return LibraryHealth(
                healthy=True,
                library_album_count=0,
                database_album_count=0,
                message="Empty library - ready for first import",
            )

        if library_album_count > 0 and database_album_count == 0:
            return LibraryHealth(
                healthy=False,
                library_album_count=library_album_count,
                database_album_count=0,
                message=f"Database is empty but library has {library_album_count} albums - rebuild needed",
            )

        if database_album_count > 0 and library_album_count == 0:
            return LibraryHealth(
                healthy=False,
                library_album_count=0,
                database_album_count=database_album_count,
                message=f"Database has {database_album_count} albums but library folder is empty",
            )

        # Both have albums - check if counts match (rough heuristic)
        if abs(library_album_count - database_album_count) > 1:
            return LibraryHealth(
                healthy=False,
                library_album_count=library_album_count,
                database_album_count=database_album_count,
                message=f"Mismatch: {library_album_count} albums in folder, {database_album_count} in database",
            )

        return LibraryHealth(
            healthy=True,
            library_album_count=library_album_count,
            database_album_count=database_album_count,
            message=f"Healthy: {library_album_count} albums in sync",
        )

    def _count_database_albums(self) -> int:
        """Count the number of albums in the beets database."""
        if not self.beets_db.exists():
            return 0

        cmd = self._get_beet_command() + [
            "--config", str(self.beets_config),
            "ls", "-a",  # List albums only
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, env=self._get_beets_env(), timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return len(result.stdout.strip().split("\n"))
            return 0
        except Exception as e:
            print(f"  [warning] Failed to count database albums: {e}")
            return 0

    def rebuild_database(self) -> tuple[bool, str]:
        """
        Rebuild the beets database from existing library files.

        This re-imports all albums in the library folder without
        modifying the files or fetching new metadata.

        Returns:
            Tuple of (success, message)
        """
        if not self.library_dir.exists():
            return False, "Library directory does not exist"

        album_count = self._count_library_albums()
        if album_count == 0:
            return False, "No albums found in library to rebuild from"

        # Run beets import with --noautotag to just register files
        cmd = self._get_beet_command() + [
            "--config", str(self.beets_config),
            "import",
            "--noautotag",  # Don't fetch metadata, trust existing tags
            "--nowrite",    # Don't modify files
            str(self.library_dir),
        ]

        print(f"Rebuilding database: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=self._get_beets_env(),
            )

            for line in process.stdout:
                line = line.rstrip()
                print(f"  [beets] {line}")

            process.wait(timeout=600)  # 10 minutes for large libraries

            if process.returncode == 0:
                return True, f"Successfully rebuilt database from {album_count} albums"
            else:
                return False, f"Rebuild failed with return code {process.returncode}"

        except subprocess.TimeoutExpired:
            return False, "Rebuild timed out after 10 minutes"
        except Exception as e:
            return False, f"Rebuild failed: {str(e)}"
