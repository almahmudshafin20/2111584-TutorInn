"""Optional SMTP email notifications for account deletion outcomes."""
import os
import smtplib
import ssl
from email.message import EmailMessage


def send_account_deletion_outcome(to_email: str, request_id: int, role: str, method: str) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    if not host or not sender:
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}
    method_label = "anonymized" if method == "anonymize" else "permanently deleted"
    message = EmailMessage()
    message["Subject"] = "TutorInn account deletion request outcome"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"Your TutorInn {role} account deletion request (reference #{request_id}) has been approved.\n\n"
        f"The Admin selected: {method_label}.\n"
        + ("Your account identity and profile were removed. Eligible shared learning posts may remain with a generic author label.\n"
           if method == "anonymize" else
           "Your account and associated content were permanently removed wherever possible.\n")
        + "\nThis is an automated notice; please do not reply."
    )
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls(context=context)
        if username:
            server.login(username, password)
        server.send_message(message)
    return True
