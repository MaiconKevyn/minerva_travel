import hashlib
import json
import os
import re
import sqlite3
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any, Literal
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from minerva_travel import storage
from minerva_travel.asset_policy import (
    AssetProvenanceError,
    assert_selected_asset_provenance,
    asset_provenance_required,
)
from minerva_travel.auth import CurrentUser
from minerva_travel.catalog import load_catalog
from minerva_travel.config import (
    app_environment,
    async_guide_jobs_enabled,
    coloring_lineart_generation_enabled,
    cors_allowed_origins,
    frontend_base_url,
    google_maps_api_key,
    guide_job_max_attempts,
    image_generation_concurrency,
    image_provider,
    landmark_art_generation_enabled,
    pilot_restaurant_recommendations_enabled,
)
from minerva_travel.contract_limits import (
    MAX_GUIDE_CHILDREN,
    MAX_GUIDE_DESTINATIONS,
    MAX_GUIDE_LANDMARKS,
    MAX_GUIDE_PARENTS,
    MAX_GUIDE_YEAR,
    MAX_VISIBLE_FAMILY_MEMBERS,
    MIN_GUIDE_YEAR,
    public_contract_limits,
)
from minerva_travel.custom_landmarks import (
    CustomLandmarkInput,
    build_custom_destinations,
    merge_custom_destinations,
    parse_custom_landmarks,
    slugify,
)
from minerva_travel.guide_builder import build_guide_context
from minerva_travel.image_generation import (
    CoverGenerationResult,
    generate_cover_with_guardrails,
    get_cover_image_validator,
    get_image_generator,
    simplify_child_coloring_lineart,
)
from minerva_travel.itinerary import recommend_itinerary
from minerva_travel.itinerary_routes import suggest_itinerary_routes
from minerva_travel.landmark_parser import ParsedLandmark, parse_landmarks_from_message
from minerva_travel.models import (
    Destination,
    DynamicItineraryRequest,
    GuideDestinationPlan,
    GuideItineraryDayPlan,
    GuideItineraryPlan,
    GuideItineraryStopPlan,
    GuideRequest,
    ItineraryRecommendation,
    ItineraryRecommendationRequest,
    Landmark,
    RouteSuggestionRequest,
    RouteSuggestionResponse,
    StrictRequestModel,
)
from minerva_travel.observability import emit_event
from minerva_travel.pdf import render_guide_html, write_pdf
from minerva_travel.persistence import (
    GuideJobRecord,
    delete_guide_and_assets,
    delete_private_asset,
    guide_repository,
    purge_all_data_for_owner,
)
from minerva_travel.place_discovery import discover_dynamic_itinerary, resolve_landmark_locations
from minerva_travel.privacy import (
    PrivacyConsent,
    PrivacyConsentError,
    validate_photo_processing_consent,
)
from minerva_travel.request_control import (
    ConcurrencyLease,
    IdempotencyInProgressError,
    IdempotencyKeyRequiredError,
    IdempotencyReservation,
    RequestControlError,
    SQLiteRequestControl,
    configured_concurrency_lease_seconds,
    configured_idempotency_pending_ttl_seconds,
    configured_idempotency_ttl_seconds,
    configured_provider_concurrency_limit,
    configured_quota_period_seconds,
    configured_rate_policy,
    configured_user_concurrency_limit,
    configured_user_quota,
    get_request_control,
    idempotency_key_required,
    request_controls_enabled,
    stable_request_hash,
)
from minerva_travel.restaurant_recommendations import discover_restaurants_for_guide
from minerva_travel.supabase_storage import sync_wikimedia_assets_to_storage
from minerva_travel.wikimedia_assets import WikimediaAsset, load_wikimedia_manifest
from minerva_travel.wikimedia_client import (
    USER_AGENT,
    fetch_landmark_asset,
    find_landmark_asset_metadata,
)

CUSTOM_LANDMARK_IMAGE_HOSTS = {
    "lh3.googleusercontent.com",
    "upload.wikimedia.org",
    "images.unsplash.com",
    "plus.unsplash.com",
}
CUSTOM_LANDMARK_IMAGE_MAX_BYTES = 10 * 1024 * 1024
LINEART_CANVAS_SIZE = (1200, 850)


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    field_errors: list[dict[str, Any]]
    request_id: str
    detail: Any = None


class CatalogLandmarkResponse(BaseModel):
    id: str
    selection_id: str
    name: str
    description: list[str]
    sort_order: int
    categories: list[str]
    duration_minutes: int
    family_tip: str | None = None


class CatalogDestinationResponse(BaseModel):
    id: str
    country: str
    city: str
    display_title: str
    intro: list[str]
    landmarks: list[CatalogLandmarkResponse]


class CatalogResponse(BaseModel):
    id: str
    title: str
    destinations: list[CatalogDestinationResponse]


class HealthLiveResponse(BaseModel):
    status: Literal["ok"]


class HealthChecksResponse(BaseModel):
    database: Literal["ok"]
    storage: Literal["ok"]


class HealthReadyResponse(BaseModel):
    status: Literal["ok"]
    checks: HealthChecksResponse


class GuideResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    expires_at: str | None = None
    cover_fallback_used: bool
    destinations: list[dict[str, Any]]
    download_url: str | None = None


class GuideListResponse(BaseModel):
    guides: list[GuideResponse]


class GuideDraftResponse(BaseModel):
    id: str
    title: str
    payload: dict[str, Any]
    revision: int
    status: str
    created_at: str
    updated_at: str
    expires_at: str | None = None


class CurrentGuideDraftResponse(BaseModel):
    draft: GuideDraftResponse | None


class DeletedResponse(BaseModel):
    deleted: Literal[True]


class GuideJobErrorResponse(BaseModel):
    code: str
    message: str


class GuideJobResponse(BaseModel):
    id: str
    status: str
    stage: str
    progress: int = Field(ge=0, le=100)
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    cancel_requested: bool
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: GuideJobErrorResponse | None = None
    result: dict[str, Any] | None = None


class GuideJobListResponse(BaseModel):
    jobs: list[GuideJobResponse]


class AccountDeletionResponse(DeletedResponse):
    guides_deleted: int = Field(ge=0)
    private_files_deleted: int = Field(ge=0)


class ResolvedDestinationResponse(BaseModel):
    id: str
    city: str
    country: str
    formatted_address: str
    latitude: float
    longitude: float


class DynamicItineraryResponse(ItineraryRecommendation):
    resolved_destination: ResolvedDestinationResponse


class CustomLandmarkResponse(BaseModel):
    id: str
    selection_id: str
    name: str
    description: list[str]
    representative_query: str | None = None
    required_terms: list[str] = Field(default_factory=list)


class CustomLandmarkDestinationResponse(BaseModel):
    id: str
    country: str
    city: str
    display_title: str
    landmarks: list[CustomLandmarkResponse]


class CustomLandmarksResponse(BaseModel):
    selected_landmarks: list[str]
    destinations: list[CustomLandmarkDestinationResponse]


class PreviewImageResponse(BaseModel):
    image_url: str
    source_url: str
    author: str
    license_short_name: str
    license_url: str


class PreviewLandmarkResponse(BaseModel):
    id: str
    selection_id: str
    name: str
    description: list[str]
    representative_query: str | None = None
    confidence: float
    image: PreviewImageResponse | None = None
    image_attributions: list[dict[str, str]] = Field(default_factory=list)
    location_status: str
    place_id: str
    google_maps_uri: str
    formatted_address: str
    latitude: float | None = None
    longitude: float | None = None


class PreviewDestinationResponse(BaseModel):
    id: str
    country: str
    city: str
    display_title: str
    landmarks: list[PreviewLandmarkResponse]


class LandmarkResolutionResponse(BaseModel):
    custom_landmarks: str
    selected_landmarks: list[str]
    destinations: list[PreviewDestinationResponse]


class CoverStatusResponse(BaseModel):
    fallback_used: bool
    validation_status: str | None = None
    visible_people_count: int | None = None
    validation_message: str = ""
    expected_visible_family_member_count: int | None = None
    attempts: int = Field(default=0, ge=0)


class GuideGenerationCompletedResponse(BaseModel):
    request_id: str
    download_url: str
    filename: str
    cover_status: CoverStatusResponse


class GuideGenerationQueuedResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    progress: int = Field(ge=0, le=100)
    poll_url: str


GuideGenerationResponse = GuideGenerationCompletedResponse | GuideGenerationQueuedResponse


class AccountExportIdentityResponse(BaseModel):
    id: str
    email: str | None = None


class AccountExportResponse(BaseModel):
    schema_version: Literal[1]
    exported_at: str
    account: AccountExportIdentityResponse
    guides: list[dict[str, Any]]
    drafts: list[dict[str, Any]]


API_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status_code: {"model": ApiErrorResponse, "description": "Erro padronizado da API"}
    for status_code in (400, 401, 403, 404, 409, 410, 413, 422, 429, 500, 502, 503)
}


class MinervaFastAPI(FastAPI):
    def openapi(self) -> dict[str, Any]:
        schema = super().openapi()
        schema["x-minerva-contract-limits"] = public_contract_limits()
        return schema


app = MinervaFastAPI(title="Minerva Travel MVP", version="1.0.0", responses=API_ERROR_RESPONSES)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type", "Idempotency-Key"],
    expose_headers=["Idempotency-Replayed", "Retry-After", "X-Request-ID"],
)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or uuid4().hex)


def _default_error_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "authentication_required",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        410: "gone",
        413: "payload_too_large",
        422: "input_validation_error",
        429: "rate_limit_exceeded",
        500: "internal_error",
        502: "provider_error",
        503: "service_unavailable",
    }.get(status_code, f"http_{status_code}")


def _error_response(
    request: Request,
    *,
    status_code: int,
    detail: Any,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    code = _default_error_code(status_code)
    message = "A solicitação não pôde ser concluída."
    field_errors: list[dict[str, Any]] = []
    if isinstance(detail, dict):
        code = str(detail.get("code") or code)
        message = str(detail.get("message") or detail.get("detail") or message)
        candidate_errors = detail.get("field_errors")
        if isinstance(candidate_errors, list):
            field_errors = [item for item in candidate_errors if isinstance(item, dict)]
    elif isinstance(detail, list):
        field_errors = [item for item in detail if isinstance(item, dict)]
        message = "Revise os campos destacados e tente novamente."
    elif detail:
        message = str(detail)
    payload = ApiErrorResponse(
        code=code,
        message=message,
        field_errors=field_errors,
        request_id=_request_id(request),
        detail=detail,
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(payload),
        headers=headers,
    )


@app.middleware("http")
async def security_and_request_headers(request: Request, call_next):
    supplied_request_id = request.headers.get("X-Request-ID", "")[:64]
    request_id = (
        supplied_request_id
        if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_request_id)
        else uuid4().hex
    )
    request.state.request_id = request_id
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        emit_event(
            "api_request",
            request_id=request_id,
            route=request.url.path,
            outcome="failed",
            http_status=500,
            duration_ms=round((perf_counter() - started_at) * 1000),
        )
        raise
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
        "form-action 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
    )
    if app_environment() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith(
        ("/api/account", "/api/drafts", "/api/guides", "/api/jobs", "/download/")
    ):
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
    emit_event(
        "api_request",
        request_id=request_id,
        route=request.url.path,
        outcome="succeeded" if response.status_code < 500 else "failed",
        http_status=response.status_code,
        duration_ms=round((perf_counter() - started_at) * 1000),
    )
    return response


@app.exception_handler(storage.ImageUploadError)
async def image_upload_error_handler(
    request: Request,
    error: storage.ImageUploadError,
) -> JSONResponse:
    return _error_response(
        request,
        status_code=error.status_code,
        detail=error.as_detail(),
    )


@app.exception_handler(RequestControlError)
async def request_control_error_handler(
    request: Request,
    error: RequestControlError,
) -> JSONResponse:
    return _error_response(
        request,
        status_code=error.status_code,
        detail=error.as_detail(),
        headers=error.response_headers(),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        request,
        status_code=422,
        detail=error.errors(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    request: Request,
    error: StarletteHTTPException,
) -> JSONResponse:
    return _error_response(
        request,
        status_code=error.status_code,
        detail=error.detail,
        headers=dict(error.headers or {}),
    )


def expensive_request_guard(
    scope: str,
    provider: str | Callable[[], str],
    *,
    default_user_limit: int,
    default_ip_limit: int,
    default_window_seconds: int = 60,
    default_user_concurrency: int = 2,
    default_user_quota: int | None = None,
    default_quota_period_seconds: int = 24 * 60 * 60,
) -> Callable[..., AsyncIterator[None]]:
    async def guard(
        request: Request,
        current_user: CurrentUser,
    ) -> AsyncIterator[None]:
        lease = admit_expensive_request(
            request=request,
            user_id=current_user.id,
            scope=scope,
            provider=provider() if callable(provider) else provider,
            default_user_limit=default_user_limit,
            default_ip_limit=default_ip_limit,
            default_window_seconds=default_window_seconds,
            default_user_concurrency=default_user_concurrency,
            default_user_quota=default_user_quota,
            default_quota_period_seconds=default_quota_period_seconds,
        )
        try:
            yield
        finally:
            if lease is not None:
                lease.release()

    return guard


def admit_expensive_request(
    *,
    request: Request,
    user_id: str,
    scope: str,
    provider: str,
    default_user_limit: int,
    default_ip_limit: int,
    default_window_seconds: int = 60,
    default_user_concurrency: int = 2,
    default_user_quota: int | None = None,
    default_quota_period_seconds: int = 24 * 60 * 60,
    control: SQLiteRequestControl | None = None,
) -> ConcurrencyLease | None:
    if not request_controls_enabled():
        return None
    active_control = control or get_request_control()
    active_control.consume_rate(
        configured_rate_policy(
            scope,
            default_user_limit=default_user_limit,
            default_ip_limit=default_ip_limit,
            default_window_seconds=default_window_seconds,
        ),
        user_id=user_id,
        ip_address=request.client.host if request.client else "unknown",
    )
    if default_user_quota is not None:
        active_control.consume_quota(
            scope=scope,
            user_id=user_id,
            limit=configured_user_quota(scope, default=default_user_quota),
            period_seconds=configured_quota_period_seconds(
                scope,
                default=default_quota_period_seconds,
            ),
        )
    return active_control.acquire_concurrency(
        scope=scope,
        user_id=user_id,
        provider=provider,
        user_limit=configured_user_concurrency_limit(
            scope,
            default=default_user_concurrency,
        ),
        provider_limit=configured_provider_concurrency_limit(provider),
        lease_seconds=configured_concurrency_lease_seconds(),
    )


class CustomLandmarksResolveRequest(StrictRequestModel):
    landmarks: str = Field(min_length=2, max_length=20_000)


class LandmarkParseRequest(StrictRequestModel):
    message: str = Field(min_length=2, max_length=5_000)


class KnownDestinationInput(StrictRequestModel):
    place: str = Field(min_length=1, max_length=160)
    landmarks: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        min_length=1,
        max_length=MAX_GUIDE_LANDMARKS,
    )


class StructuredLandmarksResolveRequest(StrictRequestModel):
    destinations: list[KnownDestinationInput] = Field(
        min_length=1, max_length=MAX_GUIDE_DESTINATIONS
    )


class GuideDraftCreateRequest(StrictRequestModel):
    title: str = Field(default="", max_length=200)
    payload: dict[str, object] = Field(default_factory=dict)


class GuideDraftUpdateRequest(GuideDraftCreateRequest):
    revision: int = Field(ge=1)


class GuideGenerationFormRequest(StrictRequestModel):
    title: str = Field(min_length=1, max_length=160)
    children_names: str = Field(min_length=1, max_length=MAX_GUIDE_CHILDREN * 102)
    parents_names: str = Field(min_length=1, max_length=MAX_GUIDE_PARENTS * 102)
    year: int = Field(ge=MIN_GUIDE_YEAR, le=MAX_GUIDE_YEAR)
    children_ages: list[Annotated[int, Field(ge=0, le=17)]] = Field(
        default_factory=list,
        max_length=MAX_GUIDE_CHILDREN,
    )
    expected_visible_family_member_count: int | None = Field(
        default=None, ge=1, le=MAX_VISIBLE_FAMILY_MEMBERS
    )
    selected_landmarks: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list,
        max_length=MAX_GUIDE_LANDMARKS,
    )
    custom_landmarks: str | None = Field(default=None, max_length=20_000)
    itinerary_json: str | None = Field(default=None, max_length=100_000)
    restaurant_recommendations_extra: bool = False
    photo_processing_consent: bool = False
    privacy_consent_version: str | None = Field(default=None, max_length=100)
    privacy_consent_at: str | None = Field(default=None, max_length=100)


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    """Keep one public UI: the React application, not the retired Jinja form."""

    return RedirectResponse(frontend_base_url(), status_code=307)


