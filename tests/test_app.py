import json
import threading
import time
from pathlib import Path

import httpx
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from minerva_travel.app import (
    LINEART_CANVAS_SIZE,
    app,
    create_local_lineart_fallbacks,
    custom_destinations_from_form,
    fetch_custom_wikimedia_assets,
    generate_selected_landmark_art,
)
from minerva_travel.models import RestaurantRecommendation
from minerva_travel.persistence import guide_repository
from minerva_travel.wikimedia_assets import WikimediaAsset

TEST_FAMILY_PHOTO = Path("assets/landmarks/paris/eiffel-tower.png").read_bytes()


def test_home_redirects_to_the_single_frontend_application():
    client = TestClient(app)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "http://127.0.0.1:3000"


def test_legacy_generate_endpoint_cannot_bypass_the_durable_api():
    client = TestClient(app)

    response = client.post("/generate")

    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "legacy_generation_removed"


def test_api_catalog_returns_destinations_and_landmarks():
    client = TestClient(app)

    response = client.get("/api/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Pequenos Exploradores pela Europa"
    assert payload["destinations"][0]["city"] == "Paris"
    assert payload["destinations"][0]["landmarks"][0]["selection_id"] == "paris:eiffel-tower"


def test_route_suggestion_endpoint_returns_editable_structured_destinations():
    client = TestClient(app)

    response = client.post(
        "/api/itinerary/routes/suggest",
        json={
            "trip_idea": "Queremos visitar Paris e Londres com parques e museus.",
            "days": 5,
            "pace": "light",
            "interests": ["parques", "museus"],
            "children_ages": [6],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["options"][0]["id"] == "suggested-route-1"
    assert payload["options"][0]["structured_destinations"] == [
        {
            "id": "suggested-1",
            "place": "Paris",
            "timing": "defina a data ou período",
            "days": 3,
        },
        {
            "id": "suggested-2",
            "place": "Londres",
            "timing": "depois de Paris",
            "days": 2,
        },
    ]
    assert "parques" in payload["options"][0]["summary"]


def test_route_suggestion_endpoint_preserves_current_structured_destinations():
    client = TestClient(app)

    response = client.post(
        "/api/itinerary/routes/suggest",
        json={
            "trip_idea": "Queremos ajuda com atividades.",
            "days": 4,
            "structured_destinations": [
                {
                    "id": "manual-paris",
                    "place": "Paris, França",
                    "timing": "Julho de 2026",
                    "days": 4,
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["options"][0]["structured_destinations"] == [
        {
            "id": "suggested-1",
            "place": "Paris, França",
            "timing": "Julho de 2026",
            "days": 4,
        }
    ]


def test_landmarks_parse_allows_browser_preflight_from_frontend_origin():
    client = TestClient(app)

    response = client.options(
        "/api/landmarks/parse",
        headers={
            "Origin": "https://minerva-travel.hostingerapp.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] in {
        "*",
        "https://minerva-travel.hostingerapp.com",
    }
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers


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


def test_custom_destinations_from_text_enriches_missing_descriptions(monkeypatch):
    def fake_parse(message: str):
        assert "Torre Eiffel, Paris, Franca" in message
        return [
            {
                "name": "Torre Eiffel",
                "city": "Paris",
                "country": "Franca",
                "description": [
                    "A Torre Eiffel foi feita de milhares de pecas de metal.",
                    "Do alto dela, Paris parece um mapa cheio de caminhos.",
                ],
                "confidence": 0.98,
            }
        ]

    monkeypatch.setattr("minerva_travel.app.parse_landmarks_from_message", fake_parse)

    destinations, selected = custom_destinations_from_form("Torre Eiffel, Paris, Franca")

    assert selected == ["custom-paris:torre-eiffel"]
    assert destinations[0].landmarks[0].description == [
        "A Torre Eiffel foi feita de milhares de pecas de metal.",
        "Do alto dela, Paris parece um mapa cheio de caminhos.",
    ]


def test_parse_landmarks_returns_structured_landmarks(monkeypatch):
    def fake_parse(message: str):
        assert "Paris" in message
        return [
            {
                "name": "Torre Eiffel",
                "city": "Paris",
                "country": "Franca",
                "description": [
                    "A Torre Eiffel foi construida para uma grande exposicao em Paris.",
                    "Hoje ela ajuda as criancas a reconhecerem a cidade em qualquer desenho.",
                ],
                "confidence": 0.98,
            },
            {
                "name": "Museu do Louvre",
                "city": "Paris",
                "country": "Franca",
                "description": [
                    "O Louvre guarda obras famosas e muito antigas.",
                    "Sua piramide de vidro parece uma entrada para uma aventura de arte.",
                ],
                "confidence": 0.96,
            },
        ]

    monkeypatch.setattr("minerva_travel.app.parse_landmarks_from_message", fake_parse)
    monkeypatch.setattr("minerva_travel.app.google_maps_api_key", lambda: None)
    client = TestClient(app)

    response = client.post(
        "/api/landmarks/parse",
        json={"message": "Em Paris vamos visitar Torre Eiffel e Museu do Louvre."},
    )

    assert response.status_code == 200
    payload = response.json()
    custom_landmarks = json.loads(payload["custom_landmarks"])
    assert custom_landmarks[0] == {
        "name": "Torre Eiffel",
        "city": "Paris",
        "country": "Franca",
        "description": [
            "A Torre Eiffel foi construida para uma grande exposicao em Paris.",
            "Hoje ela ajuda as criancas a reconhecerem a cidade em qualquer desenho.",
        ],
    }
    assert payload["destinations"][0]["city"] == "Paris"
    assert payload["destinations"][0]["landmarks"][0]["name"] == "Torre Eiffel"
    assert payload["destinations"][0]["landmarks"][0]["description"] == [
        "A Torre Eiffel foi construida para uma grande exposicao em Paris.",
        "Hoje ela ajuda as criancas a reconhecerem a cidade em qualquer desenho.",
    ]
    assert payload["destinations"][0]["landmarks"][0]["image"] is None
    assert payload["destinations"][0]["landmarks"][1]["image"] is None


def test_parse_landmarks_enriches_confirmed_places_with_map_location(monkeypatch):
    def fake_parse(message: str):
        assert "Paris" in message
        return [
            {
                "name": "Torre Eiffel",
                "city": "Paris",
                "country": "Franca",
                "description": ["A Torre Eiffel ajuda a reconhecer Paris no mapa."],
                "confidence": 0.98,
            }
        ]

    def fake_resolve(destinations, *, api_key: str, include_photos: bool = False):
        assert api_key == "test-google-key"
        assert include_photos is True
        assert destinations[0].city == "Paris"
        return {
            "custom-paris:torre-eiffel": {
                "place_id": "eiffel",
                "google_maps_uri": "https://maps.google.com/?cid=eiffel",
                "formatted_address": "Champ de Mars, 5 Av. Anatole France, Paris",
                "latitude": 48.8584,
                "longitude": 2.2945,
                "location_status": "resolved",
            }
        }

    monkeypatch.setattr("minerva_travel.app.parse_landmarks_from_message", fake_parse)
    monkeypatch.setattr("minerva_travel.app.google_maps_api_key", lambda: "test-google-key")
    monkeypatch.setattr(
        "minerva_travel.app.resolve_landmark_locations",
        fake_resolve,
        raising=False,
    )
    client = TestClient(app)

    response = client.post(
        "/api/landmarks/parse",
        json={"message": "Em Paris vamos visitar a Torre Eiffel."},
    )

    assert response.status_code == 200
    landmark = response.json()["destinations"][0]["landmarks"][0]
    assert landmark["latitude"] == 48.8584
    assert landmark["longitude"] == 2.2945
    assert landmark["google_maps_uri"] == "https://maps.google.com/?cid=eiffel"
    assert landmark["formatted_address"] == "Champ de Mars, 5 Av. Anatole France, Paris"
    assert landmark["location_status"] == "resolved"


def test_resolve_structured_landmarks_groups_by_destination_and_selects_all(monkeypatch):
    def fake_resolve(destinations, *, api_key: str, include_photos: bool = False):
        assert api_key == "test-google-key"
        assert include_photos is True
        assert destinations[0].city == "Paris"
        return {
            "custom-paris:torre-eiffel": {
                "place_id": "eiffel",
                "google_maps_uri": "https://maps.google.com/?cid=eiffel",
                "formatted_address": "Champ de Mars, Paris",
                "latitude": 48.8584,
                "longitude": 2.2945,
                "location_status": "resolved",
                "image_url": "https://places.googleapis.com/photo/eiffel.jpg",
                "image_attributions": [{"display_name": "Foto: Guia Local", "uri": ""}],
            }
        }

    monkeypatch.setattr("minerva_travel.app.google_maps_api_key", lambda: "test-google-key")
    monkeypatch.setattr("minerva_travel.app.resolve_landmark_locations", fake_resolve)
    client = TestClient(app)

    response = client.post(
        "/api/landmarks/resolve-structured",
        json={
            "destinations": [
                {"place": "Paris, França", "landmarks": ["Torre Eiffel", "Museu do Louvre"]},
                {"place": "Roma", "landmarks": ["Coliseu"]},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_landmarks"] == [
        "custom-paris:torre-eiffel",
        "custom-paris:museu-do-louvre",
        "custom-roma:coliseu",
    ]

    paris, roma = payload["destinations"]
    assert paris["city"] == "Paris"
    assert paris["country"] == "França"
    assert roma["city"] == "Roma"

    eiffel, louvre = paris["landmarks"]
    assert eiffel["confidence"] == 1.0
    assert eiffel["latitude"] == 48.8584
    assert eiffel["image"]["image_url"] == "https://places.googleapis.com/photo/eiffel.jpg"
    assert eiffel["image_attributions"] == [{"display_name": "Foto: Guia Local", "uri": ""}]
    assert louvre["image"] is None
    assert louvre["location_status"] == "missing"


def test_resolve_structured_landmarks_without_google_key_keeps_structure(monkeypatch):
    monkeypatch.setattr("minerva_travel.app.google_maps_api_key", lambda: None)
    client = TestClient(app)

    response = client.post(
        "/api/landmarks/resolve-structured",
        json={"destinations": [{"place": "Lisboa, Portugal", "landmarks": ["Oceanário"]}]},
    )

    assert response.status_code == 200
    landmark = response.json()["destinations"][0]["landmarks"][0]
    assert landmark["name"] == "Oceanário"
    assert landmark["location_status"] == "missing"
    assert landmark["image"] is None


def test_resolve_structured_landmarks_requires_at_least_one_landmark():
    client = TestClient(app)

    response = client.post(
        "/api/landmarks/resolve-structured",
        json={"destinations": [{"place": "Paris, França", "landmarks": ["   "]}]},
    )

    assert response.status_code == 400
    assert "pelo menos um ponto turistico" in response.json()["detail"]


def test_sample_preview_renders_pdf_layout_html():
    client = TestClient(app)

    response = client.get("/preview/sample")

    assert response.status_code == 200
    assert "Pequenos Exploradores pela Europa" in response.text
    assert "guide-shell" in response.text
    assert "page cover-page" in response.text
    assert "activity-page" in response.text
    assert "Checklist da aventura" in response.text


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
            "itinerary_json": json.dumps(
                {
                    "mode": "known",
                    "pace": "light",
                    "interests": ["história"],
                    "destinations": [
                        {
                            "id": "paris",
                            "place": "Paris, França",
                            "timing": "Julho de 2026",
                            "days": 1,
                            "order": 1,
                        }
                    ],
                    "days": [
                        {
                            "day": 1,
                            "title": "Paris em família",
                            "stops": [
                                {
                                    "selection_id": "paris:eiffel-tower",
                                    "name": "Torre Eiffel",
                                    "destination_id": "paris",
                                }
                            ],
                        }
                    ],
                }
            ),
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["download_url"].startswith("/download/")
    assert payload["request_id"]
    persisted = guide_repository().get_for_owner(payload["request_id"], "development-user")
    assert persisted is not None
    assert persisted.metadata["itinerary"]["pace"] == "light"
    assert persisted.metadata["itinerary"]["days"][0]["stops"][0]["selection_id"] == (
        "paris:eiffel-tower"
    )


def test_api_generate_uses_safe_photo_fallback_when_people_validation_is_unavailable(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    captured_counts = []

    class FakeGenerator:
        def generate_cover(
            self,
            family_photo,
            output_path,
            title,
            destination_names,
            *,
            expected_visible_family_member_count=None,
        ):
            captured_counts.append(expected_visible_family_member_count)
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            raise AssertionError("landmark image generation should stay disabled")

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            raise AssertionError("landmark lineart generation should stay disabled")

    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Pequenos Exploradores pela Europa",
            "children_names": "Alice, Antonio",
            "parents_names": "Ana, Otavio",
            "year": "2026",
            "expected_visible_family_member_count": "4",
            "selected_landmarks": ["paris:eiffel-tower"],
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert captured_counts == []
    assert payload["cover_status"]["expected_visible_family_member_count"] == 4
    assert payload["cover_status"]["fallback_used"] is True
    assert payload["cover_status"]["attempts"] == 0


def test_api_generate_without_expected_family_member_count_keeps_existing_flow(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    captured_counts = []

    class FakeGenerator:
        def generate_cover(
            self,
            family_photo,
            output_path,
            title,
            destination_names,
            *,
            expected_visible_family_member_count=None,
        ):
            captured_counts.append(expected_visible_family_member_count)
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            raise AssertionError("landmark image generation should stay disabled")

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            raise AssertionError("landmark lineart generation should stay disabled")

    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
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
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert captured_counts == [None]
    assert payload["download_url"].startswith("/download/")
    assert payload["cover_status"]["expected_visible_family_member_count"] is None


def test_api_generate_accepts_child_ages(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Pequenos Exploradores pela Europa",
            "children_names": "Alice, Antonio",
            "children_ages": ["5", "9"],
            "parents_names": "Ana, Otavio",
            "year": "2026",
            "selected_landmarks": ["paris:eiffel-tower"],
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["download_url"].startswith("/download/")


def test_api_generate_omits_restaurant_discovery_without_extra(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)

    def fail_restaurant_discovery(*_args, **_kwargs):
        raise AssertionError("restaurant discovery should require explicit entitlement")

    monkeypatch.setattr(
        "minerva_travel.app.discover_restaurants_for_guide",
        fail_restaurant_discovery,
    )
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Pequenos Exploradores pela Europa",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "selected_landmarks": ["paris:eiffel-tower"],
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200


def test_api_generate_runs_restaurant_discovery_with_extra(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    captured_anchors = []
    captured_restaurants = []

    class FakeGenerator:
        def generate_cover(
            self,
            family_photo,
            output_path,
            title,
            destination_names,
            *,
            expected_visible_family_member_count=None,
        ):
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            raise AssertionError("landmark image generation should stay disabled")

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            raise AssertionError("landmark lineart generation should stay disabled")

    def fake_restaurant_discovery(guide_destinations, *, api_key=None):
        captured_anchors.extend(
            landmark.name for item in guide_destinations for landmark in item.landmarks
        )
        return [
            RestaurantRecommendation(
                destination_id=guide_destinations[0].destination.id,
                name="Bistro Familiar",
                nearby_context="perto de Torre Eiffel",
                reason="Boa pausa para familia entre passeios.",
            )
        ]

    def fake_write_pdf(context, output_path):
        captured_restaurants.extend(context.restaurant_recommendations)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"pdf")
        return output_path

    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    monkeypatch.setattr(
        "minerva_travel.app.discover_restaurants_for_guide",
        fake_restaurant_discovery,
    )
    monkeypatch.setattr("minerva_travel.app.write_pdf", fake_write_pdf)
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Pequenos Exploradores pela Europa",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "selected_landmarks": ["paris:eiffel-tower"],
            "restaurant_recommendations_extra": "true",
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    assert captured_anchors == ["Torre Eiffel"]
    assert [restaurant.name for restaurant in captured_restaurants] == ["Bistro Familiar"]


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
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["download_url"].startswith("/download/")


def test_api_generate_uses_custom_landmark_image_url_when_wikimedia_is_missing(
    tmp_path,
    monkeypatch,
):
    captured_images = []
    downloaded_image = tmp_path / "custom-images" / "speyer.jpg"
    downloaded_image.parent.mkdir(parents=True)
    downloaded_image.write_bytes(b"image")

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            raise AssertionError("landmark image generation should stay disabled")

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            raise AssertionError("landmark lineart generation should stay disabled")

    def fake_write_pdf(context, output_path):
        captured_images.extend(
            landmark.image
            for destination in context.destinations
            for landmark in destination.landmarks
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"pdf")
        return output_path

    def fake_download_custom_images(destinations, selected, request_id, *, skip_selection_ids):
        selection_id = f"{destinations[0].id}:{destinations[0].landmarks[0].id}"
        assert destinations[0].landmarks[0].image == (
            "https://lh3.googleusercontent.com/place-photo=w900"
        )
        assert selection_id in selected
        assert skip_selection_ids == set()
        return {selection_id: downloaded_image}

    custom_landmarks = json.dumps(
        [
            {
                "name": "Museu da Tecnologia de Speyer",
                "city": "Speyer",
                "country": "Alemanha",
                "description": ["Um museu cheio de maquinas e descobertas."],
                "image": "https://lh3.googleusercontent.com/place-photo=w900",
            }
        ]
    )

    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.fetch_custom_wikimedia_assets", lambda *_: {})
    monkeypatch.setattr(
        "minerva_travel.app.download_custom_landmark_images",
        fake_download_custom_images,
    )
    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    monkeypatch.setattr("minerva_travel.app.write_pdf", fake_write_pdf)
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia da Alemanha",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": custom_landmarks,
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    assert captured_images == [downloaded_image]


def test_api_generate_creates_local_lineart_from_custom_landmark_image_by_default(
    tmp_path,
    monkeypatch,
):
    captured_lineart_images = []
    generated_lineart = []
    downloaded_image = tmp_path / "custom-images" / "speyer.jpg"
    downloaded_image.parent.mkdir(parents=True)
    Image.new("RGB", (320, 220), "#4f86b7").save(downloaded_image)

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            raise AssertionError("landmark image generation should stay disabled")

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
            output_path.write_bytes(b"premium-lineart")
            return output_path

    def fake_write_pdf(context, output_path):
        captured_lineart_images.extend(
            landmark.lineart_image
            for destination in context.destinations
            for landmark in destination.landmarks
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"pdf")
        return output_path

    def fake_download_custom_images(destinations, selected, request_id, *, skip_selection_ids):
        selection_id = f"{destinations[0].id}:{destinations[0].landmarks[0].id}"
        return {selection_id: downloaded_image}

    custom_landmarks = json.dumps(
        [
            {
                "name": "Museu da Tecnologia de Speyer",
                "city": "Speyer",
                "country": "Alemanha",
                "description": ["Um museu cheio de maquinas e descobertas."],
                "image": "https://lh3.googleusercontent.com/place-photo=w900",
            }
        ]
    )

    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.fetch_custom_wikimedia_assets", lambda *_: {})
    monkeypatch.setattr(
        "minerva_travel.app.download_custom_landmark_images",
        fake_download_custom_images,
    )
    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    monkeypatch.setattr("minerva_travel.app.write_pdf", fake_write_pdf)
    monkeypatch.setenv("IMAGE_PROVIDER", "replicate")
    monkeypatch.setenv("LANDMARK_ART_GENERATION", "false")
    monkeypatch.delenv("COLORING_LINEART_GENERATION", raising=False)
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia da Alemanha",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": custom_landmarks,
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    assert generated_lineart == []
    assert len(captured_lineart_images) == 1
    assert captured_lineart_images[0] != Path("assets/lineart/paris/eiffel-tower.png")
    assert captured_lineart_images[0].exists()
    with Image.open(captured_lineart_images[0]) as lineart:
        assert lineart.size == LINEART_CANVAS_SIZE


def test_create_local_lineart_fallbacks_writes_named_placeholder_without_reference(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    destinations, selected = custom_destinations_from_form("Les Pavillons de Bercy, Paris, Franca")

    lineart_images = create_local_lineart_fallbacks(
        destinations,
        selected,
        "request-123",
        reference_images={},
    )

    assert sorted(lineart_images) == selected
    output_path = lineart_images[selected[0]]
    assert output_path.exists()
    assert output_path != Path("assets/lineart/paris/eiffel-tower.png")
    assert output_path.as_posix().endswith(
        "generated/lineart-local/request-123/custom-paris/les-pavillons-de-bercy.png"
    )


def test_create_local_lineart_fallbacks_simplifies_busy_reference_image(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    destinations, selected = custom_destinations_from_form("Museu do Louvre, Paris, Franca")
    selection_id = selected[0]
    reference = tmp_path / "louvre-reference.png"
    reference_image = Image.new("RGB", (360, 240), "#dfe8f1")
    draw = ImageDraw.Draw(reference_image)
    draw.polygon((40, 210, 180, 42, 320, 210), outline="#111111", fill="#f2f5f7", width=4)
    for x in range(64, 300, 8):
        draw.line((x, 70, x + 35, 210), fill="#26323a", width=1)
    for y in range(80, 205, 8):
        draw.line((55, y, 305, y), fill="#26323a", width=1)
    reference_image.save(reference)

    lineart_images = create_local_lineart_fallbacks(
        destinations,
        selected,
        "request-123",
        reference_images={selection_id: reference},
    )

    black_pixels = _count_black_pixels(lineart_images[selection_id])
    assert black_pixels < 35_000


def test_api_generate_uses_confirmed_landmarks_for_cover_prompt(
    tmp_path,
    monkeypatch,
):
    captured_cover_landmarks = []
    captured_summary_landmarks = []

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            captured_cover_landmarks.extend(destination_names)
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            captured_summary_landmarks.extend(destination_names)
            output_path.write_bytes(b"summary")
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
                "Cristo Redentor, Rio de Janeiro, Brasil\nUsina do Gasometro, Porto Alegre, Brasil"
            ),
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    assert captured_cover_landmarks == ["Cristo Redentor", "Usina do Gasometro"]
    assert captured_summary_landmarks == ["Cristo Redentor", "Usina do Gasometro"]


def test_api_generate_passes_trip_summary_image_to_pdf(
    tmp_path,
    monkeypatch,
):
    captured_summary_image = []

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            raise AssertionError("landmark image generation should stay disabled")

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            raise AssertionError("landmark lineart generation should stay disabled")

    def fake_write_pdf(context, output_path):
        captured_summary_image.append(context.summary_image)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"pdf")
        return output_path

    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.fetch_custom_wikimedia_assets", lambda *_: {})
    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    monkeypatch.setattr("minerva_travel.app.write_pdf", fake_write_pdf)
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia do Brasil",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": "Cristo Redentor, Rio de Janeiro, Brasil",
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    assert captured_summary_image
    assert captured_summary_image[0].name.endswith("-summary.png")


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

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
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
    monkeypatch.setattr("minerva_travel.app.fetch_custom_wikimedia_assets", lambda *_: {})
    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    monkeypatch.setenv("LANDMARK_ART_GENERATION", "true")
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia do Brasil",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": (
                "Cristo Redentor, Rio de Janeiro, Brasil\nUsina do Gasometro, Porto Alegre, Brasil"
            ),
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    assert sorted(generated_landmarks) == sorted(
        [
            ("Cristo Redentor", "Rio de Janeiro", "Brasil"),
            ("Usina do Gasometro", "Porto Alegre", "Brasil"),
        ]
    )
    assert sorted((name, city, country) for name, city, country, _ in generated_lineart) == sorted(
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
        "runtime/generated/landmarks" in reference.as_posix() for *_, reference in generated_lineart
    )


def test_api_generate_uses_wikimedia_image_before_generating_landmark_art(
    tmp_path,
    monkeypatch,
):
    generated_landmarks = []
    generated_lineart = []
    wikimedia_path = tmp_path / "wikimedia" / "rio" / "cristo.jpg"
    wikimedia_path.parent.mkdir(parents=True)
    Image.new("RGB", (320, 220), "#4f86b7").save(wikimedia_path)

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            generated_landmarks.append((landmark_name, city, country))
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"generated")
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

    def fake_wikimedia_assets(destinations, request_id):
        selection_id = f"{destinations[0].id}:{destinations[0].landmarks[0].id}"
        return {
            selection_id: WikimediaAsset(
                selection_id=selection_id,
                title="File:Cristo.jpg",
                source_url="https://commons.wikimedia.org/wiki/File:Cristo.jpg",
                image_url="https://upload.wikimedia.org/cristo.jpg",
                local_path=wikimedia_path,
                author="Jane Doe",
                license_short_name="CC BY-SA 4.0",
                license_url="https://creativecommons.org/licenses/by-sa/4.0/",
                credit="Jane Doe / Wikimedia Commons",
            )
        }

    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.fetch_custom_wikimedia_assets", fake_wikimedia_assets)
    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia do Brasil",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": "Cristo Redentor, Rio de Janeiro, Brasil",
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    assert generated_landmarks == []
    assert generated_lineart == []


def test_api_generate_keeps_local_landmark_asset_in_pdf_after_supabase_sync(
    tmp_path,
    monkeypatch,
):
    captured_images = []
    wikimedia_path = tmp_path / "wikimedia" / "rio" / "cristo.jpg"
    wikimedia_path.parent.mkdir(parents=True)
    wikimedia_path.write_bytes(b"wikimedia")

    class FakeGenerator:
        def generate_cover(self, family_photo, output_path, title, destination_names):
            output_path.write_bytes(b"cover")
            return output_path

        def generate_trip_summary(self, output_path, title, destination_names):
            output_path.write_bytes(b"summary")
            return output_path

        def generate_landmark_image(self, landmark_name, city, country, output_path):
            raise AssertionError("landmark image generation should stay disabled by default")

        def generate_landmark_lineart(
            self,
            landmark_name,
            city,
            country,
            reference_image,
            output_path,
        ):
            raise AssertionError("landmark lineart generation should stay disabled by default")

    def fake_wikimedia_assets(destinations, request_id):
        selection_id = f"{destinations[0].id}:{destinations[0].landmarks[0].id}"
        return {
            selection_id: WikimediaAsset(
                selection_id=selection_id,
                title="File:Cristo.jpg",
                source_url="https://commons.wikimedia.org/wiki/File:Cristo.jpg",
                image_url="https://upload.wikimedia.org/cristo.jpg",
                local_path=wikimedia_path,
                author="Jane Doe",
                license_short_name="CC BY-SA 4.0",
                license_url="https://creativecommons.org/licenses/by-sa/4.0/",
                credit="Jane Doe / Wikimedia Commons",
            )
        }

    def fake_sync(assets):
        return {
            selection_id: asset.model_copy(
                update={
                    "public_url": None,
                    "storage_path": f"{selection_id}.jpg",
                }
            )
            for selection_id, asset in assets.items()
        }

    def fake_write_pdf(context, output_path):
        captured_images.append(context.destinations[0].landmarks[0].image)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"pdf")
        return output_path

    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    monkeypatch.setattr("minerva_travel.app.fetch_custom_wikimedia_assets", fake_wikimedia_assets)
    monkeypatch.setattr("minerva_travel.app.sync_wikimedia_assets_to_storage", fake_sync)
    monkeypatch.setattr("minerva_travel.app.get_image_generator", lambda _: FakeGenerator())
    monkeypatch.setattr("minerva_travel.app.write_pdf", fake_write_pdf)
    client = TestClient(app)

    response = client.post(
        "/api/generate",
        data={
            "title": "Guia do Brasil",
            "children_names": "Alice",
            "parents_names": "Ana",
            "year": "2026",
            "custom_landmarks": "Cristo Redentor, Rio de Janeiro, Brasil",
        },
        files={"family_photo": ("family.png", TEST_FAMILY_PHOTO, "image/png")},
    )

    assert response.status_code == 200
    assert captured_images == [wikimedia_path]


def _count_black_pixels(path: Path) -> int:
    with Image.open(path) as image:
        grayscale = image.convert("L")
        return sum(1 for pixel in grayscale.getdata() if pixel < 128)


def test_fetch_custom_wikimedia_assets_ignores_network_failures(monkeypatch):
    destinations, _selected = custom_destinations_from_form("Cristo Redentor, Rio, Brasil")

    def fake_fetch_landmark_asset(*_args, **_kwargs):
        raise httpx.ConnectError("network unavailable")

    monkeypatch.setattr("minerva_travel.app.fetch_landmark_asset", fake_fetch_landmark_asset)

    assert fetch_custom_wikimedia_assets(destinations, "request-123") == {}


def test_fetch_custom_wikimedia_assets_skips_landmarks_with_provided_image(monkeypatch):
    destinations, _selected = custom_destinations_from_form(
        json.dumps(
            [
                {
                    "name": "Torre Eiffel",
                    "city": "Paris",
                    "country": "Franca",
                    "description": ["A torre foi escolhida no roteiro."],
                    "image": "https://lh3.googleusercontent.com/place-photo=w900",
                }
            ]
        )
    )

    def fake_fetch_landmark_asset(*_args, **_kwargs):
        raise AssertionError("Wikimedia should not run when the card image is already available")

    monkeypatch.setattr("minerva_travel.app.fetch_landmark_asset", fake_fetch_landmark_asset)

    assert fetch_custom_wikimedia_assets(destinations, "request-123") == {}


def test_selected_landmark_art_generates_multiple_landmarks_concurrently(monkeypatch):
    destinations, selected = custom_destinations_from_form(
        "Cristo Redentor, Rio de Janeiro, Brasil\nUsina do Gasometro, Porto Alegre, Brasil"
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
