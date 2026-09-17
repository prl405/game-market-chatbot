"""
Ingester registry.

Maps source name strings to their BaseIngester subclasses.
The CLI uses this registry to dispatch `ingest <source>` commands.

To register a new source, import its class and add it to REGISTRY.
"""

from game_market_chatbot.ingestion.gamalytics import GamalyticsIngester

REGISTRY = {
    "gamalytics": GamalyticsIngester,
}

__all__ = ["REGISTRY"]