@app.get("/api/catalog", response_model=CatalogResponse)
def api_catalog() -> CatalogResponse:
    catalog = load_catalog()
    return CatalogResponse(
        id=catalog.id,
        title=catalog.title,
        destinations=[
            CatalogDestinationResponse(
                id=destination.id,
                country=destination.country,
                city=destination.city,
                display_title=destination.display_title,
                intro=destination.intro,
                landmarks=[
                    CatalogLandmarkResponse(
                        id=landmark.id,
                        selection_id=f"{destination.id}:{landmark.id}",
                        name=landmark.name,
                        description=landmark.description,
                        sort_order=landmark.sort_order,
                        categories=landmark.categories,
                        duration_minutes=landmark.duration_minutes,
                        family_tip=landmark.family_tip,
                    )
                    for landmark in destination.landmarks
                ],
            )
            for destination in catalog.destinations
        ],
    )


@app.get("/health/live", response_model=HealthLiveResponse)
def health_live() -> HealthLiveResponse:
    return HealthLiveResponse(status="ok")


@app.get("/health/ready", response_model=HealthReadyResponse)
def health_ready() -> HealthReadyResponse:
    try:
        storage.ensure_runtime_dirs()
        database_ready = guide_repository().healthcheck()
        storage_ready = storage.RUNTIME_DIR.exists() and os.access(storage.RUNTIME_DIR, os.W_OK)
    except (OSError, sqlite3.Error):
        database_ready = False
        storage_ready = False
    if not database_ready or not storage_ready:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "not_ready",
                "message": "Dependências essenciais indisponíveis.",
            },
        )
    return HealthReadyResponse(
        status="ok",
        checks=HealthChecksResponse(database="ok", storage="ok"),
    )


@app.post("/api/itinerary/recommend", response_model=ItineraryRecommendation)
def api_recommend_itinerary(
    payload: ItineraryRecommendationRequest,
    _current_user: CurrentUser,
) -> ItineraryRecommendation:
    catalog = load_catalog()
    try:
        recommendation = recommend_itinerary(catalog, payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return recommendation


@app.post(
    "/api/itinerary/discover",
    response_model=DynamicItineraryResponse,
    dependencies=[
        Depends(
            expensive_request_guard(
                "itinerary_discover",
                "google",
                default_user_limit=3,
                default_ip_limit=10,
                default_user_concurrency=1,
            )
        )
    ],
)
def api_discover_itinerary(
    payload: DynamicItineraryRequest,
    _current_user: CurrentUser,
) -> DynamicItineraryResponse:
    try:
        return DynamicItineraryResponse.model_validate(
            discover_dynamic_itinerary(payload, api_key=google_maps_api_key())
        )
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except httpx.HTTPStatusError as error:
        detail = "Google Places nao conseguiu montar o roteiro."
        if error.response.status_code in {401, 403}:
            detail = "Google Places nao esta habilitado ou a chave nao tem permissao suficiente."
        raise HTTPException(status_code=502, detail=detail) from error


@app.post("/api/itinerary/routes/suggest", response_model=RouteSuggestionResponse)
def api_suggest_itinerary_routes(
    payload: RouteSuggestionRequest,
    _current_user: CurrentUser,
) -> RouteSuggestionResponse:
    catalog = load_catalog()
    return suggest_itinerary_routes(payload, catalog)


@app.post("/api/custom-landmarks/resolve", response_model=CustomLandmarksResponse)
def resolve_custom_landmarks(
    payload: CustomLandmarksResolveRequest,
    _current_user: CurrentUser,
) -> CustomLandmarksResponse:
    try:
        custom_landmarks = parse_custom_landmarks(payload.landmarks)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    custom_destinations, selected_landmarks = build_custom_destinations(custom_landmarks)
    return CustomLandmarksResponse(
        selected_landmarks=selected_landmarks,
        destinations=[
            CustomLandmarkDestinationResponse(
                id=destination.id,
                country=destination.country,
                city=destination.city,
                display_title=destination.display_title,
                landmarks=[
                    CustomLandmarkResponse(
                        id=landmark.id,
                        selection_id=f"{destination.id}:{landmark.id}",
                        name=landmark.name,
                        description=landmark.description,
                        representative_query=landmark.representative_query,
                        required_terms=landmark.required_terms,
                    )
                    for landmark in destination.landmarks
                ],
            )
            for destination in custom_destinations
        ],
    )


@app.post(
    "/api/landmarks/resolve-structured",
    response_model=LandmarkResolutionResponse,
    dependencies=[
        Depends(
            expensive_request_guard(
                "landmarks_resolve",
                "google",
                default_user_limit=10,
                default_ip_limit=30,
            )
        )
    ],
)
def resolve_structured_landmarks(
    payload: StructuredLandmarksResolveRequest,
    _current_user: CurrentUser,
) -> LandmarkResolutionResponse:
    custom_inputs: list[CustomLandmarkInput] = []
    for destination in payload.destinations:
        city, country = _split_destination_place(destination.place)
        for landmark_name in destination.landmarks:
            cleaned_name = landmark_name.strip()
            if not cleaned_name:
                continue
            custom_inputs.append(CustomLandmarkInput(name=cleaned_name, city=city, country=country))
    if not custom_inputs:
        raise HTTPException(
            status_code=400,
            detail="Informe pelo menos um ponto turistico por destino.",
        )

    custom_destinations, selected_landmarks = build_custom_destinations(custom_inputs)
    location_metadata = {}
    api_key = google_maps_api_key()
    if api_key:
        location_metadata = resolve_landmark_locations(
            custom_destinations,
            api_key=api_key,
            include_photos=True,
        )
    return LandmarkResolutionResponse(
        custom_landmarks=json.dumps(
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
        selected_landmarks=selected_landmarks,
        destinations=[
            PreviewDestinationResponse.model_validate(destination)
            for destination in serialize_preview_destinations(
                custom_destinations,
                [],
                {},
                location_metadata,
            )
        ],
    )


def _split_destination_place(place: str) -> tuple[str, str]:
    parts = [part.strip() for part in place.replace(";", ",").split(",") if part.strip()]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], ", ".join(parts[1:])


@app.post(
    "/api/landmarks/parse",
    response_model=LandmarkResolutionResponse,
    dependencies=[
        Depends(
            expensive_request_guard(
                "landmarks_parse",
                "openai",
                default_user_limit=5,
                default_ip_limit=20,
            )
        )
    ],
)
def parse_landmarks(
    payload: LandmarkParseRequest,
    _current_user: CurrentUser,
) -> LandmarkResolutionResponse:
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
    location_metadata = {}
    api_key = google_maps_api_key()
    if api_key:
        location_metadata = resolve_landmark_locations(
            custom_destinations,
            api_key=api_key,
            include_photos=True,
        )
    return LandmarkResolutionResponse(
        custom_landmarks=json.dumps(
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
        selected_landmarks=selected_landmarks,
        destinations=[
            PreviewDestinationResponse.model_validate(destination)
            for destination in serialize_preview_destinations(
                custom_destinations,
                parsed_landmarks,
                {},
                location_metadata,
            )
        ],
    )


def _parsed_landmark_description(item: ParsedLandmark | dict[str, object]) -> list[str]:
    raw_description = item.get("description", []) if isinstance(item, dict) else item.description
    if not isinstance(raw_description, list):
        return []
    return [str(paragraph).strip() for paragraph in raw_description if str(paragraph).strip()]


@app.post(
    "/api/landmarks/parse-preview",
    response_model=LandmarkResolutionResponse,
    dependencies=[
        Depends(
            expensive_request_guard(
                "landmarks_parse",
                "openai",
                default_user_limit=5,
                default_ip_limit=20,
            )
        )
    ],
)
def parse_preview_landmarks(
    payload: LandmarkParseRequest,
    current_user: CurrentUser,
) -> LandmarkResolutionResponse:
    return parse_landmarks(payload, current_user)


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
        children_ages=[6, 9],
        parents_names=["Ana", "Otavio"],
        year=2026,
        selected_landmarks=selected,
        itinerary=GuideItineraryPlan(
            mode="known",
            pace="balanced",
            interests=["história", "arte", "passeios em família"],
            destinations=[
                GuideDestinationPlan(
                    id=destination.id,
                    place=destination.location_label,
                    timing="Europa 2026",
                    days=max(1, min(3, len(destination.landmarks))),
                    order=index,
                )
                for index, destination in enumerate(catalog.destinations, start=1)
            ],
            days=[
                GuideItineraryDayPlan(
                    day=index,
                    title=f"Dia {index}: {destination.city}",
                    theme=f"Descobertas em {destination.city}",
                    stops=[
                        GuideItineraryStopPlan(
                            selection_id=f"{destination.id}:{landmark.id}",
                            name=landmark.name,
                            destination_id=destination.id,
                        )
                        for landmark in destination.landmarks[:3]
                    ],
                )
                for index, destination in enumerate(catalog.destinations, start=1)
            ],
        ),
    )
    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/representative-full-cover.png"),
    )
    return render_guide_html(context, preview=True)


