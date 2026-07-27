"""O aviso de guia pronto: sai quando dá, e nunca derruba a entrega."""

import smtplib

import pytest

from minerva_travel.email_delivery import (
    SmtpSettings,
    guide_ready_message,
    send_guide_ready_email,
    smtp_settings,
)


def _settings(**overrides) -> SmtpSettings:
    values = {
        "host": "smtp.example.test",
        "port": 587,
        "username": "guias@minerva.test",
        "password": "segredo",
        "sender": "guias@minerva.test",
        "use_starttls": True,
    }
    values.update(overrides)
    return SmtpSettings(**values)


class FakeSmtp:
    """Servidor SMTP de mentira que registra o que aconteceu."""

    instances: list["FakeSmtp"] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in_as = None
        self.sent = []
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, username, password):
        self.logged_in_as = username

    def send_message(self, message):
        self.sent.append(message)


class BrokenSmtp(FakeSmtp):
    def send_message(self, message):
        raise smtplib.SMTPRecipientsRefused({"a@b.test": (550, b"no")})


@pytest.fixture(autouse=True)
def _reset():
    FakeSmtp.instances = []
    yield
    FakeSmtp.instances = []


def test_the_email_carries_the_link_and_never_the_pdf():
    message = guide_ready_message(
        recipient="familia@example.test",
        family_title="Família Lima",
        guide_url="https://minerva.test/create?builder=abc",
        page_count=12,
        sender="guias@minerva.test",
    )

    assert message["To"] == "familia@example.test"
    assert "Família Lima" in message["Subject"]
    body = message.get_content()
    assert "https://minerva.test/create?builder=abc" in body
    assert "12 páginas" in body
    # Anexar 40 MB faria o servidor recusar; o guia vai por link.
    assert not message.is_multipart()
    assert message.get_payload(decode=False)


def test_one_page_is_not_pluralised():
    body = guide_ready_message(
        recipient="a@b.test",
        family_title="Família Lima",
        guide_url="https://x/y",
        page_count=1,
        sender="s@t.test",
    ).get_content()

    assert "1 página" in body
    assert "1 páginas" not in body


def test_a_configured_server_receives_the_message(monkeypatch):
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://127.0.0.1:3000")

    sent = send_guide_ready_email(
        recipient="familia@example.test",
        family_title="Família Lima",
        session_id="abc123",
        page_count=9,
        settings=_settings(),
        transport=FakeSmtp,
    )

    assert sent is True
    server = FakeSmtp.instances[-1]
    assert server.started_tls is True
    assert server.logged_in_as == "guias@minerva.test"
    assert "abc123" in server.sent[0].get_content()


def test_nothing_is_sent_and_nothing_breaks_without_smtp_configured():
    # É o estado do projeto hoje: sem SMTP, o guia continua no download.
    assert (
        send_guide_ready_email(
            recipient="familia@example.test",
            family_title="Família Lima",
            session_id="abc123",
            page_count=9,
            settings=_settings(host="", sender=""),
            transport=FakeSmtp,
        )
        is False
    )
    assert FakeSmtp.instances == []


def test_an_account_without_an_address_is_skipped_quietly():
    assert (
        send_guide_ready_email(
            recipient="",
            family_title="Família Lima",
            session_id="abc123",
            page_count=9,
            settings=_settings(),
            transport=FakeSmtp,
        )
        is False
    )
    assert FakeSmtp.instances == []


def test_a_refused_recipient_never_takes_the_guide_down(monkeypatch):
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://127.0.0.1:3000")

    # O PDF já existe quando o envio acontece; estourar aqui tiraria da
    # família um guia que está pronto.
    assert (
        send_guide_ready_email(
            recipient="familia@example.test",
            family_title="Família Lima",
            session_id="abc123",
            page_count=9,
            settings=_settings(),
            transport=BrokenSmtp,
        )
        is False
    )


def test_starttls_can_be_switched_off_for_servers_that_reject_it(monkeypatch):
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://127.0.0.1:3000")

    send_guide_ready_email(
        recipient="familia@example.test",
        family_title="Família Lima",
        session_id="abc123",
        page_count=9,
        settings=_settings(use_starttls=False, username=""),
        transport=FakeSmtp,
    )

    server = FakeSmtp.instances[-1]
    assert server.started_tls is False
    assert server.logged_in_as is None


def test_settings_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.hostinger.test")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_FROM", "guias@minerva.test")
    monkeypatch.setenv("SMTP_STARTTLS", "false")

    settings = smtp_settings()

    assert settings.host == "smtp.hostinger.test"
    assert settings.port == 465
    assert settings.use_starttls is False
    assert settings.configured is True
