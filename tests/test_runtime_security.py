from fastapi.testclient import TestClient

from minerva_travel import storage
from minerva_travel.app import app
from minerva_travel.config import cors_allowed_origins


def test_health_endpoints_are_public_and_readiness_checks_local_dependencies(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(storage, "RUNTIME_DIR", tmp_path)
    client = TestClient(app)

    live = client.get("/health/live")
    ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json()["checks"] == {"database": "ok", "storage": "ok"}


def test_security_headers_and_request_id_are_applied():
    client = TestClient(app)

    response = client.get("/api/catalog", headers={"X-Request-ID": "e2e-request-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "e2e-request-123"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_untrusted_request_id_is_replaced():
    client = TestClient(app)

    response = client.get("/health/live", headers={"X-Request-ID": "bad request id\nvalue"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "bad request id\nvalue"
    assert len(response.headers["x-request-id"]) == 32


def test_validation_errors_use_the_versioned_api_error_envelope():
    client = TestClient(app)

    response = client.post(
        "/api/itinerary/recommend",
        json={},
        headers={"X-Request-ID": "validation-request-123"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "input_validation_error"
    assert response.json()["message"] == "Revise os campos destacados e tente novamente."
    assert response.json()["field_errors"]
    assert response.json()["request_id"] == "validation-request-123"
    assert response.headers["x-request-id"] == response.json()["request_id"]


def test_not_found_errors_use_the_same_api_error_envelope():
    client = TestClient(app)

    response = client.get("/api/route-that-does-not-exist")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert response.json()["message"] == "Not Found"
    assert response.json()["field_errors"] == []
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_openapi_documents_the_shared_error_contract_and_api_version():
    schema = app.openapi()

    assert schema["info"]["version"] == "1.0.0"
    error_schema = schema["components"]["schemas"]["ApiErrorResponse"]
    assert {"code", "message", "field_errors", "request_id"}.issubset(error_schema["required"])
    response_schema = schema["paths"]["/api/itinerary/recommend"]["post"]["responses"]["422"]
    reference = response_schema["content"]["application/json"]["schema"]["$ref"]
    assert reference == "#/components/schemas/ApiErrorResponse"

    expected_success_contracts = {
        ("/api/catalog", "get", "200"): "CatalogResponse",
        ("/health/live", "get", "200"): "HealthLiveResponse",
        ("/health/ready", "get", "200"): "HealthReadyResponse",
        ("/api/itinerary/recommend", "post", "200"): "ItineraryRecommendation",
        ("/api/itinerary/discover", "post", "200"): "DynamicItineraryResponse",
        ("/api/itinerary/routes/suggest", "post", "200"): "RouteSuggestionResponse",
        ("/api/custom-landmarks/resolve", "post", "200"): "CustomLandmarksResponse",
        (
            "/api/landmarks/resolve-structured",
            "post",
            "200",
        ): "LandmarkResolutionResponse",
        ("/api/landmarks/parse", "post", "200"): "LandmarkResolutionResponse",
        ("/api/landmarks/parse-preview", "post", "200"): "LandmarkResolutionResponse",
        ("/api/guides", "get", "200"): "GuideListResponse",
        ("/api/guides/{guide_id}", "get", "200"): "GuideResponse",
        ("/api/guides/{guide_id}", "delete", "200"): "DeletedResponse",
        ("/api/drafts/current", "get", "200"): "CurrentGuideDraftResponse",
        ("/api/drafts", "post", "201"): "GuideDraftResponse",
        ("/api/drafts/{draft_id}", "put", "200"): "GuideDraftResponse",
        ("/api/drafts/{draft_id}", "delete", "200"): "DeletedResponse",
        ("/api/jobs", "get", "200"): "GuideJobListResponse",
        ("/api/jobs/{job_id}", "get", "200"): "GuideJobResponse",
        ("/api/jobs/{job_id}", "delete", "200"): "GuideJobResponse",
        ("/api/account/export", "get", "200"): "AccountExportResponse",
        ("/api/account/data", "delete", "200"): "AccountDeletionResponse",
    }
    for (path, method, status), model_name in expected_success_contracts.items():
        success_schema = schema["paths"][path][method]["responses"][status]
        success_reference = success_schema["content"]["application/json"]["schema"]["$ref"]
        assert success_reference == f"#/components/schemas/{model_name}"

    generation_schema = schema["paths"]["/api/generate"]["post"]["responses"]["200"]
    generation_variants = generation_schema["content"]["application/json"]["schema"]["anyOf"]
    assert {variant["$ref"] for variant in generation_variants} == {
        "#/components/schemas/GuideGenerationCompletedResponse",
        "#/components/schemas/GuideGenerationQueuedResponse",
    }


def test_all_public_json_api_routes_have_explicit_response_contracts():
    missing_contracts = []
    generic_contracts = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/"):
            continue
        response_model = getattr(route, "response_model", None)
        if response_model is None:
            missing_contracts.append(path)
        if response_model in {dict, dict[str, object]}:
            generic_contracts.append(path)

    assert missing_contracts == []
    assert generic_contracts == []


def test_malformed_inputs_across_write_routes_return_4xx_error_envelopes():
    client = TestClient(app)
    json_routes = [
        ("post", "/api/itinerary/recommend"),
        ("post", "/api/itinerary/discover"),
        ("post", "/api/itinerary/routes/suggest"),
        ("post", "/api/custom-landmarks/resolve"),
        ("post", "/api/landmarks/resolve-structured"),
        ("post", "/api/landmarks/parse"),
        ("post", "/api/landmarks/parse-preview"),
        ("post", "/api/drafts"),
        ("put", "/api/drafts/not-a-real-draft"),
    ]

    for method, path in json_routes:
        response = client.request(
            method,
            path,
            content="{",
            headers={"Content-Type": "application/json"},
        )
        assert 400 <= response.status_code < 500, (path, response.text)
        assert response.json()["code"] == "input_validation_error"
        assert response.json()["field_errors"]
        assert response.json()["request_id"] == response.headers["x-request-id"]

    multipart_response = client.post("/api/generate", data={})
    assert multipart_response.status_code == 422
    assert multipart_response.json()["code"] == "input_validation_error"
    assert multipart_response.json()["field_errors"]


def test_generation_form_model_rejects_contract_limits_before_processing():
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "x" * 161,
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "selected_landmarks": "paris:eiffel-tower",
        },
        files={"family_photo": ("family.png", b"not-read", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "input_validation_error"
    assert any(error["loc"][-1] == "title" for error in response.json()["field_errors"])


def test_json_request_contracts_reject_unknown_fields():
    client = TestClient(app)
    requests = [
        ("/api/itinerary/recommend", {"destination_ids": ["paris"], "days": 1}),
        ("/api/itinerary/discover", {"destination": "Paris", "days": 1}),
        ("/api/itinerary/routes/suggest", {"days": 1}),
        ("/api/custom-landmarks/resolve", {"landmarks": "Torre Eiffel, Paris"}),
        (
            "/api/landmarks/resolve-structured",
            {
                "destinations": [{"place": "Paris", "landmarks": ["Torre Eiffel"]}],
            },
        ),
        ("/api/landmarks/parse", {"message": "Torre Eiffel, Paris"}),
        ("/api/landmarks/parse-preview", {"message": "Torre Eiffel, Paris"}),
        ("/api/drafts", {"title": "Viagem", "payload": {}}),
    ]

    for path, payload in requests:
        response = client.post(path, json={**payload, "unexpected_contract_field": True})
        assert response.status_code == 422, (path, response.text)
        assert response.json()["code"] == "input_validation_error"
        assert any(
            error["loc"][-1] == "unexpected_contract_field"
            for error in response.json()["field_errors"]
        )


def test_openapi_marks_all_json_request_models_as_closed_contracts():
    schema = app.openapi()
    request_models = {
        "CustomLandmarksResolveRequest",
        "DynamicItineraryRequest",
        "GuideDraftCreateRequest",
        "GuideDraftUpdateRequest",
        "ItineraryRecommendationRequest",
        "LandmarkParseRequest",
        "RouteSuggestionRequest",
        "StructuredLandmarksResolveRequest",
    }

    for model_name in request_models:
        assert schema["components"]["schemas"][model_name]["additionalProperties"] is False


def test_production_cors_rejects_wildcard_and_non_https(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    try:
        cors_allowed_origins()
    except RuntimeError as error:
        assert "wildcard" in str(error).lower()
    else:  # pragma: no cover - explicit security invariant
        raise AssertionError("Production wildcard CORS should be rejected.")

    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://example.com")
    try:
        cors_allowed_origins()
    except RuntimeError as error:
        assert "https" in str(error).lower()
    else:  # pragma: no cover - explicit security invariant
        raise AssertionError("Production CORS must require HTTPS.")


def test_production_cors_accepts_explicit_https_origins(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "https://app.minerva.example,https://admin.minerva.example",
    )

    assert cors_allowed_origins() == [
        "https://app.minerva.example",
        "https://admin.minerva.example",
    ]
