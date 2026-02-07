"""Domain-specific library modules.

Modules here import yubal domain models and provide higher-level logic
(matching, playlist generation, etc.). Pure utilities that don't depend
on domain models live in ``yubal.utils`` instead.

Consumers should import directly from submodules::

    from yubal.lib.matching import find_best_album_match
    from yubal.lib.m3u import write_m3u
"""
