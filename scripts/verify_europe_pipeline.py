import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from minerva_travel import storage
from minerva_travel.app import app
from minerva_travel.config import load_project_env
from minerva_travel.models import DynamicItineraryRequest
from minerva_travel.place_discovery import discover_dynamic_itinerary


@dataclass(frozen=True)
class Scenario:
    id: str
    country: str
    country_terms: tuple[str, ...]
    prompt: str
    expected_groups: tuple[tuple[str, ...], ...]
    interests: tuple[str, ...]


SCENARIOS = [
    Scenario(
        id="france_paris",
        country="Franca",
        country_terms=("franca", "france"),
        prompt=(
            "Vamos viajar para Paris, Franca, com as criancas. Pontos obrigatorios: "
            "Torre Eiffel e Museu do Louvre. Tambem queremos lugares educativos e "
            "bonitos para explorar em familia."
        ),
        expected_groups=(("eiffel",), ("louvre",)),
        interests=("historia", "museus", "arte"),
    ),
    Scenario(
        id="italy_rome",
        country="Italia",
        country_terms=("italia", "italy"),
        prompt=(
            "Vamos viajar para Roma, Italia, com as criancas. Pontos obrigatorios: "
            "Coliseu e Fontana di Trevi. Tambem queremos historia antiga e lugares "
            "classicos para familia."
        ),
        expected_groups=(("coliseu", "colosseum", "colosseo"), ("trevi",)),
        interests=("historia", "museus", "arte"),
    ),
    Scenario(
        id="spain_barcelona",
        country="Espanha",
        country_terms=("espanha", "spain"),
        prompt=(
            "Vamos viajar para Barcelona, Espanha, com as criancas. Pontos obrigatorios: "
            "Sagrada Familia e Park Guell. Tambem queremos arte, arquitetura e um "
            "passeio educativo."
        ),
        expected_groups=(("sagrada",), ("guell",)),
        interests=("arte", "historia", "parques"),
    ),
    Scenario(
        id="portugal_lisbon",
        country="Portugal",
        country_terms=("portugal",),
        prompt=(
            "Vamos viajar para Lisboa, Portugal, com as criancas. Pontos obrigatorios: "
            "Torre de Belem e Mosteiro dos Jeronimos. Tambem queremos rio, historia "
            "e atividades familiares."
        ),
        expected_groups=(("belem",), ("jeronimos",)),
        interests=("historia", "rio", "museus"),
    ),
    Scenario(
        id="uk_london",
        country="Reino Unido",
        country_terms=("reino unido", "united kingdom", "inglaterra", "england"),
        prompt=(
            "Vamos viajar para Londres, Reino Unido, com as criancas. Pontos "
            "obrigatorios: Big Ben e Tower Bridge. Tambem queremos museus e "
            "lugares educativos para criancas."
        ),
        expected_groups=(("big", "ben"), ("tower", "bridge")),
        interests=("historia", "museus", "vistas"),
    ),
    Scenario(
        id="germany_berlin",
        country="Alemanha",
        country_terms=("alemanha", "germany", "deutschland"),
        prompt=(
            "Vamos viajar para Berlim, Alemanha, com as criancas. Pontos obrigatorios: "
            "Portao de Brandemburgo e Ilha dos Museus. Tambem queremos historia, "
            "ciencia e lugares educativos."
        ),
        expected_groups=(("brandemburgo", "brandenburg"), ("museus", "museum", "museums")),
        interests=("historia", "museus", "science"),
    ),
]