@app.post("/generate", include_in_schema=False)
def legacy_generate_removed() -> JSONResponse:
    """Prevent the retired form from bypassing auth, jobs and idempotency."""

    return JSONResponse(
        status_code=410,
        content={
            "detail": {
                "code": "legacy_generation_removed",
                "message": "Use o aplicativo atualizado para criar um guia.",
            }
        },
    )


def parse_guide_generation_form(
    title: Annotated[str, Form()],
    children_names: Annotated[str, Form()],
    parents_names: Annotated[str, Form()],
    year: Annotated[int, Form()],
    children_ages: Annotated[list[int] | None, Form()] = None,
    expected_visible_family_member_count: Annotated[int | None, Form()] = None,
    selected_landmarks: Annotated[list[str] | None, Form()] = None,
    custom_landmarks: Annotated[str | None, Form()] = None,
    itinerary_json: Annotated[str | None, Form()] = None,
    restaurant_recommendations_extra: Annotated[bool | None, Form()] = None,
    photo_processing_consent: Annotated[bool, Form()] = False,
    privacy_consent_version: Annotated[str | None, Form()] = None,
    privacy_consent_at: Annotated[str | None, Form()] = None,
) -> GuideGenerationFormRequest:
    try:
        return GuideGenerationFormRequest(
            title=title,
            children_names=children_names,
            parents_names=parents_names,
            year=year,
            children_ages=children_ages or [],
            expected_visible_family_member_count=expected_visible_family_member_count,
            selected_landmarks=selected_landmarks or [],
            custom_landmarks=custom_landmarks,
            itinerary_json=itinerary_json,
            restaurant_recommendations_extra=bool(restaurant_recommendations_extra),
            photo_processing_consent=photo_processing_consent,
            privacy_consent_version=privacy_consent_version,
            privacy_consent_at=privacy_consent_at,
        )
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error


@app.post("/api/generate", response_model=GuideGenerationResponse)
async def api_generate(
    form: Annotated[GuideGenerationFormRequest, Depends(parse_guide_generation_form)],
    family_photo: Annotated[UploadFile, File()],
    request: Request,
    response: Response,
    current_user: CurrentUser,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> GuideGenerationResponse:
    title = form.title
    children_names = form.children_names
    parents_names = form.parents_names
    year = form.year
    children_ages = form.children_ages
    expected_visible_family_member_count = form.expected_visible_family_member_count
    selected_landmarks = form.selected_landmarks
    custom_landmarks = form.custom_landmarks
    itinerary_json = form.itinerary_json
    restaurant_recommendations_extra = form.restaurant_recommendations_extra
    photo_processing_consent = form.photo_processing_consent
    privacy_consent_version = form.privacy_consent_version
    privacy_consent_at = form.privacy_consent_at

    queue_generation = async_guide_jobs_enabled()
    key_required = idempotency_key_required() or queue_generation
    if key_required and not (idempotency_key or "").strip():
        raise IdempotencyKeyRequiredError()

    controls_enabled = request_controls_enabled()
    uses_idempotency = key_required or bool(idempotency_key and idempotency_key.strip())
    control = get_request_control() if controls_enabled or uses_idempotency else None
    reservation: IdempotencyReservation | None = None
    if uses_idempotency and control is not None:
        request_hash = await generation_request_hash(
            title=title,
            children_names=children_names,
            children_ages=children_ages or [],
            expected_visible_family_member_count=expected_visible_family_member_count,
            parents_names=parents_names,
            year=year,
            selected_landmarks=selected_landmarks or [],
            custom_landmarks=custom_landmarks,
            itinerary_json=itinerary_json,
            restaurant_recommendations_extra=bool(restaurant_recommendations_extra),
            photo_processing_consent=photo_processing_consent,
            privacy_consent_version=privacy_consent_version,
            privacy_consent_at=privacy_consent_at,
            family_photo=family_photo,
        )
        reservation = control.reserve_idempotency(
            namespace="guide-generation-api",
            user_id=current_user.id,
            key=idempotency_key,
            request_hash=request_hash,
            required=key_required,
            pending_ttl_seconds=configured_idempotency_pending_ttl_seconds(),
        )
        if reservation is not None and reservation.state == "completed":
            response.status_code = reservation.response_status or 200
            response.headers["Idempotency-Replayed"] = "true"
            return validate_generation_response_payload(reservation.response_payload)
        if reservation is not None and reservation.state == "in_progress":
            if queue_generation:
                existing_job = guide_repository().get_job_for_idempotency(
                    current_user.id, idempotency_key or ""
                )
                if existing_job is not None:
                    response.status_code = 202
                    response.headers["Idempotency-Replayed"] = "true"
                    return GuideGenerationQueuedResponse.model_validate(
                        queued_job_payload(existing_job)
                    )
            raise IdempotencyInProgressError(
                operation_id=reservation.operation_id,
                retry_after=reservation.retry_after or 1,
            )

    lease: ConcurrencyLease | None = None
    queued_photo_path: Path | None = None
    job_persisted = False
    try:
        lease = admit_expensive_request(
            request=request,
            user_id=current_user.id,
            scope="guide_generate",
            provider=image_provider(),
            default_user_limit=2,
            default_ip_limit=5,
            default_window_seconds=10 * 60,
            default_user_concurrency=1,
            default_user_quota=20,
            control=control,
        )
        if queue_generation:
            submission = validate_queued_generation_submission(
                title=title,
                children_names=children_names,
                children_ages=children_ages or [],
                expected_visible_family_member_count=expected_visible_family_member_count,
                parents_names=parents_names,
                year=year,
                selected_landmarks=selected_landmarks or [],
                custom_landmarks=custom_landmarks,
                itinerary_json=itinerary_json,
                restaurant_recommendations_extra=bool(restaurant_recommendations_extra),
                photo_processing_consent=photo_processing_consent,
                privacy_consent_version=privacy_consent_version,
                privacy_consent_at=privacy_consent_at,
            )
            queued_photo_path = await storage.save_upload(family_photo)
            job_id = uuid4().hex
            try:
                created_job = guide_repository().create_job(
                    job_id=job_id,
                    user_id=current_user.id,
                    idempotency_key=idempotency_key or job_id,
                    request_snapshot=submission,
                    photo_path=queued_photo_path,
                    max_attempts=guide_job_max_attempts(),
                )
            except sqlite3.IntegrityError:
                existing_job = guide_repository().get_job_for_idempotency(
                    current_user.id, idempotency_key or ""
                )
                if existing_job is None:
                    raise
                delete_private_asset(queued_photo_path)
                queued_photo_path = None
                response.status_code = 202
                response.headers["Idempotency-Replayed"] = "true"
                return GuideGenerationQueuedResponse.model_validate(
                    queued_job_payload(existing_job)
                )
            job_persisted = True
            payload = queued_job_payload(created_job)
            emit_event(
                "guide_job_accepted",
                request_id=getattr(request.state, "request_id", None),
                job_id=created_job.id,
                user_id=current_user.id,
                stage=created_job.stage,
                outcome="accepted",
            )
            if reservation is not None and control is not None:
                try:
                    control.complete_idempotency(
                        reservation,
                        response_payload=payload,
                        response_status=202,
                        ttl_seconds=configured_idempotency_ttl_seconds(),
                    )
                except RequestControlError:
                    # The durable job row is the source of truth once it has
                    # been committed. A replay can recover through its unique
                    # user/key constraint even if the short-lived cache fails.
                    pass
                response.headers["Idempotency-Replayed"] = "false"
            response.status_code = 202
            return GuideGenerationQueuedResponse.model_validate(payload)
        result = await generate_pdf_from_form(
            title=title,
            children_names=children_names,
            children_ages=children_ages or [],
            expected_visible_family_member_count=expected_visible_family_member_count,
            parents_names=parents_names,
            year=year,
            selected_landmarks=selected_landmarks or [],
            custom_landmarks=custom_landmarks,
            itinerary_json=itinerary_json,
            restaurant_recommendations_extra=bool(restaurant_recommendations_extra),
            family_photo=family_photo,
            owner_id=current_user.id,
            photo_processing_consent=photo_processing_consent,
            privacy_consent_version=privacy_consent_version,
            privacy_consent_at=privacy_consent_at,
        )
        payload = {
            "request_id": result["request_id"],
            "download_url": result["download_url"],
            "filename": result["filename"],
            "cover_status": result["cover_status"],
        }
        if reservation is not None and control is not None:
            control.complete_idempotency(
                reservation,
                response_payload=payload,
                response_status=200,
                ttl_seconds=configured_idempotency_ttl_seconds(),
            )
            response.headers["Idempotency-Replayed"] = "false"
        return GuideGenerationCompletedResponse.model_validate(payload)
    except BaseException:
        if queued_photo_path is not None and not job_persisted:
            delete_private_asset(queued_photo_path)
        if reservation is not None and control is not None:
            try:
                control.abandon_idempotency(reservation)
            except RequestControlError:
                pass
        raise
    finally:
        if lease is not None:
            lease.release()


def queued_job_payload(job: GuideJobRecord) -> dict[str, object]:
    """Return the stable submission response for a persisted guide job."""

    job_id = job.id
    return {
        "job_id": job_id,
        "status": job.status,
        "stage": job.stage,
        "progress": job.progress,
        "poll_url": f"/api/jobs/{job_id}",
    }


def validate_generation_response_payload(
    payload: dict[str, object] | None,
) -> GuideGenerationResponse:
    if not payload:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "idempotency_response_invalid",
                "message": "A resposta idempotente armazenada está inválida.",
            },
        )
    if "job_id" in payload:
        return GuideGenerationQueuedResponse.model_validate(payload)
    return GuideGenerationCompletedResponse.model_validate(payload)


