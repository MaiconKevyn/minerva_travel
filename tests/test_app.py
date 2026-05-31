import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from minerva_travel.app import app, custom_destinations_from_form, generate_selected_landmark_art


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


def test_api_generate_uses_confirmed_landmarks_for_cover_prompt(
    tmp_path,
    monkeypatch,
):
    captured_cover_landmarks = []

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            captured_cover_landmarks.extend(destination_names)
            output_path.write_bytes(b"cover")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(f"{landmark_name}|{city}|{country}".encode())
            return output_path

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(
                f"lineart|{landmark_name}|{city}|{country}|{reference_image.name}".encode()
            )
            return output_path

    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.fetch_custom_wikimedia_assets", lambda *_: {})
    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia do Brasil",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": (
                "Cristo Redentor, Rio de Janeiro, Brasil\n"
                "Usina do Gasometro, Porto Alegre, Brasil"
            ),
        },
        files={"family_photo": ("family.png", Path("README.md").read_bytes(), "image/png")},
    )

    assert response.status_code == 200
    assert captured_cover_landmarks == ["Cristo Redentor", "Usina do Gasometro"]


def test_api_generate_creates_images_for_confirmed_landmarks(
    tmp_path,
    monkeypatch,
):
    generated_landmarks = []
    generated_lineart = []

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            output_path.write_bytes(b"cover")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            generated_landmarks.append((landmark_name, city, country))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"landmark")
            return output_path

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            generated_lineart.append((landmark_name, city, country, reference_image))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"lineart")
            return output_path

    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia do Brasil",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": (
                "Cristo Redentor, Rio de Janeiro, Brasil\n"
                "Usina do Gasometro, Porto Alegre, Brasil"
            ),
        },
        files={"family_photo": ("family.png", Path("README.md").read_bytes(), "image/png")},
    )

    assert response.status_code == 200
    assert sorted(generated_landmarks) == sorted(
        [
            ("Cristo Redentor", "Rio de Janeiro", "Brasil"),
            ("Usina do Gasometro", "Porto Alegre", "Brasil"),
        ]
    )
    assert sorted(
        (name, city, country)
        for name, city, country, _ in generated_lineart
    ) == sorted(
        [
            ("Cristo Redentor", "Rio de Janeiro", "Brasil"),
            ("Usina do Gasometro", "Porto Alegre", "Brasil"),
        ]
    )
    assert sorted(reference.name for *_, reference in generated_lineart) == [
        "cristo-redentor.png",
        "usina-do-gasometro.png",
    ]
    assert all(
        "runtime/generated/landmarks" in reference.as_posix()
        for *_, reference in generated_lineart
    )


def test_selected_landmark_art_generates_multiple_landmarks_concurrently(monkeypatch):
    destinations, selected = custom_destinations_from_form(
        "Cristo Redentor, Rio de Janeiro, Brasil\n"
        "Usina do Gasometro, Porto Alegre, Brasil"
    )
    active_image_generations = 0
    max_active_image_generations = 0
    lock = threading.Lock()

    class SlowGenerator:
        def generate_landmark_image(self, landmark_name, city, country, output_path):
            nonlocal active_image_generations, max_active_image_generations
            with lock:
                active_image_generations += 1
                max_active_image_generations = max(
                    max_active_image_generations,
                    active_image_generations,
                )
            time.sleep(0.05)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(f"{landmark_name}|{city}|{country}".encode())
            with lock:
                active_image_generations -= 1
            return output_path

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(f"lineart|{reference_image.name}".encode())
            return output_path

    monkeypatch.setenv("IMAGE_GENERATION_CONCURRENCY", "2")

    images, lineart_images = generate_selected_landmark_art(
        destinations=destinations,
        selected=selected,
        request_id="parallel-test",
        generator=SlowGenerator(),
    )

    assert len(images) == 2
    assert len(lineart_images) == 2
    assert max_active_image_generations == 2
