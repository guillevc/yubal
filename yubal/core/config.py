"""Application configuration paths."""

from pathlib import Path

# PACKAGE_ROOT: yubal package directory
PACKAGE_ROOT = Path(__file__).parent.parent

# APP_ROOT: project root (where pyproject.toml is)
APP_ROOT = PACKAGE_ROOT.parent

# Default directories (can be overridden via CLI options)
DATA_DIR = APP_ROOT / "data"
CONFIG_DIR = PACKAGE_ROOT / "config"

DEFAULT_BEETS_CONFIG = CONFIG_DIR / "config.yaml"
DEFAULT_BEETS_DB = CONFIG_DIR / "beets.db"
DEFAULT_LIBRARY_DIR = DATA_DIR
