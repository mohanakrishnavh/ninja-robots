"""Shared utilities used by every platform-specific job search client."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "job_search_config.json"


def load_platform_config(platform: str) -> dict:
    """Load the static JSON config block for a given platform (e.g. 'linkedin', 'indeed')."""
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        config = json.load(f)
    return config[platform]


def get_env_credential(var_name: str) -> Optional[str]:
    """Read a credential from an environment variable, or None if unset.

    Credentials must never be hardcoded in source, config, or fixtures --
    always pass them via environment variables at runtime.
    """
    return os.environ.get(var_name) or None


@dataclass
class JobPosting:
    """Normalized job posting shape returned by every platform client."""

    title: str
    company: str
    location: str
    url: str
    source: str
    job_id: Optional[str] = None
    posted_at: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)
