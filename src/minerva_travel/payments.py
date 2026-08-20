from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx


class MercadoPagoError(RuntimeError):
    """Safe provider error that never includes credentials or response bodies."""


@dataclass(frozen=True)
class MercadoPagoPreference:
    id: str
    checkout_url: str


@dataclass(frozen=True)
class MercadoPagoPayment:
    id: str
    status: str
    external_reference: str
    amount_minor: int
    currency: str


class MercadoPagoClient:
    def __init__(
        self,
        *,
        access_token: str,
        api_base_url: str = "https://api.mercadopago.com",
        environment: str = "test",
        timeout_seconds: float = 15.0,
    ) -> None:
        if not access_token:
            raise MercadoPagoError("A integração do Mercado Pago não está configurada.")
        self._access_token = access_token
        self._api_base_url = api_base_url.rstrip("/")
        self._environment = environment
        self._timeout_seconds = timeout_seconds

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def create_preference(
        self,
        *,
        local_payment_id: str,
        idempotency_key: str,
        title: str,
        amount_minor: int,
        currency: str,
        payer_email: str | None,
        success_url: str,
        pending_url: str,
        failure_url: str,
        notification_url: str | None,
    ) -> MercadoPagoPreference:
        payload: dict[str, Any] = {
            "items": [
                {
                    "id": local_payment_id,
                    "title": title,
                    "quantity": 1,
                    "currency_id": currency,
                    "unit_price": float(Decimal(amount_minor) / Decimal(100)),
                }
            ],
            "external_reference": local_payment_id,
            "back_urls": {
                "success": success_url,
                "pending": pending_url,
                "failure": failure_url,
            },
            "auto_return": "approved",
        }
        if payer_email:
            payload["payer"] = {"email": payer_email}
        if notification_url:
            payload["notification_url"] = notification_url

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(
                    f"{self._api_base_url}/checkout/preferences",
                    headers={**self._headers, "X-Idempotency-Key": idempotency_key},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise MercadoPagoError(
                "Não foi possível iniciar o checkout no Mercado Pago."
            ) from error

        preference_id = str(body.get("id") or "").strip()
        url_key = "sandbox_init_point" if self._environment == "test" else "init_point"
        checkout_url = str(body.get(url_key) or "").strip()
        if not preference_id or not checkout_url.startswith("https://"):
            raise MercadoPagoError("O Mercado Pago retornou um checkout inválido.")
        return MercadoPagoPreference(id=preference_id, checkout_url=checkout_url)

    def get_payment(self, provider_payment_id: str) -> MercadoPagoPayment:
        if not provider_payment_id.isdigit():
            raise MercadoPagoError("Identificador de pagamento inválido.")
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.get(
                    f"{self._api_base_url}/v1/payments/{provider_payment_id}",
                    headers=self._headers,
                )
                response.raise_for_status()
                body = response.json()
            amount_minor = int(
                (Decimal(str(body.get("transaction_amount"))) * Decimal(100)).quantize(Decimal("1"))
            )
        except (httpx.HTTPError, ValueError, ArithmeticError) as error:
            raise MercadoPagoError(
                "Não foi possível confirmar o pagamento no Mercado Pago."
            ) from error

        payment_id = str(body.get("id") or "").strip()
        status = str(body.get("status") or "").strip().lower()
        external_reference = str(body.get("external_reference") or "").strip()
        currency = str(body.get("currency_id") or "").strip().upper()
        if not payment_id or not status or not external_reference or len(currency) != 3:
            raise MercadoPagoError("O Mercado Pago retornou dados de pagamento inválidos.")
        return MercadoPagoPayment(
            id=payment_id,
            status=status,
            external_reference=external_reference,
            amount_minor=amount_minor,
            currency=currency,
        )


def verify_mercado_pago_signature(
    *,
    secret: str,
    signature_header: str,
    request_id: str,
    data_id: str,
) -> bool:
    if not secret or not signature_header or not request_id or not data_id:
        return False
    parts: dict[str, str] = {}
    for raw_part in signature_header.split(","):
        key, separator, value = raw_part.strip().partition("=")
        if separator and key and value:
            parts[key] = value
    timestamp = parts.get("ts", "")
    received = parts.get("v1", "")
    if not timestamp.isdigit() or len(received) != 64:
        return False
    manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{timestamp};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received.lower())


def local_payment_status(provider_status: str) -> str:
    return {
        "approved": "paid",
        "authorized": "authorized",
        "pending": "pending",
        "in_process": "pending",
        "in_mediation": "pending",
        "rejected": "failed",
        "cancelled": "cancelled",
        "refunded": "refunded",
        "charged_back": "refunded",
    }.get(provider_status.lower(), "pending")
