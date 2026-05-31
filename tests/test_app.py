from pathlib import Path

from fastapi.testclient import TestClient

from minerva_travel.app import app


def test_home_page_lists_reference_landmarks():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Torre Eiffel" in response.text
    assert "Comer Pastel de Belem" in response.text


def test_generate_creates_download_link(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    client = TestClient(app)

    response = client.post(
        "/generate",
        data={
            "title": "Pequenos Exploradores pela Europa",
            "children_names": "Alice, Antonio",
            "parents_names": "Ana, Otavio",
            "year": "2026",
            "selected_landmarks": ["paris:eiffel-tower"],
        },
        files={"family_photo": ("family.png", Path("README.md").read_bytes(), "image/png")},
    )

    assert response.status_code == 200
    assert "/download/" in response.text


def test_api_catalog_returns_destinations_and_landmarks():
    client = TestClient(app)

    response = client.get("/api/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Pequenos Exploradores pela Europa"
    assert payload["destinations"][0]["city"] == "Paris"
    assert payload["destinations"][0]["landmarks"][0]["selection_id"] == "paris:eiffel-tower"


def test_landmarks_parse_allows_browser_preflight_from_frontend_origin():
    client = TestClient(app)

    response = client.options(
        "/api/landmarks/parse",
        headers={
            "Origin": "https://minerva-travel.hostingerapp.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] in {
        "*",
        "https://minerva-travel.hostingerapp.com",
    }


def test_resolve_custom_landmarks_structures_freeform_list():
    client = TestClient(app)

    response = client.post(
        "/api/custom-landmarks/resolve",
        json={"landmarks": "Colosseum, Rome, Italy\nTrevi Fountain, Rome, Italy"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_landmarks"] == [
        "custom-rome:colosseum",
        "custom-rome:trevi-fountain",
    ]
    assert payload["destinations"][0]["city"] == "Rome"
    assert payload["destinations"][0]["landmarks"][0]["representative_query"] == (
        "Colosseum Rome Italy tourist attraction exterior"
    )


def test_parse_landmarks_returns_structured_landmarks(monkeypatch):
    def fake_parse(message: str):
        assert "Paris" in message
        return [
            {
                "name": "Torre Eiffel",
                "city": "Paris",
                "country": "Franca",
                "confidence": 0.98,
            },
            {
                "name": "Museu do Louvre",
                "city": "Paris",
                "country": "Franca",
                "confidence": 0.96,
            },
        ]

    monkeypatch.setattr("minerva_travel.app.parse_landmarks_from_message", fake_parse)
    client = TestClient(app)

    response = client.post(
        "/api/landmarks/parse",
        json={"message": "Em Paris vamos visitar Torre Eiffel e Museu do Louvre."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["custom_landmarks"] == (
        "Torre Eiffel, Paris, Franca\nMuseu do Louvre, Paris, Franca"
    )
    assert payload["destinations"][0]["city"] == "Paris"
    assert payload["destinations"][0]["landmarks"][0]["name"] == "Torre Eiffel"
    assert payload["destinations"][0]["landmarks"][0]["image"] is None
    assert payload["destinations"][0]["landmarks"][1]["image"] is None


def test_sample_preview_renders_pdf_layout_html():
    client = TestClient(app)

    response = client.get("/preview/sample")

    assert response.status_code == 200
    assert "Pequenos Exploradores pela Europa" in response.text
    assert "guide-shell" in response.text
    assert "page cover-page" in response.text


def test_api_generate_returns_download_url(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Pequenos Exploradores pela Europa",
            "children_names": "Alice, Antonio",
            "parents_names": "Ana, Otavio",
            "year": "2026",
            "selected_landmarks": ["paris:eiffel-tower"],
        },
        files={"family_photo": ("family.png", Path("README.md").read_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["download_url"].startswith("/download/")
    assert payload["request_id"]


def test_api_generate_accepts_custom_landmarks_without_catalog_selection(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.fetch_custom_wikimedia_assets", lambda *_: {})
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia de Roma",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": "Colosseum, Rome, Italy\nTrevi Fountain, Rome, Italy",
        },
        files={"family_photo": ("family.png", Path("README.md").read_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["download_url"].startswith("/download/")
