"""Application configuration paths."""
from pathlib import Path

APP_ROOT = Path(__file__).parent.parent
CONFIG_DIR = APP_ROOT / "config"
DATA_DIR = APP_ROOT / "data"

DEFAULT_BEETS_CONFIG = CONFIG_DIR / "beets_config.yaml"
DEFAULT_BEETS_DB = CONFIG_DIR / "beets.db"
DEFAULT_LIBRARY_DIR = DATA_DIR
