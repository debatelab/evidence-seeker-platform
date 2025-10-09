from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from app.core.config import settings


class EmailService:
    def __init__(self) -> None:
        self.config = ConnectionConfig(
            MAIL_USERNAME=settings.smtp_username,
            MAIL_PASSWORD=settings.smtp_password,
            MAIL_FROM=settings.email_from,
            MAIL_PORT=settings.smtp_port,
            MAIL_SERVER=settings.smtp_server,
            MAIL_FROM_NAME=settings.email_from_name,
            MAIL_SSL_TLS=False,  # Added missing parameter
            MAIL_STARTTLS=True,
            USE_CREDENTIALS=True,
            TEMPLATE_FOLDER=Path(settings.email_templates_dir),
        )
        self.fast_mail = FastMail(self.config)

    async def send_verification_email(self, email: EmailStr, token: str) -> None:
        """Send email verification link"""
        message = MessageSchema(
            subject="Verify your Evidence Seeker Platform account",
            recipients=[email],
            template_body={
                "token": token,
                "email": email,
            },
            subtype=MessageType.html,
        )

        await self.fast_mail.send_message(message, template_name="verify_email.html")

    async def send_password_reset_email(self, email: EmailStr, token: str) -> None:
        """Send password reset email"""
        message = MessageSchema(
            subject="Reset your Evidence Seeker Platform password",
            recipients=[email],
            template_body={
                "token": token,
                "email": email,
            },
            subtype=MessageType.html,
        )

        await self.fast_mail.send_message(message, template_name="reset_password.html")
