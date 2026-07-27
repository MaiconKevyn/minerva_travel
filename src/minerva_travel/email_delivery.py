"""Aviso por e-mail de que o guia ficou pronto, com o link de download.

O PDF não vai anexado de propósito: uma página aprovada tem cerca de 3 MB, e
um guia de quinze páginas passa de 40 MB — acima do limite de anexo de
praticamente todo provedor. Um e-mail recusado pelo servidor é pior do que um
e-mail com link, porque a família nem fica sabendo.

O link aponta para a aplicação, não para um endpoint público: o download
continua exigindo a sessão do dono. Assim não inventamos uma URL assinada
sem autenticação só para caber num e-mail.

Sem SMTP configurado nada é enviado e nada quebra — o guia continua
disponível para baixar na tela.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from minerva_travel.config import frontend_base_url, load_project_env
from minerva_travel.observability import emit_event


class EmailDeliveryError(RuntimeError):
    """O envio falhou. Nunca derruba a geração do guia."""


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    username: str
    password: str
    sender: str
    use_starttls: bool

    @property
    def configured(self) -> bool:
        return bool(self.host and self.sender)


def smtp_settings() -> SmtpSettings:
    load_project_env()
    return SmtpSettings(
        host=os.getenv("SMTP_HOST", "").strip(),
        port=int(os.getenv("SMTP_PORT", "587") or 587),
        username=os.getenv("SMTP_USERNAME", "").strip(),
        password=os.getenv("SMTP_PASSWORD", ""),
        sender=os.getenv("SMTP_FROM", "").strip(),
        use_starttls=os.getenv("SMTP_STARTTLS", "true").strip().lower() != "false",
    )


def guide_ready_message(
    *,
    recipient: str,
    family_title: str,
    guide_url: str,
    page_count: int,
    sender: str,
) -> EmailMessage:
    """O texto que a família recebe. Curto: o que ficou pronto e onde pegar."""

    pages = "página" if page_count == 1 else "páginas"
    message = EmailMessage()
    message["Subject"] = f"O guia da {family_title} está pronto"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"""Olá!

O guia de viagem da {family_title} terminou de ser montado, com {page_count} {pages}
ilustradas — capa, roteiro, os pontos turísticos e as atividades que vocês escolheram.

Baixe o PDF aqui:
{guide_url}

É um arquivo A4, pronto para imprimir em casa ou levar a uma gráfica.
O link abre na sua conta, então mantenha a sessão iniciada.

Boa viagem!
Minerva Travel
"""
    )
    return message


def guide_download_url(session_id: str) -> str:
    """A página da aplicação onde o guia fica disponível para o dono."""

    return f"{frontend_base_url()}/create?builder={session_id}"


def send_guide_ready_email(
    *,
    recipient: str,
    family_title: str,
    session_id: str,
    page_count: int,
    settings: SmtpSettings | None = None,
    transport: type[smtplib.SMTP] | None = None,
) -> bool:
    """Devolve ``True`` quando o e-mail saiu. Falha vira log, nunca exceção.

    Quem chama já entregou o PDF; derrubar a resposta porque o servidor de
    e-mail está fora tiraria da família um guia que existe e está pronto.
    """

    resolved = settings or smtp_settings()
    if not resolved.configured:
        return False
    if not (recipient or "").strip():
        return False

    message = guide_ready_message(
        recipient=recipient,
        family_title=family_title,
        guide_url=guide_download_url(session_id),
        page_count=page_count,
        sender=resolved.sender,
    )
    client_class = transport or smtplib.SMTP
    try:
        with client_class(resolved.host, resolved.port, timeout=20) as client:
            if resolved.use_starttls:
                client.starttls(context=ssl.create_default_context())
            if resolved.username:
                client.login(resolved.username, resolved.password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        # O endereço nunca entra no log; só o tipo da falha.
        emit_event(
            "guide_email_failed",
            outcome="failed",
            error_code=type(error).__name__,
        )
        return False
    emit_event("guide_email_sent", outcome="succeeded")
    return True
