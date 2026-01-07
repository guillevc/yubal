#!/usr/bin/env python3
"""Sync beets config with version-aware backup."""

import shutil
from pathlib import Path

import yaml

DEFAULT_CONFIG = Path("/app/beets-default/config.yaml")
TARGET_CONFIG = Path("/app/beets/config.yaml")


def get_version(config_path: Path) -> str | None:
    """Extract __yubal.version from config, None if missing."""
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return data.get("__yubal", {}).get("version")
    except Exception:
        return None


def main() -> None:
    TARGET_CONFIG.parent.mkdir(parents=True, exist_ok=True)

    if not TARGET_CONFIG.exists():
        shutil.copy(DEFAULT_CONFIG, TARGET_CONFIG)
        print("Initialized beets config")
        return

    default_version = get_version(DEFAULT_CONFIG)
    target_version = get_version(TARGET_CONFIG)

    # Missing version = legacy config
    if target_version is None:
        backup = TARGET_CONFIG.with_name("config_legacy.yaml")
        shutil.move(TARGET_CONFIG, backup)
        shutil.copy(DEFAULT_CONFIG, TARGET_CONFIG)
        print(f"Migrated legacy beets config -> v{default_version}")
        print(f"Backup saved: {backup.name}")
        return

    if default_version == target_version:
        print(f"Beets config up to date (v{target_version})")
        return

    # Version differs: backup and replace
    backup = TARGET_CONFIG.with_name(f"config_{target_version}.yaml")
    shutil.move(TARGET_CONFIG, backup)
    shutil.copy(DEFAULT_CONFIG, TARGET_CONFIG)
    print(f"Migrated beets config: v{target_version} -> v{default_version}")
    print(f"Backup saved: {backup.name}")


if __name__ == "__main__":
    main()
