"""Unit tests for the BaseIngester abstract contract."""

import pytest

from game_market_chatbot.ingestion.base import BaseIngester
from game_market_chatbot.ingestion.gamalytics import GamalyticsIngester


def test_base_ingester_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseIngester()


def test_subclass_missing_ingest_cannot_be_instantiated():
    class NoIngest(BaseIngester):
        source_name = "x"

    with pytest.raises(TypeError):
        NoIngest()


def test_subclass_missing_source_name_cannot_be_instantiated():
    class NoName(BaseIngester):
        def ingest(self) -> None:
            pass

    with pytest.raises(TypeError):
        NoName()


def test_complete_subclass_is_instantiable():
    class Good(BaseIngester):
        source_name = "good"

        def ingest(self) -> None:
            return None

    g = Good()
    assert g.source_name == "good"
    assert g.ingest() is None


def test_gamalytics_ingester_satisfies_contract():
    ingester = GamalyticsIngester()
    assert isinstance(ingester, BaseIngester)
    assert ingester.source_name == "gamalytics"
