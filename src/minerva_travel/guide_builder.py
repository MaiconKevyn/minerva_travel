from collections import defaultdict
from pathlib import Path

from minerva_travel.destination_languages import lookup_destination_language, preferred_language_tip
from minerva_travel.models import (
    ActivityComplexity,
    ActivityType,
    Catalog,
    Destination,
    GuideActivity,
    GuideContext,
    GuideDestination,
    GuideRequest,
    Landmark,
    RestaurantRecommendation,
)
from minerva_travel.wikimedia_assets import ImageCredit, WikimediaAsset
from minerva_travel.word_search import build_word_search_grid


def build_guide_context(
    request: GuideRequest,
    catalog: Catalog,
    cover_image: Path,
    summary_image: Path | None = None,
    wikimedia_assets: dict[str, WikimediaAsset] | None = None,
    landmark_images: dict[str, Path] | None = None,
    landmark_lineart_images: dict[str, Path] | None = None,
    restaurant_recommendations: list[RestaurantRecommendation] | None = None,
) -> GuideContext:
    wikimedia_assets = wikimedia_assets or {}
    landmark_images = landmark_images or {}
    landmark_lineart_images = landmark_lineart_images or {}
    selected_by_destination: dict[str, set[str]] = defaultdict(set)
    for selected in request.selected_landmarks:
        destination_id, landmark_id = selected.split(":", maxsplit=1)
        selected_by_destination[destination_id].add(landmark_id)

    guide_destinations: list[GuideDestination] = []
    selection_order = _reviewed_selection_order(request)
    for destination in _reviewed_destination_order(request, catalog):
        selected_ids = selected_by_destination.get(destination.id, set())
        if not selected_ids:
            continue
        landmarks: list[Landmark] = []
        for landmark in destination.landmarks:
            if landmark.id not in selected_ids:
                continue
            selection_id = f"{destination.id}:{landmark.id}"
            asset = wikimedia_assets.get(selection_id)
            generated_image = landmark_images.get(selection_id)
            generated_lineart = landmark_lineart_images.get(selection_id)
            # O renderer PDF é local-only por segurança; URLs públicas de
            # storage nunca devem sobreviver até o template.
            asset_image = asset.local_path if asset else None
            if generated_image:
                landmarks.append(
                    landmark.model_copy(
                        update={
                            "image": generated_image,
                            "lineart_image": generated_lineart or landmark.lineart_image,
                        }
                    )
                )
            elif asset_image:
                landmarks.append(landmark.model_copy(update={"image": asset_image}))
            else:
                landmarks.append(landmark)
        if selection_order:
            landmarks.sort(
                key=lambda landmark: selection_order.get(
                    f"{destination.id}:{landmark.id}",
                    len(selection_order),
                )
            )
        if landmarks:
            guide_destinations.append(
                GuideDestination(destination=destination, landmarks=landmarks)
            )

    enabled_restaurant_recommendations = (
        restaurant_recommendations or [] if request.restaurant_recommendations_extra else []
    )
    return GuideContext(
        request=request,
        cover_image=cover_image,
        summary_image=summary_image,
        destinations=guide_destinations,
        activity_plan=_build_activity_plan(request, guide_destinations),
        image_credits=_collect_credits(request, catalog, wikimedia_assets),
        restaurant_recommendations=enabled_restaurant_recommendations,
    )


def _reviewed_destination_order(request: GuideRequest, catalog: Catalog) -> list[Destination]:
    if not request.itinerary:
        return list(catalog.destinations)
    order = {
        destination.id: index for index, destination in enumerate(request.itinerary.destinations)
    }
    return sorted(
        catalog.destinations,
        key=lambda destination: (order.get(destination.id, len(order)), destination.id),
    )


def _reviewed_selection_order(request: GuideRequest) -> dict[str, int]:
    if not request.itinerary:
        return {}
    selections: list[str] = []
    selections.extend(stop.selection_id for day in request.itinerary.days for stop in day.stops)
    selections.extend(stop.selection_id for stop in request.itinerary.unplanned_stops)
    selections.extend(request.selected_landmarks)
    return {selection_id: index for index, selection_id in enumerate(dict.fromkeys(selections))}


