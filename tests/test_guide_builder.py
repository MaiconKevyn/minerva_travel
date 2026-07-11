from pathlib import Path

from minerva_travel.catalog import load_catalog
from minerva_travel.guide_builder import build_guide_context
from minerva_travel.models import GuideItineraryPlan, GuideRequest, RestaurantRecommendation
from minerva_travel.wikimedia_assets import WikimediaAsset


def test_build_guide_context_keeps_only_selected_landmarks():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice", "Antonio"],
        parents_names=["Ana", "Otavio"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "london:big-ben", "lisbon:oceanario"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert [item.destination.id for item in context.destinations] == ["paris", "london", "lisbon"]
    assert [item.landmarks[0].id for item in context.destinations] == [
        "eiffel-tower",
        "big-ben",
        "oceanario",
    ]


def test_build_guide_context_preserves_catalog_order_inside_destination():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:louvre", "paris:eiffel-tower"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert [landmark.id for landmark in context.destinations[0].landmarks] == [
        "eiffel-tower",
        "louvre",
    ]


def test_build_guide_context_uses_reviewed_destination_and_stop_order():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    itinerary = GuideItineraryPlan.model_validate(
        {
            "destinations": [
                {"id": "london", "place": "Londres", "timing": "primeiro", "days": 1, "order": 1},
                {"id": "paris", "place": "Paris", "timing": "depois", "days": 2, "order": 2},
            ],
            "days": [
                {
                    "day": 1,
                    "title": "Londres",
                    "stops": [
                        {
                            "selection_id": "london:big-ben",
                            "name": "Big Ben",
                            "destination_id": "london",
                        },
                    ],
                },
                {
                    "day": 2,
                    "title": "Paris",
                    "stops": [
                        {
                            "selection_id": "paris:louvre",
                            "name": "Louvre",
                            "destination_id": "paris",
                        },
                    ],
                },
            ],
            "unplanned_stops": [
                {
                    "selection_id": "paris:eiffel-tower",
                    "name": "Torre Eiffel",
                    "destination_id": "paris",
                },
            ],
        }
    )
    request = GuideRequest(
        title="Londres e Paris",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "london:big-ben", "paris:louvre"],
        itinerary=itinerary,
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert [item.destination.id for item in context.destinations] == ["london", "paris"]
    assert [landmark.id for landmark in context.destinations[1].landmarks] == [
        "louvre",
        "eiffel-tower",
    ]


def test_build_guide_context_includes_summary_image():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    summary_image = Path("runtime/generated/summary.png")

    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        summary_image=summary_image,
    )

    assert context.summary_image == summary_image


def test_build_guide_context_creates_single_destination_activity_plan():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        children_ages=[6],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "paris:louvre"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    destination_activities = [
        activity for activity in context.activity_plan if activity.destination_id == "paris"
    ]
    assert len(destination_activities) >= 2
    assert all(activity.destination_id == "paris" for activity in destination_activities)
    assert all(activity.title for activity in destination_activities)
    assert all(activity.prompt for activity in destination_activities)
    assert all(activity.complexity == "early_reader" for activity in destination_activities)


def test_build_guide_context_word_search_activity_carries_playable_grid():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        children_ages=[7],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "paris:louvre"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    word_search = next(
        activity for activity in context.activity_plan if activity.type == "word_search"
    )
    assert len(word_search.word_search_grid) == 10
    assert all(len(row) == 10 for row in word_search.word_search_grid)
    assert word_search.words
    assert "DIA1" not in word_search.words
    columns = ["".join(row[index] for row in word_search.word_search_grid) for index in range(10)]
    searchable = list(word_search.word_search_grid) + columns
    for word in word_search.words:
        assert any(word in line for line in searchable)


def test_build_guide_context_never_plans_spot_the_difference_without_art():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        children_ages=[11],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower", "paris:louvre", "london:big-ben"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert all(activity.type != "spot_the_difference" for activity in context.activity_plan)


