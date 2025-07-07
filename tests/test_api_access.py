# tests/test_api_access.py
import os

import pytest
import robin_stocks.robinhood as rh
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@pytest.fixture(scope="module")
def robinhood_session():
    """
    Pytest fixture to handle Robinhood login and logout for a test module.
    Requires ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD to be set.
    """
    username = os.getenv("ROBINHOOD_USERNAME")
    password = os.getenv("ROBINHOOD_PASSWORD")

    # Skip test if username or password are not available
    if not all([username, password]):
        pytest.skip(
            "Skipping integration test: ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD "
            "environment variables must be set."
        )

    # Perform login with stored session if available
    login_response = rh.login(
        username=username,
        password=password,
        store_session=True,  # Store session for reuse
    )

    # Check for successful login before yielding to tests
    assert login_response is not None, (
        "Login failed: rh.login() returned None. Check credentials."
    )
    assert "access_token" in login_response, (
        f"Login failed: {login_response.get('detail', 'Unknown error')}"
    )

    yield

    # Teardown: logout and remove the pickle file to ensure clean state
    rh.logout()
    if os.path.exists("robinhood.pickle"):
        os.remove("robinhood.pickle")


@pytest.mark.integration
def test_successful_login_and_get_profile(robinhood_session):
    """
    Tests that a simple, authenticated API call can be made after a successful login.
    The robinhood_session fixture handles the login and logout.
    """
    # If the fixture was successful, we are logged in.
    # Now, try to access a basic authenticated endpoint.
    profile_info = rh.load_user_profile()

    assert profile_info is not None
    assert "username" in profile_info
