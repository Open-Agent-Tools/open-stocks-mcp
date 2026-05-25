"""Pickle-based session persistence: read, write, clear, and encrypt/decrypt."""

import contextlib
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from open_stocks_mcp.logging_config import logger


class SessionPickleManager:
    """Manages pickle read/write/clear and Fernet encryption for session tokens."""

    def __init__(self) -> None:
        self._consecutive_pickle_clear_failures = 0
        self._max_pickle_clear_failures = 3

    def _get_tokens_dir(self) -> Path:
        tokens_dir = Path.home() / ".tokens"
        tokens_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name != "nt":
            try:
                tokens_dir.chmod(0o700)
            except OSError as e:
                logger.warning(f"Could not set secure permissions on {tokens_dir}: {e}")
        return tokens_dir

    def _get_pickle_file_path(self, pickle_name: str = "robinhood") -> Path:
        return self._get_tokens_dir() / f"{pickle_name}.pickle"

    def _get_encrypted_pickle_path(self, pickle_name: str = "robinhood") -> Path:
        return self._get_tokens_dir() / f"{pickle_name}.pickle.enc"

    def _get_fernet_key_path(self) -> Path:
        return self._get_tokens_dir() / ".session.key"

    def _get_or_create_fernet_key(self) -> bytes:
        key_path = self._get_fernet_key_path()
        if key_path.exists():
            return key_path.read_bytes()
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        return key

    def _encrypt_pickle_if_exists(self, pickle_name: str = "robinhood") -> None:
        pickle_path = self._get_pickle_file_path(pickle_name)
        if not pickle_path.exists():
            return
        try:
            key = self._get_or_create_fernet_key()
            ciphertext = Fernet(key).encrypt(pickle_path.read_bytes())
            enc_path = self._get_encrypted_pickle_path(pickle_name)
            enc_path.write_bytes(ciphertext)
            enc_path.chmod(0o600)
            pickle_path.unlink()
            logger.debug(f"Session pickle encrypted: {enc_path}")
        except Exception as e:
            logger.warning(
                f"Could not encrypt session pickle, hardening permissions: {e}"
            )
            with contextlib.suppress(Exception):
                pickle_path.chmod(0o600)

    def _decrypt_pickle_if_exists(self, pickle_name: str = "robinhood") -> bool:
        enc_path = self._get_encrypted_pickle_path(pickle_name)
        if not enc_path.exists():
            return False
        try:
            key = self._get_or_create_fernet_key()
            plaintext = Fernet(key).decrypt(enc_path.read_bytes())
            pickle_path = self._get_pickle_file_path(pickle_name)
            pickle_path.write_bytes(plaintext)
            pickle_path.chmod(0o600)
            logger.debug(f"Session pickle decrypted for use: {pickle_path}")
            return True
        except InvalidToken:
            logger.warning(
                "Session pickle decryption failed (key mismatch or corrupt), treating as missing"
            )
            enc_path.unlink(missing_ok=True)
            return False
        except Exception as e:
            logger.warning(
                f"Could not decrypt session pickle, treating as missing: {e}"
            )
            enc_path.unlink(missing_ok=True)
            return False

    def _clear_pickle_file(self, pickle_name: str = "robinhood") -> bool:
        try:
            pickle_path = self._get_pickle_file_path(pickle_name)
            enc_path = self._get_encrypted_pickle_path(pickle_name)
            cleared = False
            if pickle_path.exists():
                pickle_path.unlink()
                logger.info(f"Cleared pickle file: {pickle_path}")
                cleared = True
            else:
                logger.debug(f"Pickle file does not exist: {pickle_path}")
            if enc_path.exists():
                enc_path.unlink()
                logger.info(f"Cleared encrypted pickle file: {enc_path}")
                cleared = True
            if not cleared:
                logger.debug(f"No session files found for: {pickle_name}")
            self._consecutive_pickle_clear_failures = 0
            return True
        except Exception as e:
            self._consecutive_pickle_clear_failures += 1
            logger.error(f"Failed to clear pickle file: {e}")
            if (
                self._consecutive_pickle_clear_failures
                >= self._max_pickle_clear_failures
            ):
                logger.critical(
                    "Session cache clear failed %s consecutive times; authentication retries will be blocked until cache clear succeeds",
                    self._consecutive_pickle_clear_failures,
                )
            return False

    def should_block_auth_retries(self) -> bool:
        return (
            self._consecutive_pickle_clear_failures >= self._max_pickle_clear_failures
        )
