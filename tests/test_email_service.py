import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from fastapi_mail.errors import ConnectionErrors

from src.services.email import EmailService, send_email, send_password_reset_email


@pytest.fixture
def email_service():
    return EmailService()


@pytest.fixture
def mock_fastmail():
    return AsyncMock()


class TestEmailService:

    def test_email_service_initialization(self, email_service):
        assert email_service is not None
        assert email_service.config is not None

    def test_create_config(self, email_service):
        config = email_service._create_config()

        assert config is not None
        assert hasattr(config, "MAIL_USERNAME")
        assert hasattr(config, "MAIL_FROM")
        assert hasattr(config, "MAIL_PORT")
        assert hasattr(config, "MAIL_SERVER")

    @pytest.mark.asyncio
    async def test_send_verification_email_success(self, email_service):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch("src.services.email.FastMail") as mock_fastmail_class:
            mock_fastmail = AsyncMock()
            mock_fastmail_class.return_value = mock_fastmail
            mock_fastmail.send_message = AsyncMock()

            result = await email_service.send_verification_email(email, username, host)

            assert result is True
            mock_fastmail.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_verification_email_connection_error(self, email_service):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch("src.services.email.FastMail") as mock_fastmail_class:
            mock_fastmail = AsyncMock()
            mock_fastmail_class.return_value = mock_fastmail
            mock_fastmail.send_message.side_effect = ConnectionErrors(
                "Connection failed"
            )

            result = await email_service.send_verification_email(email, username, host)

            assert result is False

    @pytest.mark.asyncio
    async def test_send_verification_email_unexpected_error(self, email_service):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch("src.services.email.FastMail") as mock_fastmail_class:
            mock_fastmail = AsyncMock()
            mock_fastmail_class.return_value = mock_fastmail
            mock_fastmail.send_message.side_effect = Exception("Unexpected error")

            result = await email_service.send_verification_email(email, username, host)

            assert result is False

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(self, email_service):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch("src.services.email.FastMail") as mock_fastmail_class:
            mock_fastmail = AsyncMock()
            mock_fastmail_class.return_value = mock_fastmail
            mock_fastmail.send_message = AsyncMock()

            result = await email_service.send_password_reset_email(
                email, username, host
            )

            assert result is True
            mock_fastmail.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_password_reset_email_connection_error(self, email_service):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch("src.services.email.FastMail") as mock_fastmail_class:
            mock_fastmail = AsyncMock()
            mock_fastmail_class.return_value = mock_fastmail
            mock_fastmail.send_message.side_effect = ConnectionErrors(
                "Connection failed"
            )

            result = await email_service.send_password_reset_email(
                email, username, host
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_password_reset_email_unexpected_error(self, email_service):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch("src.services.email.FastMail") as mock_fastmail_class:
            mock_fastmail = AsyncMock()
            mock_fastmail_class.return_value = mock_fastmail
            mock_fastmail.send_message.side_effect = Exception("Unexpected error")

            result = await email_service.send_password_reset_email(
                email, username, host
            )

            assert result is False


class TestEmailConvenienceFunctions:

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch(
            "src.services.email.email_service.send_verification_email"
        ) as mock_send:
            mock_send.return_value = True

            await send_email(email, username, host)

            mock_send.assert_called_once_with(email, username, host)

    @pytest.mark.asyncio
    async def test_send_email_failure(self):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch(
            "src.services.email.email_service.send_verification_email"
        ) as mock_send:
            mock_send.return_value = False

            with pytest.raises(Exception) as exc_info:
                await send_email(email, username, host)

            assert "Failed to send verification email" in str(exc_info.value)
            mock_send.assert_called_once_with(email, username, host)

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(self):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch(
            "src.services.email.email_service.send_password_reset_email"
        ) as mock_send:
            mock_send.return_value = True

            await send_password_reset_email(email, username, host)

            mock_send.assert_called_once_with(email, username, host)

    @pytest.mark.asyncio
    async def test_send_password_reset_email_failure(self):
        email = "test@example.com"
        username = "testuser"
        host = "http://localhost:8000"

        with patch(
            "src.services.email.email_service.send_password_reset_email"
        ) as mock_send:
            mock_send.return_value = False

            with pytest.raises(Exception) as exc_info:
                await send_password_reset_email(email, username, host)

            assert "Failed to send password reset email" in str(exc_info.value)
            mock_send.assert_called_once_with(email, username, host)
