"""Tests for virtual charger filtering and idle energy parsing."""

from __future__ import annotations

from custom_components.jullix.models.charger import parse_chargers_list


def test_parse_chargers_skips_virtual_connection_status():
    data = [
        {
            "device_id": "f412faed7298",
            "name": "Charger online",
            "connection": {"status": "online", "error": "no_error"},
            "active": True,
        },
        {
            "device_id": "d09fd9100098",
            "name": "Charger virtual",
            "connection": {"status": "virtual", "error": "not_connected_to_router"},
            "active": False,
        },
    ]
    chargers = parse_chargers_list(data)
    assert len(chargers) == 1
    assert chargers[0].mac == "f412faed7298"


def test_parse_chargers_skips_top_level_virtual_status():
    data = [{"device_id": "abc", "status": "virtual", "name": "V"}]
    assert parse_chargers_list(data) == ()