def validate_queued_generation_submission(
    *,
    title: str,
    children_names: str,
    children_ages: list[int],
    expected_visible_family_member_count: int | None,
    parents_names: str,
    year: int,
    selected_landmarks: list[str],
    custom_landmarks: str | None,
    itinerary_json: str | None,
    restaurant_recommendations_extra: bool,
    photo_processing_consent: bool,
    privacy_consent_version: str | None,
    privacy_consent_at: str | None,
) -> dict[str, object]:
    """Reject malformed queued work before it can consume a worker lease."""

    try:
        validate_photo_processing_consent(
            granted=photo_processing_consent,
            version=privacy_consent_version,
            granted_at=privacy_consent_at,
        )
    except PrivacyConsentError as error:
        raise HTTPException(status_code=422, detail=error.as_detail()) from error
    try:
        custom_items = parse_custom_landmarks(custom_landmarks)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not selected_landmarks and not custom_items:
        raise HTTPException(
            status_code=400,
            detail="Selecione ou informe pelo menos um ponto turístico.",
        )
    try:
        GuideRequest(
            title=title,
            children_names=_split_names(children_names),
            children_ages=[age for age in children_ages if age > 0],
            parents_names=_split_names(parents_names),
            year=year,
            selected_landmarks=selected_landmarks or ["custom:pending"],
            expected_visible_family_member_count=expected_visible_family_member_count,
            restaurant_recommendations_extra=restaurant_recommendations_extra,
            itinerary=parse_guide_itinerary(itinerary_json),
        )
    except (ValidationError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "generation_input_invalid",
                "message": "Revise os dados da família e do roteiro.",
            },
        ) from error
    return {
        "title": title,
        "children_names": children_names,
        "children_ages": children_ages,
        "expected_visible_family_member_count": expected_visible_family_member_count,
        "parents_names": parents_names,
        "year": year,
        "selected_landmarks": selected_landmarks,
        "custom_landmarks": custom_landmarks,
        "itinerary_json": itinerary_json,
        "restaurant_recommendations_extra": restaurant_recommendations_extra,
        "photo_processing_consent": photo_processing_consent,
        "privacy_consent_version": privacy_consent_version,
        "privacy_consent_at": privacy_consent_at,
    }


async def generation_request_hash(
    *,
    title: str,
    children_names: str,
    children_ages: list[int],
    expected_visible_family_member_count: int | None,
    parents_names: str,
    year: int,
    selected_landmarks: list[str],
    custom_landmarks: str | None,
    itinerary_json: str | None,
    restaurant_recommendations_extra: bool,
    photo_processing_consent: bool,
    privacy_consent_version: str | None,
    privacy_consent_at: str | None,
    family_photo: UploadFile,
) -> str:
    photo_hash, photo_size = await upload_content_hash(family_photo)
    return stable_request_hash(
        {
            "title": title,
            "children_names": children_names,
            "children_ages": children_ages,
            "expected_visible_family_member_count": expected_visible_family_member_count,
            "parents_names": parents_names,
            "year": year,
            "selected_landmarks": selected_landmarks,
            "custom_landmarks": custom_landmarks,
            "itinerary_json": itinerary_json,
            "restaurant_recommendations_extra": restaurant_recommendations_extra,
            "photo_processing_consent": photo_processing_consent,
            "privacy_consent_version": privacy_consent_version,
            "privacy_consent_at": privacy_consent_at,
            "family_photo": {
                "sha256": photo_hash,
                "size": photo_size,
                "content_type": family_photo.content_type,
            },
        }
    )


async def upload_content_hash(upload: UploadFile) -> tuple[str, int]:
    max_bytes = storage.image_upload_max_bytes()
    if upload.size is not None and upload.size > max_bytes:
        raise storage.ImageUploadTooLargeError(
            max_bytes=max_bytes,
            bytes_read=upload.size,
        )
    digest = hashlib.sha256()
    bytes_read = 0
    await upload.seek(0)
    try:
        while True:
            chunk = await upload.read(storage.IMAGE_UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            bytes_read += len(chunk)
            if bytes_read > max_bytes:
                raise storage.ImageUploadTooLargeError(
                    max_bytes=max_bytes,
                    bytes_read=bytes_read,
                )
            digest.update(chunk)
    finally:
        await upload.seek(0)
    return digest.hexdigest(), bytes_read


@app.get("/api/guides", response_model=GuideListResponse)
def list_guides(current_user: CurrentUser) -> GuideListResponse:
    records = guide_repository().list_for_owner(current_user.id)
    return GuideListResponse(
        guides=[GuideResponse.model_validate(record.public_payload()) for record in records]
    )


@app.get("/api/drafts/current", response_model=CurrentGuideDraftResponse)
def get_current_draft(current_user: CurrentUser) -> CurrentGuideDraftResponse:
    draft = guide_repository().latest_draft_for_owner(current_user.id)
    return CurrentGuideDraftResponse(
        draft=GuideDraftResponse.model_validate(draft.public_payload()) if draft else None
    )


@app.post("/api/drafts", status_code=201, response_model=GuideDraftResponse)
def create_draft(
    payload: GuideDraftCreateRequest,
    current_user: CurrentUser,
) -> GuideDraftResponse:
    try:
        draft = guide_repository().create_draft(
            user_id=current_user.id,
            title=payload.title,
            payload=payload.payload,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "draft_payload_invalid", "message": str(error)},
        ) from error
    emit_event("guide_draft_created", user_id=current_user.id, outcome="accepted")
    return GuideDraftResponse.model_validate(draft.public_payload())


