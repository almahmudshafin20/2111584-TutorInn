"""Optional SMTP email notifications for account deletion outcomes."""
import os
import smtplib
import ssl
from email.message import EmailMessage


def send_account_deletion_outcome(
    to_email: str,
    request_id: int,
    role: str,
    method: str,
    *,
    content_action: str | None = None,
    visibility: str | None = None,
    anonymize_content: bool | None = None,
    retained_counts: dict[str, int] | None = None,
    admin_reason: str = "",
) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    if not host or not sender:
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}

    if content_action is None:
        method_label = "anonymized" if method == "anonymize" else "permanently deleted"
        details = (
            f"Your account identity and profile were removed; retained authored content was {method_label}. Eligible shared learning posts may remain with a generic author label.\n"
            if method == "anonymize"
            else "Your account and associated content were permanently removed wherever possible.\n"
        )
    else:
        action_labels = {
            "account_only": "Your account was deleted; eligible content was retained.",
            "retain_all": "Your account was deleted; eligible content was retained.",
            "delete_selected": "The Admin-approved selected content was deleted; other eligible content was retained.",
            "delete_all": "Your account and all removable content in the approved scope were deleted.",
        }
        details = action_labels.get(content_action, "Your account deletion request was approved.")
        if retained_counts:
            retained_total = sum(retained_counts.values())
            details += f" Retained content records: {retained_total}."
        if visibility and content_action in {"account_only", "retain_all", "delete_selected"}:
            details += f" Retained content visibility: {visibility}."
        if anonymize_content is not None and content_action in {"account_only", "retain_all", "delete_selected"}:
            details += (
                " Retained content author identity was anonymized.\n"
                if anonymize_content
                else " Retained content author display details were kept where possible, without an account link.\n"
            )
        else:
            details += "\n"

    message = EmailMessage()
    message["Subject"] = "TutorInn account deletion request outcome"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"Your TutorInn {role} account deletion request (reference #{request_id}) has been approved.\n\n"
        + details
        + (f"\nAdmin explanation for changing your requested deletion scope:\n{admin_reason.strip()}\n" if admin_reason.strip() else "")
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



def send_former_user_content_verification(to_email: str, request_id: int, raw_token: str) -> bool:
    """Email a one-time link; the raw token is never stored in the database."""
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    if not host or not sender:
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}
    base_url = (os.getenv("PUBLIC_APP_URL") or os.getenv("FRONTEND_ORIGIN") or "").strip().rstrip("/")
    if not base_url.startswith("https://"):
        return False
    link = f"{base_url}/former-user-content#token={raw_token}"
    message = EmailMessage()
    message["Subject"] = "TutorInn: review your retained learning content"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"Your TutorInn account deletion (reference #{request_id}) has been completed. "
        "Some learning content was retained according to the approved deletion settings.\n\n"
        "If you want TutorInn to review removal of retained items, open this one-time verification link "
        f"within 48 hours:\n{link}\n\n"
        "The link can be used once. If you did not request this, you can ignore this email."
    )
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls(context=context)
        if username:
            server.login(username, password)
        server.send_message(message)
    return True



def send_former_user_content_removal_outcome(
    to_email: str,
    request_id: int,
    status: str,
    review_note: str = "",
) -> bool:
    """Notify a former user after Admin reviews a retained-content removal request."""
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    if not host or not sender:
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes"}
    approved = status == "approved"
    message = EmailMessage()
    message["Subject"] = "TutorInn: retained-content request reviewed"
    message["From"] = sender
    message["To"] = to_email
    outcome = (
        "The Admin approved your request. The selected retained learning content has been removed where eligible."
        if approved else
        "The Admin could not approve your request. Your retained content has not been removed."
    )
    note = f"\n\nAdmin note: {review_note.strip()}" if review_note.strip() else ""
    message.set_content(
        f"Your TutorInn retained-content removal request (reference #{request_id}) has been reviewed.\n\n"
        + outcome + note
        + "\n\nThis is an automated notice; please do not reply."
    )
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=15) as server:
        if use_tls:
            server.starttls(context=context)
        if username:
            server.login(username, password)
        server.send_message(message)
    return True
