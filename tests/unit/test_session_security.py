"""Tests for session-pickle encryption and directory-permission hardening."""

import stat
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from open_stocks_mcp.brokers.session_pickle import SessionPickleManager
from open_stocks_mcp.brokers.session_state import SessionManager


@pytest.fixture()
def tmp_tokens_dir(tmp_path: Path) -> Path:
    """Return a temporary directory used as the ~/.tokens stand-in."""
    return tmp_path / ".tokens"


@pytest.fixture()
def manager(tmp_tokens_dir: Path) -> Generator[SessionPickleManager, None, None]:
    """SessionPickleManager with home directory patched to a temp location."""
    with patch(
        "open_stocks_mcp.brokers.session_pickle.Path.home",
        return_value=tmp_tokens_dir.parent,
    ):
        yield SessionPickleManager()


class TestTokensDirectoryPermissions:
    def test_directory_created_with_restricted_permissions(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        manager._get_tokens_dir()
        assert tmp_tokens_dir.exists()
        mode = stat.S_IMODE(tmp_tokens_dir.stat().st_mode)
        assert mode == 0o700

    def test_existing_directory_permissions_are_hardened(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        # Create directory with looser permissions first
        tmp_tokens_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
        manager._get_tokens_dir()
        mode = stat.S_IMODE(tmp_tokens_dir.stat().st_mode)
        assert mode == 0o700


class TestFernetKeyManagement:
    def test_key_file_created_on_first_access(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        key = manager._get_or_create_fernet_key()
        key_path = tmp_tokens_dir / ".session.key"
        assert key_path.exists()
        assert key == key_path.read_bytes()

    def test_key_file_has_restricted_permissions(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        manager._get_or_create_fernet_key()
        key_path = tmp_tokens_dir / ".session.key"
        mode = stat.S_IMODE(key_path.stat().st_mode)
        assert mode == 0o600

    def test_same_key_returned_on_subsequent_calls(
        self, manager: SessionPickleManager
    ) -> None:
        key1 = manager._get_or_create_fernet_key()
        key2 = manager._get_or_create_fernet_key()
        assert key1 == key2

    def test_valid_fernet_key_generated(self, manager: SessionPickleManager) -> None:
        key = manager._get_or_create_fernet_key()
        # Fernet key must be usable — if it's invalid Fernet() raises ValueError
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(b"test")
        assert fernet.decrypt(ciphertext) == b"test"


class TestPickleEncryption:
    def test_encrypt_removes_plaintext(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        pickle_path = tmp_tokens_dir / "robinhood.pickle"
        tmp_tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        pickle_path.write_bytes(b"fake-pickle-data")

        manager._encrypt_pickle_if_exists()

        assert not pickle_path.exists()

    def test_encrypt_creates_enc_file(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        pickle_path = tmp_tokens_dir / "robinhood.pickle"
        tmp_tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        pickle_path.write_bytes(b"fake-pickle-data")

        manager._encrypt_pickle_if_exists()

        enc_path = tmp_tokens_dir / "robinhood.pickle.enc"
        assert enc_path.exists()

    def test_enc_file_has_restricted_permissions(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        pickle_path = tmp_tokens_dir / "robinhood.pickle"
        tmp_tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        pickle_path.write_bytes(b"fake-pickle-data")

        manager._encrypt_pickle_if_exists()

        enc_path = tmp_tokens_dir / "robinhood.pickle.enc"
        mode = stat.S_IMODE(enc_path.stat().st_mode)
        assert mode == 0o600

    def test_encrypt_no_op_when_no_plaintext(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        manager._encrypt_pickle_if_exists()  # Should not raise
        enc_path = tmp_tokens_dir / "robinhood.pickle.enc"
        assert not enc_path.exists()


class TestPickleDecryption:
    def test_round_trip_preserves_content(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        original_data = b"serialized-oauth-token-data"
        pickle_path = tmp_tokens_dir / "robinhood.pickle"
        tmp_tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        pickle_path.write_bytes(original_data)

        manager._encrypt_pickle_if_exists()
        assert not pickle_path.exists()

        result = manager._decrypt_pickle_if_exists()

        assert result is True
        assert pickle_path.exists()
        assert pickle_path.read_bytes() == original_data

    def test_decrypt_returns_false_when_no_enc_file(
        self, manager: SessionPickleManager
    ) -> None:
        result = manager._decrypt_pickle_if_exists()
        assert result is False

    def test_corrupt_enc_file_is_removed(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        tmp_tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        enc_path = tmp_tokens_dir / "robinhood.pickle.enc"
        enc_path.write_bytes(b"not-valid-fernet-ciphertext")

        result = manager._decrypt_pickle_if_exists()

        assert result is False
        assert not enc_path.exists()

    def test_decrypted_file_has_restricted_permissions(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        pickle_path = tmp_tokens_dir / "robinhood.pickle"
        tmp_tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        pickle_path.write_bytes(b"data")

        manager._encrypt_pickle_if_exists()
        manager._decrypt_pickle_if_exists()

        mode = stat.S_IMODE(pickle_path.stat().st_mode)
        assert mode == 0o600


class TestLoginPickleReencryption:
    @pytest.mark.parametrize("login_result", [False, RuntimeError("login failed")])
    def test_login_failure_reencrypts_decrypted_pickle(
        self,
        manager: SessionPickleManager,
        tmp_tokens_dir: Path,
        login_result: bool | RuntimeError,
    ) -> None:
        pickle_path = tmp_tokens_dir / "robinhood.pickle"
        enc_path = tmp_tokens_dir / "robinhood.pickle.enc"
        tmp_tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        pickle_path.write_bytes(b"serialized-oauth-token-data")
        manager._encrypt_pickle_if_exists()

        if isinstance(login_result, Exception):
            side_effect = login_result
            return_value = None
        else:
            side_effect = None
            return_value = login_result

        with patch(
            "open_stocks_mcp.brokers.session_mfa.rh.login",
            return_value=return_value,
            side_effect=side_effect,
        ):
            session_manager = SessionManager()
            session_manager._pickle = manager

            assert (
                session_manager._login_with_device_verification("user", "pass") is False
            )

        assert not pickle_path.exists()
        assert enc_path.exists()


class TestClearPickleFile:
    def test_clears_both_plaintext_and_encrypted(
        self, manager: SessionPickleManager, tmp_tokens_dir: Path
    ) -> None:
        tmp_tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        pickle_path = tmp_tokens_dir / "robinhood.pickle"
        enc_path = tmp_tokens_dir / "robinhood.pickle.enc"
        pickle_path.write_bytes(b"data")
        enc_path.write_bytes(b"encrypted-data")

        result = manager._clear_pickle_file()

        assert result is True
        assert not pickle_path.exists()
        assert not enc_path.exists()

    def test_clear_succeeds_when_no_files_exist(
        self, manager: SessionPickleManager
    ) -> None:
        result = manager._clear_pickle_file()
        assert result is True

    def test_reset_clear_failures_allows_auth_retries(
        self, manager: SessionPickleManager
    ) -> None:
        manager._consecutive_pickle_clear_failures = 3

        manager.reset_clear_failures()

        assert manager.should_block_auth_retries() is False


class TestSessionInfoCircuitBreaker:
    def test_get_session_info_includes_pickle_clear_circuit_breaker_state(
        self, manager: SessionPickleManager
    ) -> None:
        session_manager = SessionManager(pickle_manager=manager)
        manager._consecutive_pickle_clear_failures = manager._max_pickle_clear_failures

        info = session_manager.get_session_info()

        assert (
            info["consecutive_pickle_clear_failures"]
            == manager._consecutive_pickle_clear_failures
        )
        assert info["auth_retries_blocked"] is True
