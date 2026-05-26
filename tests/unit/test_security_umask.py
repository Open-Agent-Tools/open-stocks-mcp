import os
from unittest.mock import patch

import pytest

from open_stocks_mcp.brokers.schwab import SchwabBroker
from open_stocks_mcp.brokers.session_state import SessionManager
from open_stocks_mcp.logging_config import setup_logging


def test_schwab_tokens_directory_permissions(tmp_path):
    """Verify that .tokens directory is created with secure permissions by SchwabBroker."""
    # Mock Path.home() to return our tmp_path
    with patch("pathlib.Path.home", return_value=tmp_path):
        # Initialize SchwabBroker which triggers mkdir
        SchwabBroker(api_key="test", app_secret="test")

        token_dir = tmp_path / ".tokens"
        assert token_dir.exists()

        # Check permissions
        mode = os.stat(token_dir).st_mode & 0o777
        assert mode == 0o700, f"Expected mode 0o700, got {oct(mode)}"


def test_session_manager_tokens_directory_permissions(tmp_path):
    """Verify that .tokens directory is created with secure permissions by SessionManager."""
    # Mock Path.home() to return our tmp_path
    with patch("pathlib.Path.home", return_value=tmp_path):
        # Initialize SessionManager
        manager = SessionManager()
        # Trigger _get_pickle_file_path
        manager._get_pickle_file_path()

        token_dir = tmp_path / ".tokens"
        assert token_dir.exists()

        # Check permissions
        mode = os.stat(token_dir).st_mode & 0o777
        assert mode == 0o700, f"Expected mode 0o700, got {oct(mode)}"


def test_session_manager_fixes_existing_permissions(tmp_path):
    """Verify that SessionManager fixes existing insecure permissions."""
    # Mock Path.home() to return our tmp_path
    with patch("pathlib.Path.home", return_value=tmp_path):
        token_dir = tmp_path / ".tokens"
        # Create directory with insecure permissions
        token_dir.mkdir(mode=0o755, exist_ok=True)
        os.chmod(token_dir, 0o755)
        assert (os.stat(token_dir).st_mode & 0o777) == 0o755

        # Initialize SessionManager and trigger _get_pickle_file_path
        manager = SessionManager()
        manager._get_pickle_file_path()

        # Check permissions - should be fixed to 0o700
        mode = os.stat(token_dir).st_mode & 0o777
        assert mode == 0o700, f"Expected mode 0o700, got {oct(mode)}"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only")
def test_schwab_default_token_dir_chmod_warning(tmp_path):
    """SchwabBroker logs a warning when chmod on default ~/.tokens dir fails."""
    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch(
            "open_stocks_mcp.brokers.schwab.os.chmod",
            side_effect=PermissionError("denied"),
        ),
        patch("open_stocks_mcp.brokers.schwab.logger") as mock_logger,
    ):
        SchwabBroker(api_key="test", app_secret="test")

    mock_logger.warning.assert_called_once()
    msg = mock_logger.warning.call_args[0][0]
    assert "Could not set secure permissions" in msg
    assert str(tmp_path / ".tokens") in msg
    assert "denied" in msg


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only")
def test_schwab_custom_token_dir_chmod_warning(tmp_path):
    """SchwabBroker logs a warning when chmod on custom token parent dir fails."""
    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch(
            "open_stocks_mcp.brokers.schwab.os.chmod",
            side_effect=[None, PermissionError("denied")],
        ),
        patch("open_stocks_mcp.brokers.schwab.logger") as mock_logger,
    ):
        SchwabBroker(
            api_key="test",
            app_secret="test",
            token_path=str(tmp_path / ".tokens" / "custom" / "schwab_token.json"),
        )

    mock_logger.warning.assert_called_once()
    msg = mock_logger.warning.call_args[0][0]
    assert "Could not set secure permissions" in msg
    assert str(tmp_path / ".tokens" / "custom") in msg
    assert "denied" in msg


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only")
def test_session_manager_tokens_dir_chmod_warning(tmp_path):
    """SessionManager logs a warning when chmod on tokens dir fails."""
    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch(
            "open_stocks_mcp.brokers.session_pickle.Path.chmod",
            side_effect=PermissionError("denied"),
        ),
        patch("open_stocks_mcp.brokers.session_pickle.logger") as mock_logger,
    ):
        manager = SessionManager()
        manager._get_tokens_dir()

    mock_logger.warning.assert_called_once()
    msg = mock_logger.warning.call_args[0][0]
    assert "Could not set secure permissions" in msg
    assert str(tmp_path / ".tokens") in msg
    assert "denied" in msg


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only")
def test_log_directory_permissions(tmp_path):
    """Verify that the log directory is created with secure 0o700 permissions."""
    log_dir = tmp_path / "logs"
    with patch(
        "open_stocks_mcp.logging_config.get_default_log_dir", return_value=log_dir
    ):
        setup_logging()

        assert log_dir.exists()
        mode = os.stat(log_dir).st_mode & 0o777
        assert mode == 0o700, f"Expected mode 0o700, got {oct(mode)}"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only")
def test_log_directory_fixes_existing_permissions(tmp_path):
    """Verify that setup_logging fixes insecure permissions on an existing log dir."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir(mode=0o755, exist_ok=True)
    os.chmod(log_dir, 0o755)
    assert (os.stat(log_dir).st_mode & 0o777) == 0o755

    with patch(
        "open_stocks_mcp.logging_config.get_default_log_dir", return_value=log_dir
    ):
        setup_logging()

        mode = os.stat(log_dir).st_mode & 0o777
        assert mode == 0o700, f"Expected mode 0o700, got {oct(mode)}"
