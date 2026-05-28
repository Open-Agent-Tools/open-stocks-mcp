"""Direct unit tests for Schwab local watchlist store helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from open_stocks_mcp.tools.watchlists import schwab_local_store as store
from open_stocks_mcp.tools.watchlists.schwab_local_store import add_symbols, remove_symbols


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
def test_load_watchlists_missing_file_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    missing = Path("/tmp/does-not-exist-schwab-watchlists.json")
    monkeypatch.setattr(store, "get_store_path", lambda: missing)

    watchlists, error = store.load_watchlists()

    assert watchlists == {}
    assert error is None


@pytest.mark.unit
def test_load_watchlists_reads_and_normalizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
def test_save_watchlists_writes_expected_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


@pytest.fixture(autouse=True)
def _tmp_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    local_store = tmp_path / "watchlists.json"
    monkeypatch.setenv("OPEN_STOCKS_SCHWAB_WATCHLIST_STORE", str(local_store))


def _seed(watchlists: dict[str, list[str]]) -> None:
    path = Path(os.environ["OPEN_STOCKS_SCHWAB_WATCHLIST_STORE"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"watchlists": watchlists}), encoding="utf-8")


class TestAddSymbolsNormalization:
    @pytest.mark.journey_watchlists
    @pytest.mark.unit
    def test_lowercase_symbol_not_duplicated(self) -> None:
        _seed({"Tech": ["MSFT", "AAPL"]})
        result, error = add_symbols("Tech", ["msft"])
        assert error is None
        assert result == ["MSFT", "AAPL"]

    @pytest.mark.journey_watchlists
    @pytest.mark.unit
    def test_whitespace_symbol_not_duplicated(self) -> None:
        _seed({"Tech": ["MSFT"]})
        result, error = add_symbols("Tech", ["  msft  "])
        assert error is None
        assert result == ["MSFT"]

    @pytest.mark.journey_watchlists
    @pytest.mark.unit
    def test_new_symbol_added_normalized(self) -> None:
        _seed({"Tech": ["MSFT"]})
        result, error = add_symbols("Tech", ["goog"])
        assert error is None
        assert result == ["MSFT", "GOOG"]

    @pytest.mark.journey_watchlists
    @pytest.mark.unit
    def test_mixed_case_duplicates_collapsed(self) -> None:
        _seed({"Tech": ["AAPL"]})
        result, error = add_symbols("Tech", ["msft", "Msft", "MSFT"])
        assert error is None
        assert result == ["AAPL", "MSFT"]


class TestRemoveSymbolsNormalization:
    @pytest.mark.journey_watchlists
    @pytest.mark.unit
    def test_lowercase_removes_uppercase(self) -> None:
        _seed({"Tech": ["MSFT", "AAPL"]})
        result, error = remove_symbols("Tech", ["msft"])
        assert error is None
        assert result == ["AAPL"]

    @pytest.mark.journey_watchlists
    @pytest.mark.unit
    def test_whitespace_removes_symbol(self) -> None:
        _seed({"Tech": ["MSFT", "AAPL"]})
        result, error = remove_symbols("Tech", ["  msft  "])
        assert error is None
        assert result == ["AAPL"]

    @pytest.mark.journey_watchlists
    @pytest.mark.unit
    def test_nonexistent_symbol_no_op(self) -> None:
        _seed({"Tech": ["MSFT", "AAPL"]})
        result, error = remove_symbols("Tech", ["GOOG"])
        assert error is None
        assert result == ["MSFT", "AAPL"]
