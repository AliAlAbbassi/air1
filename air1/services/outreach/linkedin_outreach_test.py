import pytest
from unittest.mock import AsyncMock, patch

from air1.services.outreach.linkedin_outreach import RateLimitHandler, LinkedinOutreach


class TestRateLimitHandler:
    """Tests for RateLimitHandler class"""

    def test_init_default_values(self):
        """Test initialization with default values."""
        handler = RateLimitHandler()
        assert handler.initial_delay == 5
        assert handler.max_delay == 300
        assert handler.max_retries == 5
        assert handler.jitter_factor == 0.3
        assert handler.current_delay == 5
        assert handler.consecutive_rate_limits == 0

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        handler = RateLimitHandler(
            initial_delay=10,
            max_delay=600,
            max_retries=3,
            jitter_factor=0.5,
        )
        assert handler.initial_delay == 10
        assert handler.max_delay == 600
        assert handler.max_retries == 3
        assert handler.jitter_factor == 0.5
        assert handler.current_delay == 10

    def test_add_jitter_returns_value_in_range(self):
        """Test that jitter stays within expected range."""
        handler = RateLimitHandler(initial_delay=10, jitter_factor=0.3)

        # Run multiple times to test randomness
        for _ in range(100):
            result = handler._add_jitter(10)
            # With jitter_factor=0.3, result should be between 7 and 13
            assert 7 <= result <= 13

    def test_add_jitter_zero_factor(self):
        """Test that zero jitter factor returns exact value."""
        handler = RateLimitHandler(jitter_factor=0.0)
        result = handler._add_jitter(10)
        assert result == 10

    def test_reset(self):
        """Test reset method returns handler to initial state."""
        handler = RateLimitHandler(initial_delay=5)
        handler.current_delay = 100
        handler.consecutive_rate_limits = 3

        handler.reset()

        assert handler.current_delay == 5
        assert handler.consecutive_rate_limits == 0


