"""Database layer for Amanak."""

from .database import ensure_db, get_stats, record_check

__all__ = ["ensure_db", "record_check", "get_stats"]
