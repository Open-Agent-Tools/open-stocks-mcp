"""Stream manager for Schwab real-time data ingestion."""

import asyncio
import contextlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from open_stocks_mcp.logging_config import logger

if TYPE_CHECKING:
    from schwab.streaming import StreamClient


class SchwabStreamManager:
    """Manages Schwab streaming WebSocket connection and data ingestion.

    This manager handles:
    - WebSocket connection lifecycle
    - Service subscriptions (Level One Equities, Options, etc.)
    - Message handling and data distribution
    - Reconnection logic
    """

    def __init__(self, broker: Any):
        """Initialize stream manager.

        Args:
            broker: SchwabBroker instance
        """
        self.broker = broker
        self.stream_client: StreamClient | None = None
        self._is_running = False
        self._task: asyncio.Task[None] | None = None
        self._handlers: list[Callable[[dict[str, Any]], None]] = []
        self._latest_quotes: dict[str, dict[str, Any]] = {}
        self._latest_option_quotes: dict[str, dict[str, Any]] = {}
        self._latest_level2_books: dict[str, dict[str, Any]] = {}
        self._latest_activity: list[dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        """Check if streamer is running."""
        return self._is_running

    def add_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        """Add a custom message handler."""
        self._handlers.append(handler)

    async def start(self) -> bool:
        """Start the streaming client.

        Returns:
            True if started successfully, False otherwise
        """
        if self._is_running:
            return True

        if not self.broker.is_available():
            logger.error("Cannot start Schwab streamer: broker not authenticated")
            return False

        try:
            from schwab.streaming import StreamClient

            self.stream_client = StreamClient(self.broker.client)

            # Define core handler
            def _core_handler(message: dict[str, Any]) -> None:
                self._handle_message(message)
                for handler in self._handlers:
                    try:
                        handler(message)
                    except Exception as e:
                        logger.error(f"Error in Schwab stream custom handler: {e}")

            # Register handlers for Level One, Level 2 and account activity
            assert self.stream_client is not None
            self.stream_client.add_level_one_equity_handler(_core_handler)
            self.stream_client.add_level_one_option_handler(_core_handler)
            self.stream_client.add_nasdaq_book_handler(_core_handler)
            self.stream_client.add_nyse_book_handler(_core_handler)
            self.stream_client.add_account_activity_handler(_core_handler)

            await self.stream_client.login()
            self._is_running = True
            logger.info("Schwab streaming client logged in and started")

            # Start background task to handle responses
            self._task = asyncio.create_task(self._run_loop())

            return True

        except ImportError:
            logger.error("schwab-py not installed, cannot start streamer")
            return False
        except Exception as e:
            logger.error(f"Failed to start Schwab streamer: {e}")
            self._is_running = False
            return False

    async def stop(self) -> None:
        """Stop the streaming client."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        if self.stream_client:
            # schwab-py StreamClient doesn't have an explicit logout/close,
            # it closes when the connection drops.
            self.stream_client = None

        logger.info("Schwab streaming client stopped")

    async def _run_loop(self) -> None:
        """Background loop to handle WebSocket responses."""
        while self._is_running:
            try:
                if self.stream_client:
                    await self.stream_client.handle_responses()
                else:
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Schwab stream loop: {e}")
                await asyncio.sleep(5)  # Wait before retry
                if self._is_running:
                    # Attempt re-login
                    try:
                        assert self.stream_client is not None
                        await self.stream_client.login()
                    except Exception as re_login_err:
                        logger.error(
                            f"Failed to re-login Schwab stream: {re_login_err}"
                        )

    def _handle_message(self, message: dict[str, Any]) -> None:
        """Process incoming stream messages."""
        service = message.get("service")
        content = message.get("content", [])

        if service == "LEVELONE_EQUITIES":
            for item in content:
                symbol = item.get("key")
                if symbol:
                    if symbol not in self._latest_quotes:
                        self._latest_quotes[symbol] = {}
                    self._latest_quotes[symbol].update(item)
        elif service == "LEVELONE_OPTIONS":
            for item in content:
                symbol = item.get("key")
                if symbol:
                    if symbol not in self._latest_option_quotes:
                        self._latest_option_quotes[symbol] = {}
                    self._latest_option_quotes[symbol].update(item)
        elif service in ("NASDAQ_BOOK", "NYSE_BOOK"):
            for item in content:
                # Level 2 messages might use 'SYMBOL' or 'key'
                symbol = item.get("SYMBOL") or item.get("key")
                if not symbol:
                    continue
                symbol_upper = symbol.upper()
                cache_key = f"{symbol_upper}:{service}"
                self._latest_level2_books[cache_key] = {
                    "symbol": symbol_upper,
                    "service": service,
                    "book_time": item.get("BOOK_TIME"),
                    "bids": item.get("BIDS", []),
                    "asks": item.get("ASKS", []),
                }
        elif service == "ACCT_ACTIVITY":
            for item in content:
                self._latest_activity.append(item)
            # Cap to most recent 100 entries to bound memory
            if len(self._latest_activity) > 100:
                self._latest_activity = self._latest_activity[-100:]

    async def subscribe_quotes(self, symbols: list[str]) -> bool:
        """Subscribe to Level One quotes for symbols."""
        if not self._is_running or not self.stream_client:
            return False

        try:
            # Split into equities and options based on symbol format
            equities = []
            options = []
            for s in symbols:
                if (
                    " " in s or len(s) > 10
                ):  # Simple heuristic for Schwab option symbols
                    options.append(s.upper())
                else:
                    equities.append(s.upper())

            results = []
            if equities:
                await self.stream_client.level_one_equity_subs(equities)
                results.append(True)
            if options:
                results.append(await self.subscribe_option_quotes(options))

            logger.info(f"Subscribed to Schwab quotes: {symbols}")
            return all(results) if results else True
        except Exception as e:
            logger.error(f"Failed to subscribe to Schwab quotes: {e}")
            return False

    async def subscribe_option_quotes(self, symbols: list[str]) -> bool:
        """Subscribe to Level One option quotes for symbols.

        Args:
            symbols: List of Schwab option symbols (e.g. 'AAPL  260619C00150000')

        Returns:
            True if subscription successful, False otherwise
        """
        if not self._is_running or not self.stream_client:
            return False

        try:
            # Uppercase all symbols to ensure consistency
            symbols = [s.upper() for s in symbols]
            await self.stream_client.level_one_option_subs(symbols)
            logger.info(f"Subscribed to Schwab option quotes: {symbols}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to Schwab option quotes: {e}")
            return False

    async def subscribe_account_activity(self) -> bool:
        """Subscribe to account activity stream.

        Returns:
            True if subscription successful, False otherwise
        """
        if not self._is_running or not self.stream_client:
            return False

        try:
            await self.stream_client.account_activity_sub()
            logger.info("Subscribed to Schwab account activity stream")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to Schwab account activity: {e}")
            return False

    async def subscribe_level2(self, symbol: str, venue: str = "nasdaq") -> bool:
        """Subscribe to Level 2 order book for a symbol.

        Args:
            symbol: Ticker symbol
            venue: 'nasdaq' or 'nyse'

        Returns:
            True if subscription successful, False otherwise
        """
        if not self._is_running or not self.stream_client:
            return False

        try:
            symbol = symbol.upper()
            if venue.lower() == "nasdaq":
                await self.stream_client.nasdaq_book_subs([symbol])
            elif venue.lower() == "nyse":
                await self.stream_client.nyse_book_subs([symbol])
            else:
                logger.error(f"Unsupported Level 2 venue: {venue}")
                return False

            logger.info(f"Subscribed to Schwab Level 2 ({venue}): {symbol}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to subscribe to Schwab Level 2 ({venue}) for {symbol}: {e}"
            )
            return False

    def get_latest_activity(self) -> list[dict[str, Any]]:
        """Get latest cached account activity events."""
        return list(self._latest_activity)

    def get_latest_quote(self, symbol: str) -> dict[str, Any] | None:
        """Get latest cached equity quote for symbol."""
        return self._latest_quotes.get(symbol.upper())

    def get_latest_option_quote(self, symbol: str) -> dict[str, Any] | None:
        """Get latest cached option quote for symbol."""
        return self._latest_option_quotes.get(symbol.upper())

    def get_latest_level2(
        self, symbol: str, venue: str = "nasdaq"
    ) -> dict[str, Any] | None:
        """Get latest cached Level 2 book snapshot for symbol and venue."""
        service = "NASDAQ_BOOK" if venue.lower() == "nasdaq" else "NYSE_BOOK"
        cache_key = f"{symbol.upper()}:{service}"
        return self._latest_level2_books.get(cache_key)