@app.put("/api/drafts/{draft_id}", response_model=GuideDraftResponse)
def update_draft(
    draft_id: str,
    payload: GuideDraftUpdateRequest,
    current_user: CurrentUser,
) -> GuideDraftResponse:
    try:
        draft = guide_repository().update_draft(
            draft_id=draft_id,
            user_id=current_user.id,
            title=payload.title,
            payload=payload.payload,
            expected_revision=payload.revision,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "draft_payload_invalid", "message": str(error)},
        ) from error
    if draft is not None:
        emit_event("guide_draft_saved", user_id=current_user.id, outcome="succeeded")
        return GuideDraftResponse.model_validate(draft.public_payload())
    existing = guide_repository().get_draft_for_owner(draft_id, current_user.id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    raise HTTPException(
        status_code=409,
        detail={
            "code": "draft_revision_conflict",
            "message": "Este rascunho foi atualizado em outra sessão. Recarregue a página.",
            "revision": existing.revision,
        },
    )


@app.delete("/api/drafts/{draft_id}", response_model=DeletedResponse)
def delete_draft(draft_id: str, current_user: CurrentUser) -> DeletedResponse:
    if not guide_repository().discard_draft(draft_id, current_user.id):
        raise HTTPException(status_code=404, detail="Draft not found")
    emit_event("guide_draft_discarded", user_id=current_user.id, outcome="cancelled")
    return DeletedResponse(deleted=True)


@app.get("/api/jobs", response_model=GuideJobListResponse)
def list_jobs(current_user: CurrentUser) -> GuideJobListResponse:
    jobs = guide_repository().list_jobs_for_owner(current_user.id)
    return GuideJobListResponse(
        jobs=[GuideJobResponse.model_validate(job.public_payload()) for job in jobs]
    )


@app.get("/api/jobs/{job_id}", response_model=GuideJobResponse)
def job_details(job_id: str, current_user: CurrentUser) -> GuideJobResponse:
    job = guide_repository().get_job_for_owner(job_id, current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return GuideJobResponse.model_validate(job.public_payload())


@app.delete("/api/jobs/{job_id}", response_model=GuideJobResponse)
def cancel_job(job_id: str, current_user: CurrentUser) -> GuideJobResponse:
    repository = guide_repository()
    job = repository.request_job_cancellation(job_id, current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    has_cross_owner_reference = repository.is_private_path_referenced_by_another_owner(
        job.photo_path, current_user.id
    )
    if job.status == "cancelled" and not has_cross_owner_reference:
        delete_private_asset(job.photo_path)
    return GuideJobResponse.model_validate(job.public_payload())


@app.get("/api/account/export", response_model=AccountExportResponse)
def export_account_data(current_user: CurrentUser) -> JSONResponse:
    repository = guide_repository()
    records = repository.list_for_export(current_user.id)
    drafts = repository.list_drafts_for_export(current_user.id)
    return JSONResponse(
        content={
            "schema_version": 1,
            "exported_at": datetime.now(UTC).isoformat(),
            "account": {
                "id": current_user.id,
                "email": current_user.email,
            },
            "guides": [record.export_payload() for record in records],
            "drafts": [draft.export_payload() for draft in drafts],
        },
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "Content-Disposition": 'attachment; filename="minerva-travel-data-export.json"',
        },
    )


@app.delete("/api/account/data", response_model=AccountDeletionResponse)
def delete_account_data(current_user: CurrentUser) -> JSONResponse:
    result = purge_all_data_for_owner(guide_repository(), current_user.id)
    return JSONResponse(
        content={
            "deleted": True,
            "guides_deleted": result.guides_deleted,
            "private_files_deleted": result.private_files_deleted,
        },
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/api/guides/{guide_id}", response_model=GuideResponse)
def guide_details(guide_id: str, current_user: CurrentUser) -> GuideResponse:
    record = guide_repository().get_for_owner(guide_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="Guide not found")
    return GuideResponse.model_validate(record.public_payload())


@app.delete("/api/guides/{guide_id}", response_model=DeletedResponse)
def delete_guide(guide_id: str, current_user: CurrentUser) -> DeletedResponse:
    deleted = delete_guide_and_assets(guide_repository(), guide_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Guide not found")
    return DeletedResponse(deleted=True)


@app.get("/download/{filename}")
def download(filename: str, current_user: CurrentUser) -> FileResponse:
    record = guide_repository().get_by_pdf_for_owner(filename, current_user.id)
    if record is None or record.status != "succeeded":
        raise HTTPException(status_code=404, detail="PDF not found")
    if record.is_expired:
        raise HTTPException(status_code=410, detail="PDF expired")
    path = storage.pdf_path(filename)
    if path.name != filename or path.suffix.lower() != ".pdf" or not path.is_file():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{slugify(record.title)[:72] or 'guia'}-minerva-travel.pdf",
        headers={
            "Cache-Control": "private, no-store, max-age=0",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def generate_pdf_from_form(
    title: str,
    children_names: str,
    children_ages: list[int],
    expected_visible_family_member_count: int | None,
    parents_names: str,
    year: int,
    selected_landmarks: list[str],
    family_photo: UploadFile,
    owner_id: str,
    custom_landmarks: str | None = None,
    itinerary_json: str | None = None,
    restaurant_recommendations_extra: bool = False,
    photo_processing_consent: bool = False,
    privacy_consent_version: str | None = None,
    privacy_consent_at: str | None = None,
) -> dict[str, object]:
    try:
        privacy_consent = validate_photo_processing_consent(
            granted=photo_processing_consent,
            version=privacy_consent_version,
            granted_at=privacy_consent_at,
        )
    except PrivacyConsentError as error:
        raise HTTPException(status_code=422, detail=error.as_detail()) from error

    photo_path = await storage.save_upload(family_photo)
    try:
        return await generate_pdf_from_saved_photo(
            title=title,
            children_names=children_names,
            children_ages=children_ages,
            expected_visible_family_member_count=expected_visible_family_member_count,
            parents_names=parents_names,
            year=year,
            selected_landmarks=selected_landmarks,
            family_photo_path=photo_path,
            owner_id=owner_id,
            custom_landmarks=custom_landmarks,
            itinerary_json=itinerary_json,
            restaurant_recommendations_extra=restaurant_recommendations_extra,
            privacy_consent=privacy_consent,
        )
    except Exception:
        delete_private_asset(photo_path)
        raise


async def generate_pdf_from_saved_photo(
    *,
    title: str,
    children_names: str,
    children_ages: list[int],
    expected_visible_family_member_count: int | None,
    parents_names: str,
    year: int,
    selected_landmarks: list[str],
    family_photo_path: Path,
    owner_id: str,
    custom_landmarks: str | None = None,
    itinerary_json: str | None = None,
    restaurant_recommendations_extra: bool = False,
    privacy_consent: PrivacyConsent | None = None,
    guide_id: str | None = None,
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
        children_ages=[age for age in children_ages if age > 0],
        parents_names=_split_names(parents_names),
        year=year,
        selected_landmarks=selected,
        expected_visible_family_member_count=expected_visible_family_member_count,
        restaurant_recommendations_extra=restaurant_recommendations_extra,
        itinerary=parse_guide_itinerary(itinerary_json),
    )
    request_id = guide_id or uuid4().hex
    # Resolve the credited landmark images before calling an image provider.
    # In production this fails closed rather than falling back to the bundled
    # geometric fixtures that are intentionally retained for offline dev/tests.
    wikimedia_assets = load_wikimedia_manifest()
    wikimedia_assets.update(fetch_custom_wikimedia_assets(custom_destinations, request_id))
    selected_wikimedia_assets = {
        selection_id: asset
        for selection_id, asset in wikimedia_assets.items()
        if selection_id in selected
    }
    try:
        assert_selected_asset_provenance(selected, selected_wikimedia_assets)
    except AssetProvenanceError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "approved_landmark_asset_unavailable",
                "message": str(error),
                "selection_ids": list(error.missing_selection_ids),
            },
        ) from error

    approved_reference_images = {
        selection_id: asset.local_path for selection_id, asset in selected_wikimedia_assets.items()
    }
    precomputed_lineart_images: dict[str, Path] = {}
    if asset_provenance_required() and not landmark_art_generation_enabled():
        # Run this inexpensive local transformation before a paid cover call.
        # A corrupt reference therefore fails safely instead of delivering a
        # generic coloring-page placeholder after spending provider budget.
        precomputed_lineart_images = create_local_lineart_fallbacks(
            catalog.destinations,
            selected,
            request_id,
            reference_images=approved_reference_images,
            allow_named_placeholder=False,
        )
        missing_lineart = sorted(set(selected) - set(precomputed_lineart_images))
        if missing_lineart:
            for path in precomputed_lineart_images.values():
                delete_private_asset(path)
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "approved_landmark_lineart_unavailable",
                    "message": "Não foi possível preparar desenhos reconhecíveis para colorir.",
                    "selection_ids": missing_lineart,
                },
            )

    photo_path = family_photo_path
    cover_landmark_names = selected_landmark_names(catalog.destinations, selected)
    cover_path = storage.generated_path(f"{request_id}-cover.png")
    generator = get_image_generator(image_provider())
    cover_result = generate_cover_with_guardrails(
        generator=generator,
        family_photo=photo_path,
        output_path=cover_path,
        title=request.title,
        destination_names=cover_landmark_names,
        expected_visible_family_member_count=request.expected_visible_family_member_count,
        validator=get_cover_image_validator(),
    )
    summary_path = storage.generated_path(f"{request_id}-summary.png")
    generator.generate_trip_summary(
        output_path=summary_path,
        title=request.title,
        destination_names=cover_landmark_names,
    )

    wikimedia_assets.update(sync_wikimedia_assets_to_storage(selected_wikimedia_assets))

    landmark_images: dict[str, Path] = download_custom_landmark_images(
        custom_destinations,
        selected,
        request_id,
        skip_selection_ids=set(selected_wikimedia_assets),
    )
    reference_images = dict(approved_reference_images)
    reference_images.update(landmark_images)
    if landmark_art_generation_enabled():
        landmark_reference_images = {
            selection_id: asset.local_path
            for selection_id, asset in wikimedia_assets.items()
            if selection_id in selected
        }
        landmark_reference_images.update(landmark_images)
        generated_landmark_images, landmark_lineart_images = generate_selected_landmark_art(
            catalog.destinations,
            selected,
            request_id,
            generator,
            reference_images=landmark_reference_images,
        )
        landmark_images.update(generated_landmark_images)
    elif precomputed_lineart_images:
        landmark_lineart_images = precomputed_lineart_images
    elif coloring_lineart_generation_enabled():
        # The color and coloring images must refer to the same landmark. The
        # older path generated line art only for custom destinations and left
        # catalog landmarks with geometric placeholder drawings.
        landmark_lineart_images = create_local_lineart_fallbacks(
            catalog.destinations,
            selected,
            request_id,
            reference_images=reference_images,
        )
    else:
        landmark_lineart_images = create_local_lineart_fallbacks(
            catalog.destinations,
            selected,
            request_id,
            reference_images=reference_images,
        )
    context = build_guide_context(
        request,
        catalog,
        cover_path,
        summary_image=summary_path,
        wikimedia_assets=wikimedia_assets,
        landmark_images=landmark_images,
        landmark_lineart_images=landmark_lineart_images,
    )
    if request.restaurant_recommendations_extra and pilot_restaurant_recommendations_enabled():
        context = context.model_copy(
            update={
                "restaurant_recommendations": discover_restaurants_for_guide(
                    context.destinations,
                    api_key=google_maps_api_key(),
                )
            }
        )
    title_slug = slugify(request.title)[:48] or "guia"
    pdf_output = storage.pdf_path(f"{title_slug}-{request_id[:16]}.pdf")
    write_pdf(context, pdf_output)
    owned_assets = _owned_guide_assets(
        request_id=request_id,
        family_photo=photo_path,
        cover=cover_path,
        summary=summary_path,
        pdf=pdf_output,
        generated_images=[*landmark_images.values(), *landmark_lineart_images.values()],
    )
    try:
        guide_repository().save_succeeded_guide(
            guide_id=request_id,
            user_id=owner_id,
            title=request.title,
            pdf_filename=pdf_output.name,
            cover_fallback_used=cover_result.fallback_used,
            metadata={
                "destinations": [
                    {
                        "id": item.destination.id,
                        "place": item.destination.location_label,
                        "landmarks": [landmark.name for landmark in item.landmarks],
                    }
                    for item in context.destinations
                ],
                "year": request.year,
                "itinerary": (
                    request.itinerary.model_dump(mode="json") if request.itinerary else None
                ),
                "privacy_consent": privacy_consent.metadata() if privacy_consent else None,
            },
            assets=owned_assets,
        )
    except Exception:
        for _kind, path in owned_assets:
            delete_private_asset(path)
        raise
    return {
        "request": request,
        "request_id": request_id,
        "filename": pdf_output.name,
        "download_url": f"/download/{pdf_output.name}",
        "cover_status": cover_status_payload(cover_result, request),
    }


def _owned_guide_assets(
    *,
    request_id: str,
    family_photo: Path,
    cover: Path,
    summary: Path,
    pdf: Path,
    generated_images: list[Path],
) -> list[tuple[str, Path]]:
    candidates = [
        ("family_upload", family_photo),
        ("generated_cover", cover),
        ("trip_summary", summary),
        ("generated_guide", pdf),
    ]
    candidates.extend(
        ("generated_landmark", path) for path in generated_images if request_id in path.parts
    )
    unique: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for kind, path in candidates:
        marker = str(path)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append((kind, path))
    return unique


def cover_status_payload(
    cover_result: CoverGenerationResult,
    request: GuideRequest,
) -> dict[str, object]:
    validation = cover_result.validation
    return {
        "fallback_used": cover_result.fallback_used,
        "validation_status": validation.status if validation else None,
        "visible_people_count": validation.visible_people_count if validation else None,
        "validation_message": validation.message if validation else "",
        "expected_visible_family_member_count": request.expected_visible_family_member_count,
        "attempts": cover_result.attempts,
    }


def _split_names(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_guide_itinerary(raw: str | None) -> GuideItineraryPlan | None:
    if not raw or not raw.strip():
        return None
    try:
        return GuideItineraryPlan.model_validate_json(raw)
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_itinerary",
                "message": "O roteiro revisado possui dados inválidos.",
                "field_errors": error.errors(include_url=False),
            },
        ) from error