class TestRateLimitHandlerDetection:
    """Tests for rate limit detection"""

    @pytest.mark.asyncio
    async def test_detect_rate_limit_no_indicators(self):
        """Test detection returns False when no indicators present."""
        handler = RateLimitHandler()
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/in/john-doe"
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await handler.detect_rate_limit(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_detect_rate_limit_visible_indicator(self):
        """Test detection returns True when rate limit indicator is visible."""
        handler = RateLimitHandler()
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/in/john-doe"

        # First call returns a visible element, subsequent calls return None
        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        result = await handler.detect_rate_limit(mock_page)

        assert result is True

    @pytest.mark.asyncio
    async def test_detect_rate_limit_hidden_indicator(self):
        """Test detection returns False when indicator exists but is hidden."""
        handler = RateLimitHandler()
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/in/john-doe"

        mock_element = AsyncMock()
        mock_element.is_visible = AsyncMock(return_value=False)
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        result = await handler.detect_rate_limit(mock_page)

        assert result is False

    @pytest.mark.asyncio
    async def test_detect_rate_limit_checkpoint_url(self):
        """Test detection returns True for checkpoint URL."""
        handler = RateLimitHandler()
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/checkpoint/challenge"
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await handler.detect_rate_limit(mock_page)

        assert result is True

    @pytest.mark.asyncio
    async def test_detect_rate_limit_captcha_url(self):
        """Test detection returns True for captcha URL."""
        handler = RateLimitHandler()
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/captcha/verify"
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await handler.detect_rate_limit(mock_page)

        assert result is True

    @pytest.mark.asyncio
    async def test_detect_rate_limit_error_url(self):
        """Test detection returns True for error URL."""
        handler = RateLimitHandler()
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/error/something"
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await handler.detect_rate_limit(mock_page)

        assert result is True


class TestRateLimitHandlerBackoff:
    """Tests for exponential backoff behavior"""

    @pytest.mark.asyncio
    async def test_wait_with_backoff_no_rate_limit(self):
        """Test normal wait without rate limit."""
        handler = RateLimitHandler(initial_delay=5, jitter_factor=0)
        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        result = await handler.wait_with_backoff(mock_page, detected_rate_limit=False)

        assert result is True
        assert handler.current_delay == 5
        assert handler.consecutive_rate_limits == 0
        mock_page.wait_for_timeout.assert_called_once_with(5000)

    @pytest.mark.asyncio
    async def test_wait_with_backoff_rate_limit_doubles_delay(self):
        """Test delay doubles on rate limit."""
        handler = RateLimitHandler(initial_delay=5, max_delay=300, jitter_factor=0)
        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        result = await handler.wait_with_backoff(mock_page, detected_rate_limit=True)

        assert result is True
        assert handler.current_delay == 10  # Doubled from 5
        assert handler.consecutive_rate_limits == 1
        mock_page.wait_for_timeout.assert_called_once_with(10000)

    @pytest.mark.asyncio
    async def test_wait_with_backoff_respects_max_delay(self):
        """Test delay doesn't exceed max_delay."""
        handler = RateLimitHandler(initial_delay=200, max_delay=300, jitter_factor=0)
        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        await handler.wait_with_backoff(mock_page, detected_rate_limit=True)

        # Should be capped at 300, not 400
        assert handler.current_delay == 300
        mock_page.wait_for_timeout.assert_called_once_with(300000)

    @pytest.mark.asyncio
    async def test_wait_with_backoff_resets_on_success(self):
        """Test delay resets after successful request."""
        handler = RateLimitHandler(initial_delay=5, jitter_factor=0)
        handler.current_delay = 80
        handler.consecutive_rate_limits = 3
        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        await handler.wait_with_backoff(mock_page, detected_rate_limit=False)

        assert handler.current_delay == 5
        assert handler.consecutive_rate_limits == 0

    @pytest.mark.asyncio
    async def test_wait_with_backoff_max_retries_exceeded(self):
        """Test returns False when max retries exceeded."""
        handler = RateLimitHandler(initial_delay=5, max_retries=3, jitter_factor=0)
        handler.consecutive_rate_limits = 3  # Already at max
        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        result = await handler.wait_with_backoff(mock_page, detected_rate_limit=True)

        assert result is False
        assert handler.consecutive_rate_limits == 4  # Incremented past max
        # Should not have waited since we're stopping
        mock_page.wait_for_timeout.assert_not_called()

    @pytest.mark.asyncio
    async def test_exponential_backoff_sequence(self):
        """Test correct exponential backoff sequence."""
        handler = RateLimitHandler(initial_delay=5, max_delay=300, jitter_factor=0)
        mock_page = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        # First rate limit: 5 -> 10
        await handler.wait_with_backoff(mock_page, detected_rate_limit=True)
        assert handler.current_delay == 10

        # Second rate limit: 10 -> 20
        await handler.wait_with_backoff(mock_page, detected_rate_limit=True)
        assert handler.current_delay == 20

        # Third rate limit: 20 -> 40
        await handler.wait_with_backoff(mock_page, detected_rate_limit=True)
        assert handler.current_delay == 40

        # Fourth rate limit: 40 -> 80
        await handler.wait_with_backoff(mock_page, detected_rate_limit=True)
        assert handler.current_delay == 80


class TestBulkConnectWithRateLimiting:
    """Tests for bulk_connect with rate limiting integration"""

    @pytest.mark.asyncio
    async def test_bulk_connect_uses_rate_limiter(self):
        """Test bulk_connect integrates with rate limiter."""
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/in/test"
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.wait_for_timeout = AsyncMock()

        with patch.object(
            LinkedinOutreach, "connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = True

            results = await LinkedinOutreach.bulk_connect(
                mock_page,
                ["user1", "user2"],
                delay_between_connections=5,
            )

            assert results == {"user1": True, "user2": True}
            assert mock_connect.call_count == 2
            # Should have waited with backoff between connections
            assert mock_page.wait_for_timeout.call_count >= 1

    @pytest.mark.asyncio
    async def test_bulk_connect_stops_on_persistent_rate_limit(self):
        """Test bulk_connect stops when max retries exceeded."""
        mock_page = AsyncMock()
        # Simulate rate limit URL
        mock_page.url = "https://www.linkedin.com/checkpoint/challenge"
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.wait_for_timeout = AsyncMock()

        with patch.object(
            LinkedinOutreach, "connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = False

            results = await LinkedinOutreach.bulk_connect(
                mock_page,
                ["user1", "user2", "user3", "user4", "user5", "user6", "user7"],
                delay_between_connections=1,
                max_retries=2,
            )

            # Should have stopped early due to rate limiting
            # Not all users should be attempted
            assert len(results) == 7
            # Some users should be marked as False without being attempted
            attempted_count = mock_connect.call_count
            assert attempted_count < 7

    @pytest.mark.asyncio
    async def test_bulk_connect_custom_rate_limit_params(self):
        """Test bulk_connect accepts custom rate limit parameters."""
        mock_page = AsyncMock()
        mock_page.url = "https://www.linkedin.com/in/test"
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.wait_for_timeout = AsyncMock()

        with patch.object(
            LinkedinOutreach, "connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = True

            await LinkedinOutreach.bulk_connect(
                mock_page,
                ["user1"],
                delay_between_connections=10,
                max_delay=600,
                max_retries=10,
            )

            # Verify parameters were accepted (no error raised)
            mock_connect.assert_called_once()