# "spot_the_difference" fica fora das rotações até existir arte pareada real;
# sem imagens, a pagina sairia com dois quadros vazios no PDF.
ACTIVITY_ROTATION_BY_COMPLEXITY: dict[ActivityComplexity, list[ActivityType]] = {
    "preschool": ["coloring", "detail_hunt", "drawing", "checklist"],
    "early_reader": ["word_search", "coloring", "detail_hunt", "checklist"],
    "older_child": ["word_search", "short_prompt", "detail_hunt", "checklist"],
    "family": ["coloring", "word_search", "detail_hunt", "checklist"],
}


def _build_activity_plan(
    request: GuideRequest,
    guide_destinations: list[GuideDestination],
) -> list[GuideActivity]:
    if not guide_destinations:
        return []

    complexity = _activity_complexity(request.children_ages)
    rotation = ACTIVITY_ROTATION_BY_COMPLEXITY[complexity]
    mixed_age_extension = _mixed_age_extension_needed(request.children_ages)
    activities: list[GuideActivity] = []

    for item in guide_destinations:
        activity_count = 2 if len(guide_destinations) == 1 else 1
        for offset in range(activity_count):
            landmark = item.landmarks[offset % len(item.landmarks)]
            activity_type = rotation[(len(activities)) % len(rotation)]
            activities.append(
                _activity_for_type(
                    activity_type,
                    item.destination.id,
                    item.destination.city,
                    landmark,
                    complexity,
                    mixed_age_extension,
                )
            )
        language_activity = _language_activity_for_destination(
            item.destination,
            complexity,
            mixed_age_extension,
        )
        if language_activity:
            activities.append(language_activity)

    return activities


def _activity_complexity(children_ages: list[int]) -> ActivityComplexity:
    valid_ages = [age for age in children_ages if age > 0]
    if not valid_ages:
        return "family"
    youngest = min(valid_ages)
    if youngest <= 5:
        return "preschool"
    if youngest <= 8:
        return "early_reader"
    return "older_child"


def _mixed_age_extension_needed(children_ages: list[int]) -> bool:
    valid_ages = [age for age in children_ages if age > 0]
    return bool(valid_ages and min(valid_ages) <= 5 and max(valid_ages) >= 9)


def _activity_for_type(
    activity_type: ActivityType,
    destination_id: str,
    city: str,
    landmark: Landmark,
    complexity: ActivityComplexity,
    include_extension: bool,
) -> GuideActivity:
    title, prompt = _activity_copy(activity_type, city, landmark.name, complexity)
    extension_prompt = None
    if include_extension:
        extension_prompt = (
            "Desafio extra: escreva uma pista para outra pessoa descobrir este lugar."
        )
    words: list[str] = []
    word_search_grid: list[str] = []
    if activity_type == "word_search":
        word_search_grid, words = build_word_search_grid(
            _activity_words(city, landmark.name),
            seed=f"{destination_id}:{landmark.id}",
        )
    return GuideActivity(
        destination_id=destination_id,
        type=activity_type,
        title=title,
        prompt=prompt,
        complexity=complexity,
        landmark_name=landmark.name,
        lineart_image=landmark.lineart_image,
        words=words,
        word_search_grid=word_search_grid,
        checklist_items=_activity_checklist(city, landmark.name),
        extension_prompt=extension_prompt,
    )


def _language_activity_for_destination(
    destination: Destination,
    complexity: ActivityComplexity,
    include_extension: bool,
) -> GuideActivity | None:
    language = lookup_destination_language(destination)
    if not language:
        return None
    tip = preferred_language_tip(language)
    title, prompt = _language_activity_copy(
        destination.city,
        language.name,
        tip.phrase,
        complexity,
    )
    extension_prompt = None
    if include_extension:
        extension_prompt = (
            "Desafio extra para a crianca maior: escreva onde essa palavra apareceu "
            "e compare com uma palavra parecida em portugues."
        )

    return GuideActivity(
        destination_id=destination.id,
        type="language_learning",
        title=title,
        prompt=prompt,
        complexity=complexity,
        phase="before",
        language_name=language.name,
        language_phrase=tip.phrase,
        language_pronunciation=tip.pronunciation,
        language_meaning=tip.meaning,
        checklist_items=[tip.use_case],
        extension_prompt=extension_prompt,
    )