def test_build_guide_context_diversifies_activity_types_for_multiple_destinations():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice", "Antonio"],
        children_ages=[9, 11],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=[
            "paris:eiffel-tower",
            "london:big-ben",
            "lisbon:oceanario",
        ],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))
    activity_types = {activity.type for activity in context.activity_plan}

    assert len(context.activity_plan) >= 3
    assert len(activity_types) >= 2
    assert {activity.destination_id for activity in context.activity_plan} == {
        "paris",
        "london",
        "lisbon",
    }
    assert {activity.complexity for activity in context.activity_plan} == {"older_child"}


def test_build_guide_context_uses_youngest_child_for_activity_complexity():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice", "Antonio"],
        children_ages=[4, 10],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["lisbon:oceanario", "lisbon:pastel-de-belem"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert {activity.complexity for activity in context.activity_plan} == {"preschool"}
    assert any(activity.extension_prompt for activity in context.activity_plan)


def test_build_guide_context_uses_family_activity_complexity_without_ages():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert context.activity_plan
    assert {activity.complexity for activity in context.activity_plan} == {"family"}


def test_build_guide_context_omits_restaurants_without_entitlement():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )

    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        restaurant_recommendations=[
            RestaurantRecommendation(
                destination_id="paris",
                name="Bistro Familiar",
                nearby_context="perto de Torre Eiffel",
                reason="Boa pausa para familia entre passeios.",
            )
        ],
    )

    assert request.restaurant_recommendations_extra is False
    assert context.restaurant_recommendations == []


def test_build_guide_context_includes_restaurants_with_entitlement():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
        restaurant_recommendations_extra=True,
    )

    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        restaurant_recommendations=[
            RestaurantRecommendation(
                destination_id="paris",
                name="Bistro Familiar",
                nearby_context="perto de Torre Eiffel",
                reason="Boa pausa para familia entre passeios.",
                cuisine="francesa",
                suitability_notes=["Cardapio simples para criancas"],
            )
        ],
    )

    assert len(context.restaurant_recommendations) == 1
    assert context.restaurant_recommendations[0].name == "Bistro Familiar"
    assert context.restaurant_recommendations[0].nearby_context == "perto de Torre Eiffel"


def test_build_guide_context_adds_one_language_activity_per_known_destination():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        children_ages=[6],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=[
            "paris:eiffel-tower",
            "london:big-ben",
            "lisbon:oceanario",
        ],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))
    language_activities = [
        activity for activity in context.activity_plan if activity.type == "language_learning"
    ]

    assert [activity.destination_id for activity in language_activities] == [
        "paris",
        "london",
        "lisbon",
    ]
    assert [activity.language_phrase for activity in language_activities] == [
        "Bonjour",
        "Thank you",
        "Obrigado/obrigada",
    ]
    assert all(activity.language_meaning for activity in language_activities)
    assert all(activity.language_name for activity in language_activities)


def test_build_guide_context_omits_language_activity_when_language_is_uncertain():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    custom_destination = catalog.destinations[0].model_copy(
        update={
            "id": "custom-atlantida",
            "city": "Cidade Misteriosa",
            "country": "Atlantida",
            "language_name": None,
            "language_tips": [],
        }
    )
    catalog = catalog.model_copy(update={"destinations": [custom_destination]})
    request = GuideRequest(
        title="Guia Misterioso",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["custom-atlantida:eiffel-tower"],
    )

    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    assert context.activity_plan
    assert all(activity.type != "language_learning" for activity in context.activity_plan)


def test_build_guide_context_uses_preschool_language_prompt_for_ages_3_to_5():
    activity = _language_activity_for_ages([4])

    assert activity.complexity == "preschool"
    assert activity.language_phrase == "Bonjour"
    assert "desenhe" in activity.prompt.lower()
    assert "palavra" in activity.prompt.lower()


