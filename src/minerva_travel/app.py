import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from minerva_travel import storage
from minerva_travel.catalog import load_catalog
from minerva_travel.config import (
    cors_allowed_origins,
    google_maps_api_key,
    image_generation_concurrency,
    image_provider,
)
from minerva_travel.custom_landmarks import (
    CustomLandmarkInput,
    build_custom_destinations,
    merge_custom_destinations,
    parse_custom_landmarks,
)
from minerva_travel.guide_builder import build_guide_context
from minerva_travel.image_generation import get_image_generator
from minerva_travel.itinerary import recommend_itinerary
from minerva_travel.landmark_parser import ParsedLandmark, parse_landmarks_from_message
from minerva_travel.models import (
    Destination,
    DynamicItineraryRequest,
    GuideRequest,
    ItineraryRecommendationRequest,
)
from minerva_travel.pdf import render_guide_html, write_pdf
from minerva_travel.place_discovery import discover_dynamic_itinerary
from minerva_travel.wikimedia_assets import WikimediaAsset, load_wikimedia_manifest
from minerva_travel.wikimedia_client import (
    USER_AGENT,
    fetch_landmark_asset,
    find_landmark_asset_metadata,
)

TEMPLATE_DIR = Path(__file__).parent / "templates"

app = FastAPI(title="Minerva Travel MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def web_templates() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )


class CustomLandmarksResolveRequest(BaseModel):
    landmarks: str


class LandmarkParseRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    catalog = load_catalog()
    template = web_templates().get_template("form.html")
    return template.render(catalog=catalog)


@app.get("/api/catalog")
def api_catalog() -> dict[str, object]:
    catalog = load_catalog()
    return {
        "id": catalog.id,
        "title": catalog.title,
        "destinations": [
            {
                "id": destination.id,
                "country": destination.country,
                "city": destination.city,
                "display_title": destination.display_title,
                "intro": destination.intro,
                "landmarks": [
                    {
                        "id": landmark.id,
                        "selection_id": f"{destination.id}:{landmark.id}",
                        "name": landmark.name,
                        "description": landmark.description,
                        "sort_order": landmark.sort_order,
                        "categories": landmark.categories,
                        "duration_minutes": landmark.duration_minutes,
                        "family_tip": landmark.family_tip,
                    }
                    for landmark in destination.landmarks
                ],
            }
            for destination in catalog.destinations
        ],
    }


@app.post("/api/itinerary/recommend")
def api_recommend_itinerary(payload: ItineraryRecommendationRequest) -> dict[str, object]:
    catalog = load_catalog()
    try:
        recommendation = recommend_itinerary(catalog, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return recommendation.model_dump(mode="json")


@app.post("/api/itinerary/discover")
def api_discover_itinerary(payload: DynamicItineraryRequest) -> dict[str, object]:
    try:
        return discover_dynamic_itinerary(payload, api_key=google_maps_api_key())
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except httpx.HTTPStatusError as error:
        detail = "Google Places nao conseguiu montar o roteiro."
        if error.response.status_code in {401, 403}:
            detail = "Google Places nao esta habilitado ou a chave nao tem permissao suficiente."
        raise HTTPException(status_code=502, detail=detail) from error


@app.post("/api/custom-landmarks/resolve")
def resolve_custom_landmarks(payload: CustomLandmarksResolveRequest) -> dict[str, object]:
    try:
        custom_landmarks = parse_custom_landmarks(payload.landmarks)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    custom_destinations, selected_landmarks = build_custom_destinations(custom_landmarks)
    return {
        "selected_landmarks": selected_landmarks,
        "destinations": [
            {
                "id": destination.id,
                "country": destination.country,
                "city": destination.city,
                "display_title": destination.display_title,
                "landmarks": [
                    {
                        "id": landmark.id,
                        "selection_id": f"{destination.id}:{landmark.id}",
                        "name": landmark.name,
                        "description": landmark.description,
                        "representative_query": landmark.representative_query,
                        "required_terms": landmark.required_terms,
                    }
                    for landmark in destination.landmarks
                ],
            }
            for destination in custom_destinations
        ],
    }


@app.post("/api/landmarks/parse")
def parse_landmarks(payload: LandmarkParseRequest) -> dict[str, object]:
    try:
        parsed_landmarks = parse_landmarks_from_message(payload.message)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ValueError, httpx.HTTPError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if not parsed_landmarks:
        raise HTTPException(
            status_code=400,
            detail="Nao encontrei pontos turisticos claros na mensagem.",
        )

    custom_inputs = [
        CustomLandmarkInput(
            name=item["name"] if isinstance(item, dict) else item.name,
            city=item["city"] if isinstance(item, dict) else item.city,
            country=item["country"] if isinstance(item, dict) else item.country,
            description=_parsed_landmark_description(item),
        )
        for item in parsed_landmarks
    ]
    custom_destinations, selected_landmarks = build_custom_destinations(custom_inputs)
    return {
        "custom_landmarks": json.dumps(
            [
                {
                    "name": landmark.name,
                    "city": landmark.city,
                    "country": landmark.country,
                    "description": landmark.description,
                }
                for landmark in custom_inputs
            ],
            ensure_ascii=False,
        ),
        "selected_landmarks": selected_landmarks,
        "destinations": serialize_preview_destinations(
            custom_destinations,
            parsed_landmarks,
            {},
        ),
    }


def _parsed_landmark_description(item: ParsedLandmark | dict[str, object]) -> list[str]:
    raw_description = item.get("description", []) if isinstance(item, dict) else item.description
    if not isinstance(raw_description, list):
        return []
    return [str(paragraph).strip() for paragraph in raw_description if str(paragraph).strip()]


@app.post("/api/landmarks/parse-preview")
def parse_preview_landmarks(payload: LandmarkParseRequest) -> dict[str, object]:
    return parse_landmarks(payload)


@app.get("/preview/sample", response_class=HTMLResponse)
def preview_sample() -> str:
    catalog = load_catalog()
    selected = [
        f"{destination.id}:{landmark.id}"
        for destination in catalog.destinations
        for landmark in destination.landmarks
    ]
    request = GuideRequest(
        title=catalog.title,
        children_names=["Alice", "Antonio"],
        parents_names=["Ana", "Otavio"],
        year=2026,
        selected_landmarks=selected,
    )
    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/representative-full-cover.png"),
        wikimedia_assets=load_wikimedia_manifest(),
    )
    return render_guide_html(context, preview=True)


@app.post("/generate", response_class=HTMLResponse)
async def generate(
    title: Annotated[str, Form()],
    children_names: Annotated[str, Form()],
    parents_names: Annotated[str, Form()],
    year: Annotated[int, Form()],
    family_photo: Annotated[UploadFile, File()],
    selected_landmarks: Annotated[list[str] | None, Form()] = None,
    custom_landmarks: Annotated[str | None, Form()] = None,
) -> str:
    result = await generate_pdf_from_form(
        title=title,
        children_names=children_names,
        parents_names=parents_names,
        year=year,
        selected_landmarks=selected_landmarks or [],
        custom_landmarks=custom_landmarks,
        family_photo=family_photo,
    )

    template = web_templates().get_template("result.html")
    return template.render(download_url=result["download_url"], request=result["request"])


@app.post("/api/generate")
async def api_generate(
    title: Annotated[str, Form()],
    children_names: Annotated[str, Form()],
    parents_names: Annotated[str, Form()],
    year: Annotated[int, Form()],
    family_photo: Annotated[UploadFile, File()],
    selected_landmarks: Annotated[list[str] | None, Form()] = None,
    custom_landmarks: Annotated[str | None, Form()] = None,
) -> dict[str, str]:
    result = await generate_pdf_from_form(
        title=title,
        children_names=children_names,
        parents_names=parents_names,
        year=year,
        selected_landmarks=selected_landmarks or [],
        custom_landmarks=custom_landmarks,
        family_photo=family_photo,
    )
    return {
        "request_id": result["request_id"],
        "download_url": result["download_url"],
        "filename": result["filename"],
    }


@app.get("/download/{filename}")
def download(filename: str) -> FileResponse:
    path = storage.pdf_path(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(path, media_type="application/pdf", filename="minerva-travel-guide.pdf")


async def generate_pdf_from_form(
    title: str,
    children_names: str,
    parents_names: str,
    year: int,
    selected_landmarks: list[str],
    family_photo: UploadFile,
    custom_landmarks: str | None = None,
) -> dict[str, object]:
    catalog = load_catalog()
    custom_destinations, custom_selected = custom_destinations_from_form(custom_landmarks)
    selected = [*selected_landmarks, *custom_selected]
    if not selected:
        raise HTTPException(
            status_code=400,
            detail="Selecione ou informe pelo menos um ponto turistico.",
        )
    if custom_destinations:
        catalog = catalog.model_copy(
            update={
                "destinations": merge_custom_destinations(
                    catalog.destinations,
                    custom_destinations,
                )
            }
        )
    request = GuideRequest(
        title=title,
        children_names=_split_names(children_names),
        parents_names=_split_names(parents_names),
        year=year,
        selected_landmarks=selected,
    )
    request_id = uuid4().hex
    photo_path = await storage.save_upload(family_photo)
    cover_landmark_names = selected_landmark_names(catalog.destinations, selected)
    cover_path = storage.generated_path(f"{request_id}-cover.png")
    generator = get_image_generator(image_provider())
    generator.generate_cover(
        family_photo=photo_path,
        output_path=cover_path,
        title=request.title,
        destination_names=cover_landmark_names,
    )

    wikimedia_assets = load_wikimedia_manifest()
    wikimedia_assets.update(fetch_custom_wikimedia_assets(custom_destinations, request_id))
    landmark_reference_images = {
        selection_id: asset.local_path
        for selection_id, asset in wikimedia_assets.items()
        if selection_id in selected
    }

    landmark_images, landmark_lineart_images = generate_selected_landmark_art(
        catalog.destinations,
        selected,
        request_id,
        generator,
        reference_images=landmark_reference_images,
    )
    context = build_guide_context(
        request,
        catalog,
        cover_path,
        wikimedia_assets=wikimedia_assets,
        landmark_images=landmark_images,
        landmark_lineart_images=landmark_lineart_images,
    )
    pdf_output = storage.pdf_path(f"{request_id}.pdf")
    write_pdf(context, pdf_output)
    return {
        "request": request,
        "request_id": request_id,
        "filename": pdf_output.name,
        "download_url": f"/download/{pdf_output.name}",
    }


def _split_names(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def selected_landmark_names(destinations: list[Destination], selected: list[str]) -> list[str]:
    selected_ids = set(selected)
    names: list[str] = []
    for destination in destinations:
        for landmark in destination.landmarks:
            if f"{destination.id}:{landmark.id}" in selected_ids:
                names.append(landmark.name)
    return names


def generate_selected_landmark_art(
    destinations: list[Destination],
    selected: list[str],
    request_id: str,
    generator,
    reference_images: dict[str, Path] | None = None,
) -> tuple[dict[str, Path], dict[str, Path]]:
    selected_ids = set(selected)
    reference_images = reference_images or {}
    image_output_dir = Path("runtime/generated/landmarks") / request_id
    lineart_output_dir = Path("runtime/generated/lineart") / request_id
    generation_jobs = []
    for destination in destinations:
        for landmark in destination.landmarks:
            selection_id = f"{destination.id}:{landmark.id}"
            if selection_id not in selected_ids:
                continue
            image_output_path = image_output_dir / destination.id / f"{landmark.id}.png"
            lineart_output_path = lineart_output_dir / destination.id / f"{landmark.id}.png"
            generation_jobs.append(
                (
                    selection_id,
                    landmark.name,
                    destination.city,
                    destination.country,
                    image_output_path,
                    lineart_output_path,
                    reference_images.get(selection_id),
                )
            )

    if not generation_jobs:
        return {}, {}

    max_workers = min(image_generation_concurrency(), len(generation_jobs))
    images: dict[str, Path] = {}
    lineart_images: dict[str, Path] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _generate_landmark_art_pair,
                generator,
                *generation_job,
            ): generation_job[0]
            for generation_job in generation_jobs
        }
        for future in as_completed(futures):
            selection_id, image_path, lineart_path = future.result()
            images[selection_id] = image_path
            lineart_images[selection_id] = lineart_path
    return images, lineart_images


def _generate_landmark_art_pair(
    generator,
    selection_id: str,
    landmark_name: str,
    city: str,
    country: str,
    image_output_path: Path,
    lineart_output_path: Path,
    reference_image: Path | None = None,
) -> tuple[str, Path, Path]:
    image_path = reference_image or generator.generate_landmark_image(
        landmark_name=landmark_name,
        city=city,
        country=country,
        output_path=image_output_path,
    )
    lineart_path = generator.generate_landmark_lineart(
        landmark_name=landmark_name,
        city=city,
        country=country,
        reference_image=image_path,
        output_path=lineart_output_path,
    )
    return selection_id, image_path, lineart_path


def custom_destinations_from_form(raw: str | None) -> tuple[list[Destination], list[str]]:
    try:
        custom_landmarks = parse_custom_landmarks(raw)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    custom_landmarks = enrich_missing_custom_descriptions(custom_landmarks)
    return build_custom_destinations(custom_landmarks)


def enrich_missing_custom_descriptions(
    custom_landmarks: list[CustomLandmarkInput],
) -> list[CustomLandmarkInput]:
    if not custom_landmarks or all(landmark.description for landmark in custom_landmarks):
        return custom_landmarks

    message = "\n".join(
        f"{landmark.name}, {landmark.city}, {landmark.country}"
        for landmark in custom_landmarks
    )
    try:
        parsed_landmarks = parse_landmarks_from_message(message)
    except (RuntimeError, ValueError, httpx.HTTPError):
        return custom_landmarks

    descriptions_by_key = {
        _landmark_description_key(
            item["name"] if isinstance(item, dict) else item.name,
            item["city"] if isinstance(item, dict) else item.city,
            item["country"] if isinstance(item, dict) else item.country,
        ): _parsed_landmark_description(item)
        for item in parsed_landmarks
    }
    descriptions_by_name = {
        _normalize_landmark_text(item["name"] if isinstance(item, dict) else item.name): (
            _parsed_landmark_description(item)
        )
        for item in parsed_landmarks
    }

    enriched: list[CustomLandmarkInput] = []
    for landmark in custom_landmarks:
        if landmark.description:
            enriched.append(landmark)
            continue
        description = descriptions_by_key.get(
            _landmark_description_key(landmark.name, landmark.city, landmark.country)
        ) or descriptions_by_name.get(_normalize_landmark_text(landmark.name), [])
        enriched.append(
            landmark.model_copy(update={"description": description})
            if description
            else landmark
        )
    return enriched


def _landmark_description_key(name: str, city: str, country: str) -> tuple[str, str, str]:
    return (
        _normalize_landmark_text(name),
        _normalize_landmark_text(city),
        _normalize_landmark_text(country),
    )


def _normalize_landmark_text(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def fetch_custom_wikimedia_assets(
    destinations: list[Destination],
    request_id: str,
) -> dict[str, WikimediaAsset]:
    if not destinations:
        return {}
    output_dir = Path("runtime/wikimedia/custom") / request_id
    assets: dict[str, WikimediaAsset] = {}
    with httpx.Client(
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for destination in destinations:
            for landmark in destination.landmarks:
                selection_id = f"{destination.id}:{landmark.id}"
                try:
                    asset = fetch_landmark_asset(client, destination, landmark, output_dir)
                except httpx.HTTPStatusError:
                    asset = None
                if asset:
                    assets[selection_id] = asset
    return assets


def fetch_preview_wikimedia_assets(
    destinations: list[Destination],
    _request_id: str,
) -> dict[str, object]:
    if not destinations:
        return {}
    assets: dict[str, object] = {}
    with httpx.Client(
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for destination in destinations:
            for landmark in destination.landmarks:
                selection_id = f"{destination.id}:{landmark.id}"
                try:
                    asset = find_landmark_asset_metadata(client, destination, landmark)
                except httpx.HTTPStatusError:
                    asset = None
                if asset:
                    assets[selection_id] = asset
    return assets


def serialize_preview_destinations(
    destinations: list[Destination],
    parsed_landmarks: list[ParsedLandmark] | list[dict[str, object]],
    images: dict[str, object],
) -> list[dict[str, object]]:
    confidence_by_name = {
        (item["name"] if isinstance(item, dict) else item.name): (
            item["confidence"] if isinstance(item, dict) else item.confidence
        )
        for item in parsed_landmarks
    }
    return [
        {
            "id": destination.id,
            "country": destination.country,
            "city": destination.city,
            "display_title": destination.display_title,
            "landmarks": [
                {
                    "id": landmark.id,
                    "selection_id": f"{destination.id}:{landmark.id}",
                    "name": landmark.name,
                    "description": landmark.description,
                    "representative_query": landmark.representative_query,
                    "confidence": confidence_by_name.get(landmark.name, 0),
                    "image": serialize_preview_image(images.get(f"{destination.id}:{landmark.id}")),
                }
                for landmark in destination.landmarks
            ],
        }
        for destination in destinations
    ]


def serialize_preview_image(image: object) -> dict[str, str] | None:
    if image is None:
        return None
    if isinstance(image, dict):
        return {
            "image_url": str(image.get("image_url", "")),
            "source_url": str(image.get("source_url", "")),
            "author": str(image.get("author", "")),
            "license_short_name": str(image.get("license_short_name", "")),
            "license_url": str(image.get("license_url", "")),
        }
    if not isinstance(image, WikimediaAsset):
        return None
    return {
        "image_url": image.image_url,
        "source_url": image.source_url,
        "author": image.author,
        "license_short_name": image.license_short_name,
        "license_url": image.license_url,
    }
