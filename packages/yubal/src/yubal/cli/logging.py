"""Logging configuration for CLI commands."""

import logging

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(verbose: bool = False, console: Console | None = None) -> None:
    """Configure logging with Rich handler.

    This function clears existing handlers before adding a new one, allowing
    it to be called multiple times to reconfigure logging (e.g., to switch
    from default console to a shared Progress console).

    Args:
        verbose: If True, set log level to DEBUG. Otherwise WARNING.
            When reconfiguring with a console, pass the same verbose
            setting to preserve the log level.
        console: Optional Console instance to use for RichHandler. When
            using Progress bars, pass the same Console to both Progress
            and this function so logs appear above the progress bar.
    """
    level = logging.DEBUG if verbose else logging.WARNING

    # Clear existing handlers to allow reconfiguration
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = RichHandler(
        rich_tracebacks=True,
        show_path=False,
        console=console,
    )
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))

    root_logger.setLevel(level)
    root_logger.addHandler(handler)