def test_build_guide_context_uses_early_reader_language_prompt_for_ages_6_to_8():
    activity = _language_activity_for_ages([7])

    assert activity.complexity == "early_reader"
    assert "leia" in activity.prompt.lower()
    assert "placa" in activity.prompt.lower()


def test_build_guide_context_uses_older_child_language_prompt_for_ages_9_to_12():
    activity = _language_activity_for_ages([10])

    assert activity.complexity == "older_child"
    assert "desafio" in activity.prompt.lower()
    assert "compare" in activity.prompt.lower()


def test_build_guide_context_uses_youngest_language_band_for_mixed_ages():
    activity = _language_activity_for_ages([4, 10])

    assert activity.complexity == "preschool"
    assert "desenhe" in activity.prompt.lower()
    assert activity.extension_prompt
    assert "crianca maior" in activity.extension_prompt.lower()


def test_build_guide_context_uses_family_language_prompt_without_ages():
    activity = _language_activity_for_ages([])

    assert activity.complexity == "family"
    assert "família" in activity.prompt.lower()


def test_build_guide_context_uses_wikimedia_images_and_credits():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    assets = {
        "paris:eiffel-tower": WikimediaAsset(
            selection_id="paris:eiffel-tower",
            title="File:Eiffel Tower.jpg",
            source_url="https://commons.wikimedia.org/wiki/File:Eiffel_Tower.jpg",
            image_url="https://upload.wikimedia.org/example.jpg",
            local_path=Path("runtime/wikimedia/paris/eiffel-tower.jpg"),
            author="Jane Doe",
            license_short_name="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            credit="Jane Doe / Wikimedia Commons",
        )
    }

    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        wikimedia_assets=assets,
    )

    assert context.destinations[0].landmarks[0].image == Path(
        "runtime/wikimedia/paris/eiffel-tower.jpg"
    )
    assert context.image_credits[0].landmark_name == "Torre Eiffel"


def _language_activity_for_ages(children_ages: list[int]):
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        children_ages=children_ages,
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    context = build_guide_context(request, catalog, Path("runtime/generated/cover.png"))

    return next(
        activity for activity in context.activity_plan if activity.type == "language_learning"
    )


def test_build_guide_context_keeps_local_wikimedia_path_for_secure_pdf():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    assets = {
        "paris:eiffel-tower": WikimediaAsset(
            selection_id="paris:eiffel-tower",
            title="File:Eiffel Tower.jpg",
            source_url="https://commons.wikimedia.org/wiki/File:Eiffel_Tower.jpg",
            image_url="https://upload.wikimedia.org/example.jpg",
            local_path=Path("runtime/wikimedia/paris/eiffel-tower.jpg"),
            storage_path="paris/eiffel-tower.jpg",
            author="Jane Doe",
            license_short_name="CC BY-SA 4.0",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            credit="Jane Doe / Wikimedia Commons",
        )
    }

    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        wikimedia_assets=assets,
    )

    assert context.destinations[0].landmarks[0].image == assets["paris:eiffel-tower"].local_path


def test_build_guide_context_prefers_generated_landmark_images():
    catalog = load_catalog(Path("data/destinations/europe_2026.json"))
    request = GuideRequest(
        title="Pequenos Exploradores pela Europa",
        children_names=["Alice"],
        parents_names=["Ana"],
        year=2026,
        selected_landmarks=["paris:eiffel-tower"],
    )
    generated_path = Path("runtime/generated/landmarks/request/paris/eiffel-tower.png")
    lineart_path = Path("runtime/generated/lineart/request/paris/eiffel-tower.png")

    context = build_guide_context(
        request,
        catalog,
        Path("runtime/generated/cover.png"),
        landmark_images={"paris:eiffel-tower": generated_path},
        landmark_lineart_images={"paris:eiffel-tower": lineart_path},
    )

    landmark = context.destinations[0].landmarks[0]
    assert landmark.image == generated_path
    assert landmark.lineart_image == lineart_path
