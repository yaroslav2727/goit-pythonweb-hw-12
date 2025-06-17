from pathlib import Path
import logging
from typing import Optional

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr, SecretStr

from src.services.auth import create_email_token
from src.conf.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailService:

    def __init__(self):
        self.config = self._create_config()

    def _create_config(self) -> ConnectionConfig:
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


email_service = EmailService()


async def send_email(email: EmailStr, username: str, host: str):
    success = await email_service.send_verification_email(email, username, host)
    if not success:
        raise Exception(f"Failed to send verification email to {email}")
