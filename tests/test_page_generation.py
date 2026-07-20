import base64
from io import BytesIO

import httpx
import pytest
from PIL import Image, ImageDraw

from minerva_travel.page_generation import (
    OpenAIGuidePageGenerator,
    PageGenerationConfigurationError,
    PageGenerationError,
    activity_artwork_prompt,
    best_memory_artwork_prompt,
    cover_page_prompt,
    landmark_page_prompt,
    summary_page_prompt,
)


def _png_bytes(size=(1024, 1536), color="#4f86b7") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _lineart_png_bytes() -> bytes:
    buffer = BytesIO()
    image = Image.new("RGB", (1024, 1536), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((250, 310, 774, 1260), outline="black", width=14)
    draw.polygon([(260, 310), (512, 120), (764, 310)], outline="black", fill="white")
    for x in range(320, 741, 105):
        draw.rectangle((x, 480, x + 55, 570), outline="black", width=8)
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _response(image_bytes: bytes) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    return httpx.Response(
        200,
        request=request,
        json={"data": [{"b64_json": base64.b64encode(image_bytes).decode("ascii")}]},
    )


def _family_references(tmp_path):
    photo = tmp_path / "family.png"
    photo.write_bytes(_png_bytes(size=(400, 300)))
    cover = tmp_path / "cover-approved.png"
    cover.write_bytes(_png_bytes(color="#315c96"))
    return photo, cover


def test_cover_prompt_requires_exact_family_copy_and_visible_people():
    prompt = cover_page_prompt(
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        expected_visible_family_member_count=4,
    )

    assert '"Família Moraes"' in prompt
    assert '"Julho de 2026"' in prompt
    assert "exactly 4 visible people" in prompt
    assert "verbatim" in prompt
    assert "Do not include any other readable text" in prompt


def test_summary_prompt_lists_every_stop_as_exact_copy():
    prompt = summary_page_prompt(
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Museu do Louvre"],
    )

    assert '1. "Torre Eiffel"' in prompt
    assert '2. "Museu do Louvre"' in prompt
    assert '"Nosso roteiro"' in prompt
    assert "Do not invent, merge or omit stops" in prompt


def test_openai_cover_uses_official_edit_contract_and_persists_png(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes())

    photo = tmp_path / "family.png"
    photo.write_bytes(_png_bytes(size=(400, 300)))
    output = tmp_path / "cover.png"
    generator = OpenAIGuidePageGenerator(
        api_key="test-key",
        model="gpt-image-2",
        quality="low",
        transport=transport,
    )

    assert (
        generator.generate_cover_page(
            family_photo=photo,
            output_path=output,
            family_title="Família Moraes",
            trip_date="2026",
            landmark_names=["Torre Eiffel"],
            expected_visible_family_member_count=3,
        )
        == output
    )
    method, url, kwargs = calls[0]
    assert method == "POST"
    assert url.endswith("/images/edits")
    assert kwargs["data"]["model"] == "gpt-image-2"
    assert "input_fidelity" not in kwargs["data"]
    assert kwargs["data"]["size"] == "1024x1536"
    assert [field for field, _file in kwargs["files"]] == ["image[]"]
    with Image.open(output) as image:
        assert image.size == (1024, 1536)
        assert image.format == "PNG"


def test_openai_summary_uses_canonical_family_edit_contract(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#69b482"))

    output = tmp_path / "summary.png"
    photo, cover = _family_references(tmp_path)
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    generator.generate_summary_page(
        family_photo=photo,
        family_cover=cover,
        output_path=output,
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        expected_visible_family_member_count=4,
    )
    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert kwargs["data"]["output_format"] == "png"
    assert [file_data[0] for _field, file_data in kwargs["files"]] == [
        "family.png",
        "cover-approved.png",
    ]
    prompt = kwargs["data"]["prompt"]
    assert '"Coliseu"' in prompt
    assert "Input image 1 is the original family photo" in prompt
    assert "Input image 2 is the approved cover" in prompt
    assert "Show exactly 4 family members together" in prompt
    assert "never introduce another detailed person" in prompt


def test_cover_revision_uses_original_photo_selected_cover_and_user_feedback(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#8f6cb3"))

    photo = tmp_path / "family.png"
    photo.write_bytes(_png_bytes(size=(400, 300)))
    reference = tmp_path / "cover-1.png"
    reference.write_bytes(_png_bytes())
    generator = OpenAIGuidePageGenerator(
        api_key="test-key", model="gpt-image-2", transport=transport
    )

    generator.generate_cover_page(
        family_photo=photo,
        reference_page=reference,
        revision_instruction="Mude o estilo para animação 3D e use tons azuis.",
        output_path=tmp_path / "cover-2.png",
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel"],
        expected_visible_family_member_count=3,
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [field for field, _file in kwargs["files"]] == ["image[]", "image[]"]
    assert [file_data[0] for _field, file_data in kwargs["files"]] == [
        "family.png",
        "cover-1.png",
    ]
    prompt = kwargs["data"]["prompt"]
    assert "Input image 1 is the original family photo" in prompt
    assert '"Mude o estilo para animação 3D e use tons azuis."' in prompt
    assert "requested visual style replaces" in prompt
    assert '"Família Moraes"' in prompt
    assert "change family identity or the required member count" in prompt


def test_summary_revision_uses_selected_page_and_visible_variation_default(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#cc825f"))

    reference = tmp_path / "summary-1.png"
    reference.write_bytes(_png_bytes())
    photo, cover = _family_references(tmp_path)
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)

    generator.generate_summary_page(
        family_photo=photo,
        family_cover=cover,
        output_path=tmp_path / "summary-2.png",
        reference_page=reference,
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [file_data[0] for _field, file_data in kwargs["files"]] == [
        "family.png",
        "cover-approved.png",
        "summary-1.png",
    ]
    assert "Input image 3 is the selected current-page attempt" in kwargs["data"]["prompt"]
    assert "Create a visibly different alternative" in kwargs["data"]["prompt"]
    assert '2. "Coliseu"' in kwargs["data"]["prompt"]


def test_landmark_page_defaults_to_generation_without_people_or_family_inputs(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#d09a55"))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    generator.generate_landmark_page(
        family_photo=None,
        family_cover=None,
        output_path=tmp_path / "landmark.png",
        family_title="Família Moraes",
        trip_date="2026",
        landmark_name="Torre Eiffel",
        city="Paris",
        country="França",
        description="Uma torre de ferro que virou símbolo de Paris.",
        curiosity="Observe as formas geométricas que se repetem.",
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/generations")
    assert "files" not in kwargs
    prompt = kwargs["json"]["prompt"]
    assert "as the only visual subject" in prompt
    assert "Do not depict any person" in prompt
    assert "silhouette, or crowd" in prompt
    assert "overrides any user revision feedback" in prompt
    assert '"Uma torre de ferro que virou símbolo de Paris."' in prompt
    assert '"Observe as formas geométricas que se repetem."' in prompt


def test_landmark_page_can_include_same_family_with_canonical_references(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#d09a55"))

    photo, cover = _family_references(tmp_path)
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    generator.generate_landmark_page(
        family_photo=photo,
        family_cover=cover,
        include_family=True,
        output_path=tmp_path / "landmark.png",
        family_title="Família Moraes",
        trip_date="2026",
        landmark_name="Torre Eiffel",
        city="Paris",
        country="França",
        description="Uma torre de ferro que virou símbolo de Paris.",
        curiosity="Observe as formas geométricas que se repetem.",
        expected_visible_family_member_count=4,
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [file_data[0] for _field, file_data in kwargs["files"]] == [
        "family.png",
        "cover-approved.png",
    ]
    prompt = kwargs["data"]["prompt"]
    assert "complete canonical family exploring together" in prompt
    assert "Do not invent, replace, omit, merge" in prompt
    assert "clothing colors" in prompt


def test_landmark_revision_without_family_uses_only_selected_page_and_removes_people(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#6faec9"))

    reference = tmp_path / "landmark-with-family.png"
    reference.write_bytes(_png_bytes())
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    generator.generate_landmark_page(
        family_photo=None,
        family_cover=None,
        reference_page=reference,
        revision_instruction="Mantenha a família e acrescente turistas.",
        output_path=tmp_path / "landmark-without-family.png",
        family_title="Família Moraes",
        trip_date="2026",
        landmark_name="Torre Eiffel",
        city="Paris",
        country="França",
        description="Uma torre de ferro que virou símbolo de Paris.",
        curiosity="Observe as formas geométricas que se repetem.",
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [file_data[0] for _field, file_data in kwargs["files"]] == ["landmark-with-family.png"]
    prompt = kwargs["data"]["prompt"]
    assert "Remove every person that may appear in it" in prompt
    assert "This invariant overrides any user revision feedback" in prompt
    assert '"Uma torre de ferro que virou símbolo de Paris."' in prompt
    assert '"Observe as formas geométricas que se repetem."' in prompt


def test_openai_page_generator_rejects_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(PageGenerationConfigurationError):
        OpenAIGuidePageGenerator(api_key="")


def test_openai_page_generator_rejects_wrong_dimensions(tmp_path):
    def transport(_method, _url, **_kwargs):
        return _response(_png_bytes(size=(512, 512)))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    photo, cover = _family_references(tmp_path)
    with pytest.raises(PageGenerationError, match="dimensões"):
        generator.generate_summary_page(
            family_photo=photo,
            family_cover=cover,
            output_path=tmp_path / "bad.png",
            family_title="Família Moraes",
            trip_date="2026",
            landmark_names=["Torre Eiffel"],
        )


def test_openai_error_exposes_only_safe_diagnostic_identifiers(tmp_path):
    def transport(_method, url, **_kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(
            400,
            request=request,
            json={
                "error": {
                    "code": "invalid_input_fidelity_model",
                    "type": "image_generation_user_error",
                    "param": "input_fidelity",
                    "message": "private family prompt must never reach the UI",
                }
            },
        )

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    photo, cover = _family_references(tmp_path)
    with pytest.raises(PageGenerationError) as captured:
        generator.generate_summary_page(
            family_photo=photo,
            family_cover=cover,
            output_path=tmp_path / "bad.png",
            family_title="Família Moraes",
            trip_date="2026",
            landmark_names=["Torre Eiffel"],
        )

    assert "code=invalid_input_fidelity_model" in str(captured.value)
    assert "private family prompt" not in str(captured.value)


def test_landmark_prompt_keeps_exact_description_and_curiosity_during_revision():
    prompt = landmark_page_prompt(
        family_title="Família Moraes",
        trip_date="2026",
        landmark_name="Torre Eiffel",
        city="Paris",
        country="França",
        description="Uma torre de ferro que virou símbolo de Paris.",
        curiosity="Observe como as formas se repetem do chão até o topo.",
        revision_instruction="Use tons mais quentes.",
        has_revision_reference=True,
    )

    assert '"Uma torre de ferro que virou símbolo de Paris."' in prompt
    assert '"Observe como as formas se repetem do chão até o topo."' in prompt
    assert '"Use tons mais quentes."' in prompt
    assert "render exactly these strings, verbatim, once each" in prompt


def test_activity_prompt_maps_fixed_reference_order_and_forbids_people_and_model_text():
    prompt = activity_artwork_prompt(
        activity_type="detail_hunt",
        landmark_name="Torre Eiffel",
        city="Paris",
        country="França",
        age_complexity="early_reader",
        has_landmark_reference=True,
        has_revision_reference=True,
        revision_instruction="Mude para estilo de quadrinhos e inclua a família.",
    )

    assert "Input image 1 is a sanitized local visual reference" in prompt
    assert "Input image 2 is the approved landmark guide page" in prompt
    assert "Input image 3 is the selected current activity attempt" in prompt
    assert "No family photo or family identity reference is supplied" in prompt
    assert "Remove every person" in prompt
    assert "Do not render any" in prompt
    assert "checkbox, grid" in prompt
    assert "invariants override both reference content and user feedback" in prompt


def test_coloring_generation_edits_landmark_refs_then_composites_printable_png(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_lineart_png_bytes())

    source = tmp_path / "sanitized-landmark.png"
    approved = tmp_path / "approved-landmark.png"
    selected = tmp_path / "selected-coloring.png"
    source.write_bytes(_png_bytes(size=(800, 600)))
    approved.write_bytes(_png_bytes())
    selected.write_bytes(_png_bytes())
    output = tmp_path / "coloring.png"
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)

    generator.generate_coloring_page(
        output_path=output,
        landmark_reference=source,
        approved_landmark_page=approved,
        landmark_context={
            "selection_id": "paris:eiffel",
            "name": "Torre Eiffel",
            "city": "Paris",
            "country": "França",
            "age_complexity": "early_reader",
        },
        activity_spec={"instruction": "Pinte a torre com suas cores favoritas."},
        revision_instruction="Use linhas um pouco mais largas.",
        reference_page=selected,
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [file_data[0] for _field, file_data in kwargs["files"]] == [
        "sanitized-landmark.png",
        "approved-landmark.png",
        "selected-coloring.png",
    ]
    assert "black-and-white children's coloring-book line art" in kwargs["data"]["prompt"]
    assert "Remove every person" in kwargs["data"]["prompt"]
    assert not (tmp_path / ".coloring.provider.png").exists()
    with Image.open(output) as image:
        assert image.size == (1024, 1536)
        colors = image.convert("RGB").getcolors(maxcolors=1024 * 1536)
        assert colors is not None
        assert {color for _count, color in colors} <= {(0, 0, 0), (255, 255, 255)}


@pytest.mark.parametrize(
    ("method_name", "activity_spec", "prompt_fragment"),
    [
        (
            "generate_detail_hunt_page",
            {
                "instruction": "Marque cada descoberta.",
                "clues": [
                    "Encontre o contorno principal.",
                    "Ache uma forma repetida.",
                    "Observe um detalhe no topo.",
                ],
            },
            "deterministic checklist",
        ),
        (
            "generate_word_search_page",
            {
                "instruction": "Encontre as palavras.",
                "words": ["TORRE", "EIFFEL", "PARIS", "VIAGEM"],
                "seed": "paris:eiffel:word_search",
            },
            "low-detail for a puzzle",
        ),
        (
            "generate_drawing_page",
            {"prompt": "Desenhe o que mais chamou sua atenção."},
            "central 70 percent completely empty and white",
        ),
    ],
)
def test_activity_generators_use_only_approved_landmark_reference_and_exact_subtype(
    tmp_path, method_name, activity_spec, prompt_fragment
):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#dce9ef"))

    approved = tmp_path / "approved-landmark.png"
    approved.write_bytes(_png_bytes())
    output = tmp_path / f"{method_name}.png"
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)

    method = getattr(generator, method_name)
    method(
        output_path=output,
        landmark_reference=None,
        approved_landmark_page=approved,
        landmark_context={
            "selection_id": "paris:eiffel",
            "name": "Torre Eiffel",
            "city": "Paris",
            "country": "França",
            "age_complexity": "early_reader",
        },
        activity_spec=activity_spec,
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [file_data[0] for _field, file_data in kwargs["files"]] == ["approved-landmark.png"]
    assert prompt_fragment in kwargs["data"]["prompt"]
    assert "family photo" in kwargs["data"]["prompt"]
    assert output.exists()


def test_word_search_revision_keeps_seeded_grid_identical(tmp_path):
    colors = iter(["#eef4f6", "#f7dfc9"])

    def transport(_method, _url, **_kwargs):
        return _response(_png_bytes(color=next(colors)))

    approved = tmp_path / "approved.png"
    selected = tmp_path / "selected.png"
    approved.write_bytes(_png_bytes())
    selected.write_bytes(_png_bytes())
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    kwargs = {
        "landmark_reference": None,
        "approved_landmark_page": approved,
        "landmark_context": {
            "selection_id": "paris:eiffel",
            "name": "Torre Eiffel",
            "city": "Paris",
            "country": "França",
        },
        "activity_spec": {
            "instruction": "Encontre as palavras.",
            "words": ["TORRE", "EIFFEL", "PARIS", "VIAGEM"],
            "seed": "stable-word-search",
        },
    }

    first = generator.generate_word_search_page(output_path=tmp_path / "first.png", **kwargs)
    revised = generator.generate_word_search_page(
        output_path=tmp_path / "revised.png",
        reference_page=selected,
        revision_instruction="Mude apenas as cores.",
        **kwargs,
    )

    # Opaque deterministic puzzle regions remain byte-identical even when the
    # provider artwork changes between attempts.
    with Image.open(first) as first_image, Image.open(revised) as revised_image:
        puzzle_box = (177, 270, 847, 940)
        assert first_image.crop(puzzle_box).tobytes() == revised_image.crop(puzzle_box).tobytes()
        assert first_image.tobytes() != revised_image.tobytes()


def test_best_memory_first_attempt_generates_and_revision_edits_selected_attempt(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#f0dfca"))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    first = tmp_path / "memory-1.png"
    generator.generate_best_memory_page(
        output_path=first,
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Museu do Louvre"],
        age_complexity="early_reader",
    )
    generator.generate_best_memory_page(
        output_path=tmp_path / "memory-2.png",
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Museu do Louvre"],
        age_complexity="early_reader",
        revision_instruction="Use bordas azuis.",
        reference_page=first,
    )

    assert calls[0][1].endswith("/images/generations")
    assert "files" not in calls[0][2]
    assert calls[1][1].endswith("/images/edits")
    assert [file_data[0] for _field, file_data in calls[1][2]["files"]] == ["memory-1.png"]
    prompt = calls[1][2]["data"]["prompt"]
    assert "Never pre-fill" in prompt
    assert "Do not depict any person" in prompt
    assert '"Use bordas azuis."' in prompt


def test_best_memory_prompt_contains_trip_context_but_no_family_reference_contract():
    prompt = best_memory_artwork_prompt(
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        age_complexity="preschool",
    )

    assert "Torre Eiffel, Coliseu" in prompt
    assert "Família Moraes" in prompt
    assert "PEOPLE-FREE, TEXT-FREE, ANSWER-FREE" in prompt
    assert "This first version has no input image" in prompt


def test_activity_generation_rejects_missing_local_reference_before_provider_call(tmp_path):
    called = False

    def transport(_method, _url, **_kwargs):
        nonlocal called
        called = True
        return _response(_png_bytes())

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    with pytest.raises(PageGenerationError, match="local"):
        generator.generate_drawing_page(
            output_path=tmp_path / "drawing.png",
            landmark_reference=None,
            approved_landmark_page=tmp_path / "outside-client-path.png",
            landmark_context={"name": "Torre Eiffel", "city": "Paris", "country": "França"},
            activity_spec={"prompt": "Desenhe."},
        )

    assert called is False
    assert not (tmp_path / "drawing.png").exists()


def test_activity_generation_rejects_wrong_provider_output_without_partial_attempt(tmp_path):
    def transport(_method, _url, **_kwargs):
        return _response(_png_bytes(size=(512, 512)))

    approved = tmp_path / "approved.png"
    approved.write_bytes(_png_bytes())
    output = tmp_path / "drawing.png"
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)

    with pytest.raises(PageGenerationError, match="dimensões"):
        generator.generate_drawing_page(
            output_path=output,
            landmark_reference=None,
            approved_landmark_page=approved,
            landmark_context={"name": "Torre Eiffel", "city": "Paris", "country": "França"},
            activity_spec={"prompt": "Desenhe."},
        )

    assert not output.exists()
    assert not (tmp_path / ".drawing.provider.png").exists()
    assert not (tmp_path / ".drawing.png.tmp").exists()
