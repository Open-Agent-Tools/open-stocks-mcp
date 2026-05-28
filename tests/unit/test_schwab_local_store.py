"""Direct unit tests for Schwab local watchlist store helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from open_stocks_mcp.tools.watchlists import schwab_local_store as store


@pytest.mark.unit
def test_normalize_payload_dedupes_and_filters_values() -> None:
    payload = {
        "watchlists": {
            "Tech": [" aapl ", "AAPL", "msft", "", 123, None],
            "Income": ["schd", "vym", "SCHD"],
            42: ["TSLA"],
            "Bad": "not-a-list",
        }
    }

    normalized = store._normalize_payload(payload)

    assert normalized == {
        "Tech": ["AAPL", "MSFT"],
        "Income": ["SCHD", "VYM"],
    }


@pytest.mark.unit
def test_normalize_payload_handles_malformed_root() -> None:
    assert store._normalize_payload(["not", "a", "dict"]) == {}
    assert store._normalize_payload({"watchlists": "bad"}) == {}


@pytest.mark.unit
def test_load_watchlists_missing_file_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = Path("/tmp/does-not-exist-schwab-watchlists.json")
    monkeypatch.setattr(store, "get_store_path", lambda: missing)

    watchlists, error = store.load_watchlists()

    assert watchlists == {}
    assert error is None


@pytest.mark.unit
def test_load_watchlists_reads_and_normalizes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "schwab_watchlists.json"
    path.write_text(
        json.dumps({"watchlists": {"Tech": ["aapl", " AAPL ", "msft", 1]}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(store, "get_store_path", lambda: path)

    watchlists, error = store.load_watchlists()

    assert error is None
    assert watchlists == {"Tech": ["AAPL", "MSFT"]}


@pytest.mark.unit
def test_load_watchlists_returns_error_for_invalid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "schwab_watchlists.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(store, "get_store_path", lambda: path)

    watchlists, error = store.load_watchlists()

    assert watchlists == {}
    assert error is not None
    assert "Unable to read Schwab watchlist store" in error


@pytest.mark.unit
def test_save_watchlists_writes_expected_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "nested" / "schwab_watchlists.json"
    monkeypatch.setattr(store, "get_store_path", lambda: path)

    error = store.save_watchlists({"Tech": ["AAPL", "MSFT"]})

    assert error is None
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted == {"watchlists": {"Tech": ["AAPL", "MSFT"]}}


@pytest.mark.unit
def test_save_watchlists_returns_error_on_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "schwab_watchlists.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(store, "get_store_path", lambda: path)

    def raise_os_error(*_args: object, **_kwargs: object) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "write_text", raise_os_error)

    error = store.save_watchlists({"Tech": ["AAPL"]})

    assert error is not None
    assert "Unable to write Schwab watchlist store" in error


@pytest.mark.unit
def test_add_symbols_merges_with_existing_and_dedupes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "schwab_watchlists.json"
    path.write_text(
        json.dumps({"watchlists": {"Tech": ["AAPL", "MSFT"]}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(store, "get_store_path", lambda: path)

    merged, error = store.add_symbols("Tech", ["MSFT", "TSLA", "AAPL", "NVDA"])

    assert error is None
    assert merged == ["AAPL", "MSFT", "TSLA", "NVDA"]


@pytest.mark.unit
def test_remove_symbols_deletes_empty_watchlist_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "schwab_watchlists.json"
    path.write_text(
        json.dumps({"watchlists": {"Tech": ["AAPL"], "Income": ["SCHD"]}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(store, "get_store_path", lambda: path)

    remaining, error = store.remove_symbols("Tech", ["AAPL"])

    assert error is None
    assert remaining == []
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert "Tech" not in persisted["watchlists"]
    assert persisted["watchlists"]["Income"] == ["SCHD"]
