"""General naming helpers shared across project layers."""

from __future__ import annotations

import re


def snake_case(name: str) -> str:
    """Convert a source column name into a warehouse-friendly snake_case name."""

    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    normalized = re.sub(r"_+", "_", normalized)
    if not normalized:
        raise ValueError(f"invalid_column_name: could not normalize '{name}'.")
    return normalized
