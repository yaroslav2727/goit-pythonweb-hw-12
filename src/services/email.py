from pathlib import Path
import logging
from typing import Optional

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr, SecretStr

from src.services.auth import create_email_token, create_password_reset_token
from src.conf.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailService:
    """Service class for email operations.

    Handles sending various types of emails including verification emails
    and password reset emails using FastMail.

    Attributes:
        config (ConnectionConfig): FastMail connection configuration.
    """

    def __init__(self):
        """Initialize EmailService with mail configuration."""
        self.config = self._create_config()

    def _create_config(self) -> ConnectionConfig:
        """Create FastMail connection configuration.

        Returns:
            ConnectionConfig: Configuration object for FastMail connection.
        """
        return ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=settings.USE_CREDENTIALS,
            VALIDATE_CERTS=settings.VALIDATE_CERTS,
            TEMPLATE_FOLDER=Path(__file__).parent / "templates",
        )

    async def send_verification_email(
        self, email: EmailStr, username: str, host: str
    ) -> bool:
        """Send email verification message to user.

        Sends an HTML email with a verification link to confirm the user's
        email address. Uses the verify_email.html template.

        Args:
            email (EmailStr): The recipient's email address.
            username (str): The user's username for personalization.
            host (str): The application host URL for building verification link.

        Returns:
            bool: True if email was sent successfully, False otherwise.
        """
        try:
            token_verification = create_email_token({"sub": email})
            message = MessageSchema(
                subject="Confirm your email - Contacts API",
                recipients=[email],
                template_body={
                    "host": host,
                    "username": username,
                    "token": token_verification,
                },
                subtype=MessageType.html,
            )

            fm = FastMail(self.config)
            await fm.send_message(message, template_name="verify_email.html")
            logger.info(f"Email successfully sent to {email}")
            return True

        except ConnectionErrors as err:
            logger.error(f"SMTP Connection error for {email}: {err}")
            return False
        except Exception as err:
            logger.error(f"Unexpected error sending email to {email}: {err}")
            return False

    async def send_password_reset_email(
        self, email: EmailStr, username: str, host: str
    ) -> bool:
        """Send password reset email to user.

        Sends an HTML email with a password reset link allowing the user
        to reset their password. Uses the password_reset_email.html template.

        Args:
            email (EmailStr): The recipient's email address.
            username (str): The user's username for personalization.
            host (str): The application host URL for building reset link.

        Returns:
            bool: True if email was sent successfully, False otherwise.
        """
        try:
            token_reset = create_password_reset_token({"sub": email})
            message = MessageSchema(
                subject="Password Reset - Contacts API",
                recipients=[email],
                template_body={
                    "host": host,
                    "username": username,
                    "email": email,
                    "token": token_reset,
                },
                subtype=MessageType.html,
            )

            fm = FastMail(self.config)
            await fm.send_message(message, template_name="password_reset_email.html")
            logger.info(f"Password reset email successfully sent to {email}")
            return True

        except ConnectionErrors as err:
            logger.error(f"SMTP Connection error for password reset {email}: {err}")
            return False
        except Exception as err:
            logger.error(
                f"Unexpected error sending password reset email to {email}: {err}"
            )
            return False


email_service = EmailService()


async def send_email(email: EmailStr, username: str, host: str):
    """Send verification email to user.

    Convenience function that uses the global email service instance
    to send verification emails.

    Args:
        email (EmailStr): The recipient's email address.
        username (str): The user's username for personalization.
        host (str): The application host URL for building verification link.

    Raises:
        Exception: If email sending fails.
    """
    success = await email_service.send_verification_email(email, username, host)
    if not success:
        raise Exception(f"Failed to send verification email to {email}")


async def send_password_reset_email(email: EmailStr, username: str, host: str):
    """Send password reset email to user.

    Convenience function that uses the global email service instance
    to send password reset emails.

    Args:
        email (EmailStr): The recipient's email address.
        username (str): The user's username for personalization.
        host (str): The application host URL for building reset link.

    Raises:
        Exception: If email sending fails.
    """
    success = await email_service.send_password_reset_email(email, username, host)
    if not success:
        raise Exception(f"Failed to send password reset email to {email}")
