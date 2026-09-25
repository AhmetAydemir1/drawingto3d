"""Offline technical drawing to STEP."""

from __future__ import annotations

import os
from pathlib import Path

__version__ = "0.1.0"

# ezdxf (pulled in by build123d) writes a font cache on import.
# Point it at the project so a locked home directory does not warn.
_cache = Path(__file__).resolve().parents[2] / ".cache"
os.environ.setdefault("XDG_CACHE_HOME", str(_cache))
_cache.mkdir(parents=True, exist_ok=True)
