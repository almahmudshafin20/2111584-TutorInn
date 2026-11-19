"""Minimal SMTP adapter for account security emails."""

import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode, urlparse


def send_password_reset_email(to_email: str, raw_token: str) -> str:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", "").strip()
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if not all((host, username, password, sender, frontend_url)):
        return "not_configured"
    parsed_frontend = urlparse(frontend_url)
    if parsed_frontend.scheme not in {"https", "http"} or not parsed_frontend.netloc:
        return "not_configured"
    if parsed_frontend.scheme == "http" and parsed_frontend.hostname not in {"localhost", "127.0.0.1"}:
        return "not_configured"

    query = urlencode({"token": raw_token})
    reset_url = f"{frontend_url}/reset-password#{query}"
    message = EmailMessage()
    message["Subject"] = "Reset your TutorInn password"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        "A password reset was approved for your TutorInn account. "
        "Use the secure, single-use link below within 30 minutes. "
        "If you did not request this change, you can ignore this email.\n\n"
        f"{reset_url}\n"
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    timeout = min(max(int(os.getenv("SMTP_TIMEOUT_SECONDS", "10")), 3), 30)
    use_ssl = os.getenv("SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes"}
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except Exception:
        return "failed"
    return "sent"


def send_email_verification_email(to_email: str, raw_token: str) -> str:
    """Send a single-use email ownership confirmation link."""
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM", "").strip()
    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if not all((host, username, password, sender, frontend_url)):
        return "not_configured"
    parsed_frontend = urlparse(frontend_url)
    if parsed_frontend.scheme not in {"https", "http"} or not parsed_frontend.netloc:
        return "not_configured"
    if parsed_frontend.scheme == "http" and parsed_frontend.hostname not in {"localhost", "127.0.0.1"}:
        return "not_configured"

    query = urlencode({"token": raw_token})
    verify_url = f"{frontend_url}/verify-email#{query}"
    message = EmailMessage()
    message["Subject"] = "Verify your TutorInn email address"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        "Confirm that this email address belongs to your TutorInn account. "
        "This single-use link expires in 30 minutes. If you did not create "
        "a TutorInn account, you can ignore this email.\n\n"
        f"{verify_url}\n"
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    timeout = min(max(int(os.getenv("SMTP_TIMEOUT_SECONDS", "10")), 3), 30)
    use_ssl = os.getenv("SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes"}
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except Exception:
        return "failed"
    return "sent"
