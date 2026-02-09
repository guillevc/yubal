"""Shared type definitions for the application."""

from collections.abc import Callable
from datetime import datetime

# Callable type aliases for dependency injection
type Clock = Callable[[], datetime]
type IdGenerator = Callable[[], str]
