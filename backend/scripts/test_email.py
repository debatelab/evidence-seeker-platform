#!/usr/bin/env python3
"""
Simple script to verify email service functionality.
Run this script to test email sending without starting the full application.
"""

import asyncio
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from app.core.config import settings
from app.core.email_service import EmailService


async def main() -> None:
    """Test the email service functionality"""
    print("Testing Email Service...")
    print(f"SMTP Server: {settings.smtp_server}")
    print(f"SMTP Port: {settings.smtp_port}")
    print(f"Email From: {settings.email_from}")
    print(f"Templates Dir: {settings.email_templates_dir}")

    # Initialize email service
    email_service = EmailService()

    # Test data
    test_email = "test@example.com"
    test_token = "test-verification-token-12345"

    try:
        # Test verification email
        print("\nSending verification email...")
        await email_service.send_verification_email(test_email, test_token)
        print("✅ Verification email sent successfully!")

        # Test password reset email
        print("\nSending password reset email...")
        await email_service.send_password_reset_email(test_email, test_token)
        print("✅ Password reset email sent successfully!")

        print("\n🎉 All email tests passed!")

    except Exception as e:
        print(f"❌ Email test failed: {e}")
        print("Note: This might be expected if SMTP credentials are not configured.")
        print(
            "Make sure to set SMTP_USERNAME and SMTP_PASSWORD in your environment variables."
        )


if __name__ == "__main__":
    asyncio.run(main())