def _language_activity_copy(
    city: str,
    language_name: str,
    phrase: str,
    complexity: ActivityComplexity,
) -> tuple[str, str]:
    if complexity == "preschool":
        return (
            f"Palavra em {language_name}",
            (
                f"Escute a palavra {phrase}, repita bem devagar e desenhe uma "
                f"coisa de {city} que combine com essa palavra."
            ),
        )
    if complexity == "early_reader":
        return (
            f"Frase para reconhecer em {language_name}",
            (
                f"Leia a palavra {phrase} com alguém da família e procure uma "
                f"placa, bilhete ou lugar em {city} onde ela poderia aparecer."
            ),
        )
    if complexity == "older_child":
        return (
            f"Desafio de idioma em {language_name}",
            (
                f"Desafio: compare {phrase} com uma palavra em português e "
                f"escreva quando você usaria essa expressão em {city}."
            ),
        )
    return (
        f"Idioma da viagem: {language_name}",
        (
            f"Em família, pratiquem {phrase} antes de sair e combinem uma "
            f"situação em {city} para tentar lembrar dessa palavra."
        ),
    )


def _activity_copy(
    activity_type: ActivityType,
    city: str,
    landmark_name: str,
    complexity: ActivityComplexity,
) -> tuple[str, str]:
    if activity_type == "coloring":
        return (
            "Colorir a lembrança",
            f"Use as cores que você imagina para lembrar de {landmark_name}.",
        )
    if activity_type == "word_search":
        return (
            "Caça-palavras da viagem",
            f"Encontre palavras ligadas a {city} e ao passeio em {landmark_name}.",
        )
    if activity_type == "spot_the_difference":
        return (
            "Jogo dos 7 erros",
            f"Observe {landmark_name} com atenção e crie diferenças para outra pessoa encontrar.",
        )
    if activity_type == "detail_hunt":
        return (
            "Caça ao detalhe",
            f"Procure uma forma, cor ou som especial em {landmark_name}.",
        )
    if activity_type == "short_prompt":
        return (
            "Pergunta de explorador",
            f"Escreva uma descoberta sobre {landmark_name} que você contaria para um amigo.",
        )
    if activity_type == "checklist":
        return (
            "Checklist do destino",
            f"Marque o que você viu, ouviu ou provou em {city}.",
        )
    title = "Desenho da aventura"
    prompt = f"Desenhe uma cena de {city} que você quer guardar na memória."
    if complexity == "preschool":
        prompt = f"Desenhe uma coisa que chamou sua atenção em {landmark_name}."
    return title, prompt


def _activity_words(city: str, landmark_name: str) -> list[str]:
    landmark_tokens = [token for token in landmark_name.split() if len(token) >= 4]
    words = [
        city.split()[0] if city else "",
        *landmark_tokens[:2],
        "família",
        "aventura",
        "viagem",
    ]
    return [word.upper() for word in words if word]


def _activity_checklist(city: str, landmark_name: str) -> list[str]:
    return [
        f"Encontrei um detalhe em {landmark_name}",
        f"Vi algo que lembra {city}",
        "Escolhi uma lembrança favorita",
    ]


def _collect_credits(
    request: GuideRequest,
    catalog: Catalog,
    wikimedia_assets: dict[str, WikimediaAsset],
) -> list[ImageCredit]:
    selected = set(request.selected_landmarks)
    credits: list[ImageCredit] = []
    for destination in catalog.destinations:
        for landmark in destination.landmarks:
            selection_id = f"{destination.id}:{landmark.id}"
            asset = wikimedia_assets.get(selection_id)
            if selection_id in selected and asset:
                credits.append(
                    ImageCredit(
                        landmark_name=landmark.name,
                        source_url=asset.source_url,
                        author=asset.author,
                        license_short_name=asset.license_short_name,
                        license_url=asset.license_url,
                        credit=asset.credit,
                    )
                )
    return credits