FOOD_INTERESTS = {"food", "comida", "gastronomia", "almoco", "almoço", "jantar", "restaurante"}
FAMILY_UNSAFE_NAME_TERMS = {"casino", "nightclub", "discoteca", "adult", "strip", "lust"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test real Minerva Travel pipeline across European destinations."
    )
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N scenarios.")
    parser.add_argument(
        "--output-dir",
        default="runtime/europe-pipeline-smoke",
        help="Directory for reports and rendered artifacts.",
    )
    parser.add_argument(
        "--min-stops",
        type=int,
        default=3,
        help="Minimum selected stops expected per country.",
    )
    args = parser.parse_args()

    load_project_env()
    os.environ["IMAGE_PROVIDER"] = "placeholder"
    os.environ["LANDMARK_ART_GENERATION"] = "false"

    missing_keys = [key for key in ("GOOGLE_MAPS_API_KEY", "OPENAI_API_KEY") if not os.getenv(key)]
    if missing_keys:
        print(f"Missing required environment keys: {', '.join(missing_keys)}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    family_photo = output_dir / "family-photo.png"
    create_family_photo(family_photo)

    scenarios = SCENARIOS[: args.limit] if args.limit else SCENARIOS
    client = TestClient(app)
    report: dict[str, Any] = {"scenarios": [], "failures": []}

    for scenario in scenarios:
        print(f"\n=== {scenario.id}: {scenario.country} ===", flush=True)
        scenario_report: dict[str, Any] = {"id": scenario.id, "country": scenario.country}
        failures: list[str] = []
        try:
            parse_report, parse_failures = verify_parse_endpoint(client, scenario)
            scenario_report["parse"] = parse_report
            failures.extend(parse_failures)

            discovery_report, selected_stops, discovery_failures = verify_discovery(
                scenario,
                min_stops=args.min_stops,
            )
            scenario_report["discovery"] = discovery_report
            failures.extend(discovery_failures)

            map_report, map_failures = verify_map_payload(selected_stops)
            scenario_report["maps"] = map_report
            failures.extend(map_failures)

            pdf_report, pdf_failures = verify_pdf_generation(
                client,
                scenario,
                selected_stops,
                family_photo,
                output_dir,
            )
            scenario_report["pdf"] = pdf_report
            failures.extend(pdf_failures)
        except Exception as error:  # noqa: BLE001 - report full smoke failure and continue.
            failures.append(f"Unexpected error: {type(error).__name__}: {error}")

        scenario_report["failures"] = failures
        report["scenarios"].append(scenario_report)
        if failures:
            report["failures"].append({"id": scenario.id, "failures": failures})
            for failure in failures:
                print(f"  FAIL: {failure}", flush=True)
        else:
            print("  OK", flush=True)

    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport: {report_path}")

    if report["failures"]:
        print(f"FAILED scenarios: {len(report['failures'])}/{len(scenarios)}", file=sys.stderr)
        return 1

    print(f"All scenarios passed: {len(scenarios)}/{len(scenarios)}")
    return 0


def verify_parse_endpoint(
    client: TestClient,
    scenario: Scenario,
) -> tuple[dict[str, Any], list[str]]:
    response = client.post("/api/landmarks/parse", json={"message": scenario.prompt})
    if response.status_code != 200:
        return {"status_code": response.status_code, "body": response.text[:1000]}, [
            f"/api/landmarks/parse returned {response.status_code}"
        ]

    payload = response.json()
    landmarks = [
        landmark
        for destination in payload.get("destinations", [])
        for landmark in destination.get("landmarks", [])
    ]
    names = [str(landmark.get("name", "")) for landmark in landmarks]
    failures: list[str] = []

    if not landmarks:
        failures.append("parse returned no landmarks")
    for group in scenario.expected_groups:
        if not any(matches_group(name, group) for name in names):
            failures.append(f"parse did not find cited place group: {group}")

    missing_coordinates = [
        name
        for name, landmark in zip(names, landmarks, strict=False)
        if not has_coordinates(landmark)
    ]
    if missing_coordinates:
        failures.append(f"parse landmarks missing coordinates: {missing_coordinates[:4]}")

    return {
        "landmark_count": len(landmarks),
        "names": names,
        "selected_landmarks": payload.get("selected_landmarks", []),
    }, failures


def verify_discovery(
    scenario: Scenario,
    *,
    min_stops: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    recommendation = discover_dynamic_itinerary(
        DynamicItineraryRequest(
            destination=scenario.prompt,
            days=1,
            interests=list(scenario.interests),
            pace="full",
            children_ages=[],
            must_see=[],
        ),
        api_key=os.getenv("GOOGLE_MAPS_API_KEY"),
    )
    selected_stops = [
        stop for day in recommendation.get("days", []) for stop in day.get("stops", [])
    ]
    all_stops = [*selected_stops, *recommendation.get("alternatives", [])]
    stop_names = [str(stop.get("name", "")) for stop in selected_stops]
    all_names = [str(stop.get("name", "")) for stop in all_stops]
    resolved = recommendation.get("resolved_destination", {})
    failures: list[str] = []

    resolved_country = str(resolved.get("country", ""))
    if not any(term in normalize(resolved_country) for term in scenario.country_terms):
        failures.append(
            f"resolved country mismatch: expected {scenario.country}, got {resolved_country}"
        )

    if len(selected_stops) < min_stops:
        failures.append(f"selected only {len(selected_stops)} stops, expected at least {min_stops}")

    for group in scenario.expected_groups:
        if not any(matches_group(name, group) for name in all_names):
            failures.append(f"discovery did not find cited place group: {group}")

    missing_coordinates = [
        str(stop.get("name", "")) for stop in selected_stops if not has_coordinates(stop)
    ]
    if missing_coordinates:
        failures.append(f"selected stops missing coordinates: {missing_coordinates[:4]}")

    missing_images = [str(stop.get("name", "")) for stop in selected_stops if not stop.get("image")]
    if missing_images:
        failures.append(f"selected stops missing Google photo image: {missing_images[:4]}")

    if not any(normalize(interest) in FOOD_INTERESTS for interest in scenario.interests):
        food_stops = [
            str(stop.get("name", ""))
            for stop in selected_stops
            if "food" in set(stop.get("categories", []))
        ]
        if food_stops:
            failures.append(f"food stops selected without a food request: {food_stops[:4]}")

    unsafe_name_stops = [
        str(stop.get("name", ""))
        for stop in selected_stops
        if any(term in normalize(str(stop.get("name", ""))) for term in FAMILY_UNSAFE_NAME_TERMS)
    ]
    if unsafe_name_stops:
        failures.append(f"family-incompatible stop names selected: {unsafe_name_stops[:4]}")

    return (
        {
            "resolved_destination": resolved,
            "selected_count": len(selected_stops),
            "selected_names": stop_names,
            "alternative_count": len(recommendation.get("alternatives", [])),
            "selected_with_images": len([stop for stop in selected_stops if stop.get("image")]),
        },
        selected_stops,
        failures,
    )


def verify_map_payload(selected_stops: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    mappable = [stop for stop in selected_stops if has_coordinates(stop)]
    embedded_point_maps = [
        stop for stop in selected_stops if has_coordinates(stop) and build_maps_url(stop)
    ]

    if len(mappable) != len(selected_stops):
        failures.append("trip map cannot show every selected stop")
    if len(embedded_point_maps) != len(selected_stops):
        failures.append("point map action cannot open every selected stop")

    return {
        "selected_count": len(selected_stops),
        "trip_map_visible_count": len(mappable),
        "point_map_embedded_count": len(embedded_point_maps),
    }, failures


def verify_pdf_generation(
    client: TestClient,
    scenario: Scenario,
    selected_stops: list[dict[str, Any]],
    family_photo: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    custom_landmarks = [
        {
            "name": stop["name"],
            "city": stop["city"],
            "country": stop["country"],
            "description": stop.get("description")
            or [f"{stop['name']} faz parte do roteiro da familia."],
            "image": stop.get("image"),
            "image_attributions": stop.get("image_attributions") or [],
        }
        for stop in selected_stops
    ]
    response = client.post(
        "/api/generate",
        data={
            "title": f"Familia Smoke {scenario.country}",
            "children_names": "Alice, Bento",
            "parents_names": "Ana, Otavio",
            "year": "2026",
            "custom_landmarks": json.dumps(custom_landmarks, ensure_ascii=False),
        },
        files={"family_photo": ("family.png", family_photo.read_bytes(), "image/png")},
    )
    if response.status_code != 200:
        return {"status_code": response.status_code, "body": response.text[:1000]}, [
            f"/api/generate returned {response.status_code}"
        ]

    payload = response.json()
    request_id = payload["request_id"]
    pdf_path = storage.pdf_path(payload["filename"])
    copied_pdf_path = output_dir / f"{scenario.id}.pdf"
    copied_pdf_path.write_bytes(pdf_path.read_bytes())

    custom_image_dir = storage.RUNTIME_DIR / "custom-images" / request_id
    custom_images = sorted(custom_image_dir.rglob("*")) if custom_image_dir.exists() else []
    custom_images = [path for path in custom_images if path.is_file()]
    image_checks = inspect_downloaded_images(custom_images)
    pdf_images = inspect_pdf_images(pdf_path)
    large_pdf_images = [
        image for image in pdf_images if image["size_bytes"] >= 25_000 and image["width"] >= 200
    ]
    failures: list[str] = []

    if len(custom_images) < len(selected_stops):
        failures.append(
            f"downloaded {len(custom_images)} landmark images, expected {len(selected_stops)}"
        )
    too_small = [item for item in image_checks if item["size_bytes"] < 15_000]
    if too_small:
        failures.append(f"downloaded image too small or placeholder-like: {too_small[:3]}")
    if len(large_pdf_images) < len(selected_stops):
        failures.append(
            f"PDF has {len(large_pdf_images)} substantial images, "
            f"expected at least {len(selected_stops)}"
        )
    if pdf_path.stat().st_size < 500_000:
        failures.append(f"PDF too small for image-rich guide: {pdf_path.stat().st_size} bytes")

    return {
        "request_id": request_id,
        "pdf_path": str(copied_pdf_path),
        "pdf_size_bytes": pdf_path.stat().st_size,
        "downloaded_images": image_checks,
        "pdf_image_count": len(pdf_images),
        "substantial_pdf_image_count": len(large_pdf_images),
    }, failures


def create_family_photo(path: Path) -> None:
    image = Image.new("RGB", (900, 650), "#d8ebf1")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def inspect_downloaded_images(paths: list[Path]) -> list[dict[str, Any]]:
    checks = []
    for path in paths:
        try:
            with Image.open(path) as image:
                width, height = image.size
        except OSError:
            width, height = 0, 0
        checks.append(
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "width": width,
                "height": height,
            }
        )
    return checks


def inspect_pdf_images(pdf_path: Path) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["pdfimages", "-list", str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    images = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 16 or not parts[0].isdigit():
            continue
        images.append(
            {
                "page": int(parts[0]),
                "width": int(parts[3]),
                "height": int(parts[4]),
                "encoding": parts[8],
                "size": parts[14],
                "size_bytes": parse_pdfimages_size(parts[14]),
            }
        )
    return images


def parse_pdfimages_size(value: str) -> int:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([KMG]?)", value)
    if not match:
        return 0
    amount = float(match.group(1))
    unit = match.group(2)
    multiplier = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[unit]
    return int(amount * multiplier)


def has_coordinates(item: dict[str, Any]) -> bool:
    return isinstance(item.get("latitude"), int | float) and isinstance(
        item.get("longitude"),
        int | float,
    )


def build_maps_url(stop: dict[str, Any]) -> str:
    if stop.get("google_maps_uri"):
        return str(stop["google_maps_uri"])
    query = " ".join(
        str(stop.get(key, "")).strip() for key in ("name", "city", "country") if stop.get(key)
    )
    return f"https://www.google.com/maps/search/?api=1&query={query}" if query else ""


def matches_group(value: str, group: tuple[str, ...]) -> bool:
    normalized_value = normalize(value)
    normalized_terms = [normalize(term) for term in group]
    if len(normalized_terms) == 1:
        return normalized_terms[0] in normalized_value
    return all(term in normalized_value for term in normalized_terms) or any(
        term in normalized_value for term in normalized_terms
    )


def normalize(value: str) -> str:
    without_accents = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return " ".join(without_accents.casefold().split())


if __name__ == "__main__":
    raise SystemExit(main())
