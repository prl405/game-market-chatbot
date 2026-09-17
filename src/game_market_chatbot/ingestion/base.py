"""
Abstract base class for all data ingesters.

To add a new data source:
1. Create a new module in this package (e.g. igdb.py).
2. Subclass BaseIngester, set source_name, and implement ingest().
3. Register the class in ingestion/__init__.py REGISTRY.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseIngester(ABC):
    """
    Contract that every ingestion source must satisfy.

    Subclasses are responsible for:
    - Fetching data from an external source (API, file, etc.)
    - Transforming records into the steam_games schema (or a future
      source-specific table).
    - Upserting records into the Turso database via get_connection().
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Human-readable identifier for this source, e.g. "gamalytics".
        Used in CLI output and the ingester registry key.
        """

    @abstractmethod
    def ingest(self) -> None:
        """
        Execute a full ingestion run.

        Implementations should:
        - Print per-page or per-batch progress to stdout.
        - Print a final summary (total records upserted).
        - Raise on unrecoverable errors rather than silently skipping.
        """
