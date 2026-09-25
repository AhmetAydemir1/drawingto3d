"""Errors that every path shares. A local model that is not installed is not a crash."""

from __future__ import annotations


class UnavailableModel(RuntimeError):
    """No local model is installed or answering. Falling back to a cloud host is not allowed."""
