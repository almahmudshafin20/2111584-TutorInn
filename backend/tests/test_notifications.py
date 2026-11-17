from app import notifications


def test_account_deletion_notice_returns_false_without_smtp_configuration(monkeypatch):
    for name in ("SMTP_HOST", "SMTP_FROM"):
        monkeypatch.delenv(name, raising=False)
    assert notifications.send_account_deletion_outcome("student@example.com", 42, "student", "anonymize") is False


def test_account_deletion_notice_sends_admin_selected_method(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["connection"] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self, context):
            sent["tls"] = context is not None

        def login(self, username, password):
            sent["login"] = (username, password)

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setenv("SMTP_HOST", "mail.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "mailer")
    monkeypatch.setenv("SMTP_PASSWORD", "test-secret")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.com")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setattr(notifications.smtplib, "SMTP", FakeSMTP)

    assert notifications.send_account_deletion_outcome("student@example.com", 42, "student", "anonymize") is True
    assert sent["connection"] == ("mail.example.com", 587, 15)
    assert sent["tls"] is True
    assert sent["message"]["To"] == "student@example.com"
    assert "anonymized" in sent["message"].get_content()


def test_account_deletion_notice_describes_final_content_decision(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self, context):
            pass

        def send_message(self, message):
            sent["message"] = message

    monkeypatch.setenv("SMTP_HOST", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.com")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setattr(notifications.smtplib, "SMTP", FakeSMTP)

    assert notifications.send_account_deletion_outcome(
        "student@example.com", 43, "student", "complete",
        content_action="delete_selected", visibility="hidden",
        anonymize_content=True, retained_counts={"learning_post": 1, "personal_task": 2},
    ) is True
    body = sent["message"].get_content()
    assert "selected content was deleted" in body
    assert "Retained content records: 3" in body
    assert "visibility: hidden" in body
    assert "anonymized" in body


def test_former_user_review_outcome_notice_reports_approval_and_rejection(monkeypatch):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def starttls(self, context):
            pass

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setenv("SMTP_HOST", "mail.example.com")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.com")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setattr(notifications.smtplib, "SMTP", FakeSMTP)

    assert notifications.send_former_user_content_removal_outcome(
        "former@example.com", 51, "approved", "Removed the selected post.",
    ) is True
    assert notifications.send_former_user_content_removal_outcome(
        "former@example.com", 52, "rejected", "The item is shared with a group.",
    ) is True
    assert sent[0]["To"] == "former@example.com"
    assert "approved" in sent[0].get_content()
    assert "not been removed" in sent[1].get_content()
    assert "shared with a group" in sent[1].get_content()


def test_former_user_review_notice_returns_false_without_smtp(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    assert notifications.send_former_user_content_removal_outcome(
        "former@example.com", 53, "approved",
    ) is False
