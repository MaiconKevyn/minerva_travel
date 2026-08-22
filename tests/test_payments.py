import hashlib
import hmac

from fastapi.testclient import TestClient

from minerva_travel.app import app
from minerva_travel.auth import (
    GUIDE_PAYMENT_BYPASS_PERMISSION,
    AuthenticatedUser,
    get_current_user,
)
from minerva_travel.builder import BuilderPage, create_builder_session
from minerva_travel.payments import MercadoPagoPayment, MercadoPagoPreference
from minerva_travel.persistence import GuideRepository


class FakeMercadoPagoClient:
    preference_calls: list[dict] = []
    provider_payment: MercadoPagoPayment | None = None

    def __init__(self, **_kwargs) -> None:
        pass

    def create_preference(self, **kwargs) -> MercadoPagoPreference:
        self.preference_calls.append(kwargs)
        return MercadoPagoPreference(
            id="preference-test-1",
            checkout_url="https://sandbox.mercadopago.com.br/checkout/v1/redirect",
        )

    def get_payment(self, _provider_payment_id: str) -> MercadoPagoPayment:
        assert self.provider_payment is not None
        return self.provider_payment


def _owner() -> AuthenticatedUser:
    return AuthenticatedUser(id="owner-payment", email="familia@example.com")


def _complimentary_owner() -> AuthenticatedUser:
    return AuthenticatedUser(
        id="owner-complimentary",
        email="equipe@example.com",
        permissions=frozenset({GUIDE_PAYMENT_BYPASS_PERMISSION}),
    )