def selected_landmark_names(destinations: list[Destination], selected: list[str]) -> list[str]:
    selected_ids = set(selected)
    names: list[str] = []
    for destination in destinations:
        for landmark in destination.landmarks:
            if f"{destination.id}:{landmark.id}" in selected_ids:
                names.append(landmark.name)
    return names


def download_custom_landmark_images(
    destinations: list[Destination],
    selected: list[str],
    request_id: str,
    *,
    skip_selection_ids: set[str] | None = None,
) -> dict[str, Path]:
    if not destinations:
        return {}
    selected_ids = set(selected)
    skipped = skip_selection_ids or set()
    output_dir = storage.RUNTIME_DIR / "custom-images" / request_id
    downloaded: dict[str, Path] = {}
    with httpx.Client(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for destination in destinations:
            for landmark in destination.landmarks:
                selection_id = f"{destination.id}:{landmark.id}"
                if selection_id not in selected_ids or selection_id in skipped:
                    continue
                image_url = str(landmark.image or "").strip()
                if not _is_allowed_custom_image_url(image_url):
                    continue
                output_base = output_dir / destination.id / landmark.id
                try:
                    image_path = _download_custom_landmark_image(client, image_url, output_base)
                except httpx.HTTPError:
                    continue
                if image_path:
                    downloaded[selection_id] = image_path
    return downloaded


def _is_allowed_custom_image_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and host in CUSTOM_LANDMARK_IMAGE_HOSTS


def _download_custom_landmark_image(
    client: httpx.Client,
    url: str,
    output_base: Path,
) -> Path | None:
    response = client.get(
        url,
        headers={
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").split(";", maxsplit=1)[0].lower()
    if not content_type.startswith("image/"):
        return None
    if len(response.content) > CUSTOM_LANDMARK_IMAGE_MAX_BYTES:
        return None
    output_path = output_base.with_suffix(_custom_image_extension(url, content_type))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    return output_path


def _custom_image_extension(url: str, content_type: str) -> str:
    path_suffix = Path(urlparse(url).path).suffix.lower()
    if path_suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return path_suffix
    return {
        "image/png": ".png",
        "image/webp": ".webp",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
    }.get(content_type, ".jpg")


def create_local_lineart_fallbacks(
    destinations: list[Destination],
    selected: list[str],
    request_id: str,
    reference_images: dict[str, Path] | None = None,
    allow_named_placeholder: bool = True,
) -> dict[str, Path]:
    if not destinations:
        return {}
    selected_ids = set(selected)
    reference_images = reference_images or {}
    output_dir = storage.RUNTIME_DIR / "generated" / "lineart-local" / request_id
    lineart_images: dict[str, Path] = {}
    for destination in destinations:
        for landmark in destination.landmarks:
            selection_id = f"{destination.id}:{landmark.id}"
            if selection_id not in selected_ids:
                continue
            output_path = output_dir / destination.id / f"{landmark.id}.png"
            reference_image = reference_images.get(selection_id)
            if not reference_image or not _write_reference_lineart(reference_image, output_path):
                if not allow_named_placeholder:
                    continue
                _write_named_lineart_placeholder(
                    landmark.name,
                    destination.city,
                    destination.country,
                    output_path,
                )
            lineart_images[selection_id] = output_path
    return lineart_images


def _write_reference_lineart(reference_image: Path, output_path: Path) -> bool:
    try:
        with Image.open(reference_image) as source:
            image = ImageOps.exif_transpose(source).convert("L")
    except (OSError, UnidentifiedImageError):
        return False

    image.thumbnail((1080, 720), Image.Resampling.LANCZOS)
    image = image.filter(ImageFilter.GaussianBlur(radius=1.2))
    edges = image.filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.autocontrast(edges, cutoff=8)
    lineart = ImageOps.invert(edges)
    lineart = lineart.point(lambda pixel: 0 if pixel < 185 else 255).convert("L")

    canvas = Image.new("L", LINEART_CANVAS_SIZE, "white")
    x = (LINEART_CANVAS_SIZE[0] - lineart.width) // 2
    y = (LINEART_CANVAS_SIZE[1] - lineart.height) // 2
    canvas.paste(lineart, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path, "PNG")
    simplify_child_coloring_lineart(output_path)
    return True


def _write_named_lineart_placeholder(
    landmark_name: str,
    city: str,
    country: str,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", LINEART_CANVAS_SIZE, "white")
    draw = ImageDraw.Draw(image)
    font_large = _lineart_font(54)
    font_medium = _lineart_font(31)
    font_small = _lineart_font(25)

    draw.rounded_rectangle((90, 80, 1110, 770), radius=38, outline="black", width=5)
    draw.rounded_rectangle((165, 155, 1035, 600), radius=28, outline="black", width=3)
    draw.line((250, 665, 950, 665), fill="black", width=3)
    draw.line((250, 715, 950, 715), fill="black", width=3)
    draw.text((600, 335), landmark_name, anchor="mm", fill="black", font=font_large)
    draw.text((600, 405), f"{city}, {country}", anchor="mm", fill="black", font=font_medium)
    draw.text(
        (600, 535),
        "Desenhe este lugar do seu jeito.",
        anchor="mm",
        fill="black",
        font=font_small,
    )
    image.save(output_path)
    return output_path


def _lineart_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


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


def generate_selected_landmark_lineart(
    destinations: list[Destination],
    selected: list[str],
    request_id: str,
    generator,
    reference_images: dict[str, Path] | None = None,
) -> dict[str, Path]:
    selected_ids = set(selected)
    reference_images = reference_images or {}
    lineart_output_dir = Path("runtime/generated/lineart") / request_id
    generation_jobs = []
    for destination in destinations:
        for landmark in destination.landmarks:
            selection_id = f"{destination.id}:{landmark.id}"
            if selection_id not in selected_ids:
                continue
            generation_jobs.append(
                (
                    selection_id,
                    landmark.name,
                    destination.city,
                    destination.country,
                    _lineart_reference_for_landmark(landmark, reference_images.get(selection_id)),
                    lineart_output_dir / destination.id / f"{landmark.id}.png",
                )
            )

    if not generation_jobs:
        return {}

    max_workers = min(image_generation_concurrency(), len(generation_jobs))
    lineart_images: dict[str, Path] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_generate_landmark_lineart, generator, *generation_job): (
                generation_job[0]
            )
            for generation_job in generation_jobs
        }
        for future in as_completed(futures):
            try:
                selection_id, lineart_path = future.result()
            except Exception:
                continue
            lineart_images[selection_id] = lineart_path
    return lineart_images


def _generate_landmark_lineart(
    generator,
    selection_id: str,
    landmark_name: str,
    city: str,
    country: str,
    reference_image: Path,
    lineart_output_path: Path,
) -> tuple[str, Path]:
    lineart_path = generator.generate_landmark_lineart(
        landmark_name=landmark_name,
        city=city,
        country=country,
        reference_image=reference_image,
        output_path=lineart_output_path,
    )
    return selection_id, lineart_path


def _lineart_reference_for_landmark(landmark: Landmark, reference_image: Path | None) -> Path:
    if reference_image:
        return reference_image
    if isinstance(landmark.image, Path):
        return landmark.image
    return Path("README.md")


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
        f"{landmark.name}, {landmark.city}, {landmark.country}" for landmark in custom_landmarks
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
            landmark.model_copy(update={"description": description}) if description else landmark
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
                if _is_allowed_custom_image_url(str(landmark.image or "").strip()):
                    continue
                selection_id = f"{destination.id}:{landmark.id}"
                try:
                    asset = fetch_landmark_asset(client, destination, landmark, output_dir)
                except httpx.HTTPError:
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
                except httpx.HTTPError:
                    asset = None
                if asset:
                    assets[selection_id] = asset
    return assets


def serialize_preview_destinations(
    destinations: list[Destination],
    parsed_landmarks: list[ParsedLandmark] | list[dict[str, object]],
    images: dict[str, object],
    location_metadata: dict[str, dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    locations = location_metadata or {}
    default_confidence = 1.0 if not parsed_landmarks else 0
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
                    "confidence": confidence_by_name.get(landmark.name, default_confidence),
                    "image": (
                        serialize_preview_image(images.get(f"{destination.id}:{landmark.id}"))
                        or _location_preview_image(locations.get(f"{destination.id}:{landmark.id}"))
                    ),
                    "image_attributions": _location_image_attributions(
                        locations.get(f"{destination.id}:{landmark.id}"),
                    ),
                    **_preview_location_metadata(
                        locations.get(f"{destination.id}:{landmark.id}"),
                    ),
                }
                for landmark in destination.landmarks
            ],
        }
        for destination in destinations
    ]


def _location_preview_image(location: dict[str, object] | None) -> dict[str, str] | None:
    image_url = str((location or {}).get("image_url") or "")
    if not image_url:
        return None
    return {
        "image_url": image_url,
        "source_url": "",
        "author": "",
        "license_short_name": "",
        "license_url": "",
    }


def _location_image_attributions(location: dict[str, object] | None) -> list[dict[str, str]]:
    attributions = (location or {}).get("image_attributions")
    if not isinstance(attributions, list):
        return []
    return [attribution for attribution in attributions if isinstance(attribution, dict)]


def _preview_location_metadata(location: dict[str, object] | None) -> dict[str, object]:
    if not location:
        return {
            "location_status": "missing",
            "place_id": "",
            "google_maps_uri": "",
            "formatted_address": "",
            "latitude": None,
            "longitude": None,
        }
    return {
        "location_status": str(location.get("location_status") or "resolved"),
        "place_id": str(location.get("place_id") or ""),
        "google_maps_uri": str(location.get("google_maps_uri") or ""),
        "formatted_address": str(location.get("formatted_address") or ""),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
    }


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