def _setup_payment_environment(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.MercadoPagoClient", FakeMercadoPagoClient)
    monkeypatch.setenv("PAYMENTS_ENABLED", "true")
    monkeypatch.setenv("MERCADO_PAGO_ACCESS_TOKEN", "test-token-not-secret")
    monkeypatch.setenv("MERCADO_PAGO_WEBHOOK_SECRET", "webhook-test-secret")
    monkeypatch.setenv("MERCADO_PAGO_ENVIRONMENT", "test")
    monkeypatch.setenv("GUIDE_PRODUCT_PRICE_MINOR", "100")
    monkeypatch.setenv("GUIDE_PRODUCT_CURRENCY", "BRL")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://127.0.0.1:3000")
    app.dependency_overrides[get_current_user] = _owner
    FakeMercadoPagoClient.preference_calls = []
    FakeMercadoPagoClient.provider_payment = None
    return TestClient(app)


def _builder_session_id(owner: AuthenticatedUser | None = None) -> str:
    active_owner = owner or _owner()
    session = create_builder_session(
        owner_id=active_owner.id,
        form={"title": "Família Teste"},
        photo_path=None,
        privacy_consent=None,
        pages=[
            BuilderPage(
                id="cover",
                kind="cover",
                title="Capa",
                position=0,
                required_copy=["Família Teste"],
            )
        ],
    )
    return session.id


def test_product_access_is_user_specific_and_complimentary_access_skips_checkout(
    monkeypatch,
    tmp_path,
):
    client = _setup_payment_environment(monkeypatch, tmp_path)
    try:
        ordinary = client.get("/api/products/guide/access")
        assert ordinary.status_code == 200
        assert ordinary.json() == {"payment_required": True, "access_mode": "payment"}

        app.dependency_overrides[get_current_user] = _complimentary_owner
        session_id = _builder_session_id(_complimentary_owner())
        access = client.get("/api/products/guide/access")
        assert access.status_code == 200
        assert access.json() == {
            "payment_required": False,
            "access_mode": "complimentary",
        }

        checkout = client.post(
            "/api/payments/checkout",
            headers={"Idempotency-Key": "must-not-charge"},
            json={"builder_session_id": session_id},
        )
        assert checkout.status_code == 409
        assert checkout.json()["detail"]["code"] == "guide_complimentary_access"
        assert FakeMercadoPagoClient.preference_calls == []

        incomplete = client.post(f"/api/guide-builder/{session_id}/complete")
        assert incomplete.status_code == 409
        assert incomplete.json()["detail"]["code"] == "builder_incomplete"

        repository = GuideRepository(tmp_path / "minerva.sqlite3")
        assert repository.has_complimentary_builder_access(
            user_id=_complimentary_owner().id,
            builder_session_id=session_id,
        )
        # Durable workers only receive the owner/session ids. The persisted
        # grant must therefore remain claimable without the original JWT.
        assert repository.claim_builder_entitlement(
            user_id=_complimentary_owner().id,
            builder_session_id=session_id,
        )
        assert repository.claim_builder_entitlement(
            user_id=_complimentary_owner().id,
            builder_session_id=session_id,
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def _signature(secret: str, request_id: str, data_id: str, timestamp: str = "1787189000") -> str:
    manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{timestamp};"
    digest = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return f"ts={timestamp},v1={digest}"


def test_checkout_uses_server_price_and_reuses_pending_payment(monkeypatch, tmp_path):
    client = _setup_payment_environment(monkeypatch, tmp_path)
    try:
        session_id = _builder_session_id()
        first = client.post(
            "/api/payments/checkout",
            headers={"Idempotency-Key": "checkout-one"},
            json={"builder_session_id": session_id, "amount_minor": 1_000_000},
        )
        assert first.status_code == 422  # strict request rejects a browser-supplied amount

        first = client.post(
            "/api/payments/checkout",
            headers={"Idempotency-Key": "checkout-one"},
            json={"builder_session_id": session_id},
        )
        assert first.status_code == 200, first.text
        assert first.json()["amount_minor"] == 100
        assert first.json()["status"] == "pending"
        assert first.json()["checkout_url"].startswith("https://sandbox.mercadopago.com.br/")

        replay = client.post(
            "/api/payments/checkout",
            headers={"Idempotency-Key": "checkout-two"},
            json={"builder_session_id": session_id},
        )
        assert replay.status_code == 200
        assert replay.json()["payment_id"] == first.json()["payment_id"]
        assert len(FakeMercadoPagoClient.preference_calls) == 1
        assert FakeMercadoPagoClient.preference_calls[0]["amount_minor"] == 100
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_signed_webhook_issues_one_entitlement_and_unlocks_builder(monkeypatch, tmp_path):
    client = _setup_payment_environment(monkeypatch, tmp_path)
    try:
        session_id = _builder_session_id()
        checkout = client.post(
            "/api/payments/checkout",
            headers={"Idempotency-Key": "checkout-webhook"},
            json={"builder_session_id": session_id},
        )
        payment_id = checkout.json()["payment_id"]

        blocked = client.post(
            f"/api/guide-builder/{session_id}/pages/cover/attempts",
            headers={"Idempotency-Key": "cover-before-payment"},
            json={},
        )
        assert blocked.status_code == 402
        assert blocked.json()["detail"]["code"] == "guide_payment_required"

        FakeMercadoPagoClient.provider_payment = MercadoPagoPayment(
            id="123456789",
            status="approved",
            external_reference=payment_id,
            amount_minor=100,
            currency="BRL",
        )
        request_id = "provider-request-1"
        headers = {
            "x-request-id": request_id,
            "x-signature": _signature(
                "webhook-test-secret", request_id, FakeMercadoPagoClient.provider_payment.id
            ),
        }
        for _ in range(2):
            webhook = client.post(
                "/api/webhooks/mercado-pago?data.id=123456789",
                headers=headers,
                json={"type": "payment", "data": {"id": "123456789"}},
            )
            assert webhook.status_code == 200, webhook.text

        status = client.get(f"/api/payments/by-builder/{session_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "paid"

        repository = GuideRepository(tmp_path / "minerva.sqlite3")
        entitlement = repository.entitlement_for_builder(
            user_id=_owner().id,
            builder_session_id=session_id,
        )
        assert entitlement is not None
        assert entitlement.status == "active"
        assert repository.claim_builder_entitlement(
            user_id=_owner().id,
            builder_session_id=session_id,
        )
        assert repository.claim_builder_entitlement(
            user_id=_owner().id,
            builder_session_id=session_id,
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_browser_return_refresh_confirms_with_provider_and_rejects_mismatch(monkeypatch, tmp_path):
    client = _setup_payment_environment(monkeypatch, tmp_path)
    try:
        session_id = _builder_session_id()
        checkout = client.post(
            "/api/payments/checkout",
            headers={"Idempotency-Key": "checkout-return"},
            json={"builder_session_id": session_id},
        )
        payment_id = checkout.json()["payment_id"]
        FakeMercadoPagoClient.provider_payment = MercadoPagoPayment(
            id="987654321",
            status="approved",
            external_reference="different-local-payment",
            amount_minor=100,
            currency="BRL",
        )
        mismatch = client.post(
            f"/api/payments/{payment_id}/refresh",
            json={"provider_payment_id": "987654321"},
        )
        assert mismatch.status_code == 409
        assert mismatch.json()["detail"]["code"] == "payment_confirmation_mismatch"

        FakeMercadoPagoClient.provider_payment = MercadoPagoPayment(
            id="987654321",
            status="approved",
            external_reference=payment_id,
            amount_minor=100,
            currency="BRL",
        )
        confirmed = client.post(
            f"/api/payments/{payment_id}/refresh",
            json={"provider_payment_id": "987654321"},
        )
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["status"] == "paid"
        assert client.get(f"/api/payments/by-builder/{session_id}").json()["status"] == "paid"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_all_delivery_routes_require_payment_and_refund_revokes_entitlement(monkeypatch, tmp_path):
    client = _setup_payment_environment(monkeypatch, tmp_path)
    try:
        session_id = _builder_session_id()
        for path in (
            f"/api/guide-builder/{session_id}/complete",
            f"/api/guide-builder/{session_id}/pdf",
        ):
            blocked = client.post(path)
            assert blocked.status_code == 402
            assert blocked.json()["detail"]["code"] == "guide_payment_required"

        checkout = client.post(
            "/api/payments/checkout",
            headers={"Idempotency-Key": "checkout-refund"},
            json={"builder_session_id": session_id},
        )
        payment_id = checkout.json()["payment_id"]
        provider_payment_id = "1122334455"
        FakeMercadoPagoClient.provider_payment = MercadoPagoPayment(
            id=provider_payment_id,
            status="approved",
            external_reference=payment_id,
            amount_minor=100,
            currency="BRL",
        )
        confirmed = client.post(
            f"/api/payments/{payment_id}/refresh",
            json={"provider_payment_id": provider_payment_id},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "paid"

        FakeMercadoPagoClient.provider_payment = MercadoPagoPayment(
            id=provider_payment_id,
            status="refunded",
            external_reference=payment_id,
            amount_minor=100,
            currency="BRL",
        )
        request_id = "provider-refund-1"
        refunded = client.post(
            f"/api/webhooks/mercado-pago?data.id={provider_payment_id}",
            headers={
                "x-request-id": request_id,
                "x-signature": _signature("webhook-test-secret", request_id, provider_payment_id),
            },
            json={"type": "payment", "data": {"id": provider_payment_id}},
        )
        assert refunded.status_code == 200
        assert client.get(f"/api/payments/by-builder/{session_id}").json()["status"] == "refunded"

        repository = GuideRepository(tmp_path / "minerva.sqlite3")
        entitlement = repository.entitlement_for_builder(
            user_id=_owner().id,
            builder_session_id=session_id,
        )
        assert entitlement is not None
        assert entitlement.status == "revoked"
        blocked_after_refund = client.post(
            f"/api/guide-builder/{session_id}/pages/cover/attempts",
            headers={"Idempotency-Key": "cover-after-refund"},
            json={},
        )
        assert blocked_after_refund.status_code == 402
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_webhook_rejects_invalid_signature(monkeypatch, tmp_path):
    client = _setup_payment_environment(monkeypatch, tmp_path)
    try:
        response = client.post(
            "/api/webhooks/mercado-pago?data.id=123456789",
            headers={"x-request-id": "request", "x-signature": "ts=1,v1=invalid"},
            json={"type": "payment", "data": {"id": "123456789"}},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "invalid_webhook_signature"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_enabled_checkout_rejects_non_https_webhook_url(monkeypatch, tmp_path):
    client = _setup_payment_environment(monkeypatch, tmp_path)
    monkeypatch.setenv(
        "MERCADO_PAGO_WEBHOOK_URL",
        "http://127.0.0.1:8000/api/webhooks/mercado-pago",
    )
    try:
        response = client.get("/api/products/guide")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "payment_configuration_error"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
