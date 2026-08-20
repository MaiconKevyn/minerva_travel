import base64
import json
from io import BytesIO

import httpx
import pytest
from PIL import Image, ImageDraw

from minerva_travel.activity_page_compositor import (
    BAND,
    COVER_LOCKUP_BOTTOM,
    COVER_LOCKUP_TOP,
    SCENE_TEXT_BOTTOM,
    SUMMARY_ROUTE_INSET,
    compose_summary_page,
    summary_band,
)
from minerva_travel.page_generation import (
    SPOT_SCENE_SIZE,
    OpenAIGuidePageGenerator,
    PageGenerationConfigurationError,
    PageGenerationError,
    PageGenerationRetryableError,
    activity_artwork_prompt,
    best_memory_artwork_prompt,
    cover_page_prompt,
    destination_intro_page_prompt,
    family_coloring_artwork_prompt,
    homecoming_page_prompt,
    investigator_artwork_prompt,
    landmark_page_prompt,
    summary_page_prompt,
)

BAND_RGB = tuple(int(BAND[i : i + 2], 16) for i in (1, 3, 5))


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


def _error_response(status: int, *, retry_after: str = "") -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    headers = {"Retry-After": retry_after} if retry_after else {}
    return httpx.Response(
        status,
        request=request,
        headers=headers,
        json={"error": {"code": "rate_limit_exceeded", "type": "requests"}},
    )


def _mission_response(missions) -> httpx.Response:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return httpx.Response(
        200,
        request=request,
        json={"output_text": json.dumps({"missions": missions}, ensure_ascii=False)},
    )


def _family_references(tmp_path):
    photo = tmp_path / "family.png"
    photo.write_bytes(_png_bytes(size=(400, 300)))
    cover = tmp_path / "cover-approved.png"
    cover.write_bytes(_png_bytes(color="#315c96"))
    return photo, cover


def test_openai_rate_limit_retries_with_bounded_exponential_backoff(tmp_path):
    responses = iter(
        [
            _error_response(429),
            _error_response(429),
            _response(_png_bytes()),
        ]
    )
    sleeps = []
    calls = 0

    def transport(_method, _url, **_kwargs):
        nonlocal calls
        calls += 1
        return next(responses)

    generator = OpenAIGuidePageGenerator(
        api_key="test-key",
        transport=transport,
        retry_sleep=sleeps.append,
        retry_random=lambda: 0.5,
    )
    output = generator.generate_destination_intro_page(
        output_path=tmp_path / "destination.png",
        title="Roma",
        city="Roma",
        country="Itália",
        learning_points=["Uma cidade cheia de história."],
        curiosity="Observe as formas dos prédios antigos.",
        curiosity_label="Missão de observação",
        landmark_names=["Pantheon"],
    )

    assert calls == 3
    assert sleeps == [1.0, 2.0]
    assert output.exists()


def test_openai_long_rate_limit_is_returned_as_retryable_without_holding_request(tmp_path):
    sleeps = []

    def transport(_method, _url, **_kwargs):
        return _error_response(429, retry_after="75")

    generator = OpenAIGuidePageGenerator(
        api_key="test-key",
        transport=transport,
        retry_sleep=sleeps.append,
        retry_random=lambda: 0.5,
    )

    with pytest.raises(PageGenerationRetryableError) as raised:
        generator.generate_destination_intro_page(
            output_path=tmp_path / "destination.png",
            title="Roma",
            city="Roma",
            country="Itália",
            learning_points=["Uma cidade cheia de história."],
            curiosity="Observe as formas dos prédios antigos.",
            curiosity_label="Missão de observação",
            landmark_names=["Pantheon"],
        )

    assert raised.value.retry_after_seconds == 75
    assert sleeps == []
    assert not (tmp_path / "destination.png").exists()


def test_cover_prompt_stays_text_free_and_keeps_every_visible_person():
    prompt = cover_page_prompt(
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        expected_visible_family_member_count=4,
    )

    # A capa com foto tambem deixou de escrever: o compositor imprime o brasao
    # por cima. Enquanto o prompt pedia o nome, ele saia desenhado pela IA E
    # impresso pelo codigo, um em cima do outro.
    assert "TEXT-FREE CONTRACT" in prompt
    assert '"Família Moraes"' not in prompt
    assert '"Julho de 2026"' not in prompt
    # Quem aparece na capa continua sendo a familia inteira.
    assert "exactly 4 visible people" in prompt
    # E a faixa reservada ao brasao vem da geometria do compositor. No meio da
    # pagina ele atravessava a cabeca das pessoas: espremer quatro pessoas
    # abaixo de 62% da altura era um pedido que o modelo nao atendia.
    alta = round((COVER_LOCKUP_TOP - 60) / 1536 * 100)
    baixa = round((COVER_LOCKUP_BOTTOM + 60) / 1536 * 100)
    assert f"between {alta} and {baixa} percent of" in prompt
    assert "every head below" in prompt


def test_summary_prompt_lists_every_stop_without_writing_it_on_the_art():
    prompt = summary_page_prompt(
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Museu do Louvre"],
    )

    # As paradas continuam ditando as vinhetas, mas nao viram letra: o codigo
    # escreve a lista numerada embaixo, na fonte do caderno.
    assert "1. Torre Eiffel" in prompt
    assert "2. Museu do Louvre" in prompt
    assert "TEXT-FREE CONTRACT" in prompt
    assert "Nosso roteiro" not in prompt
    assert "Do not invent, merge or omit stops" in prompt
    # Cada parada ganha a sua faixa e o seu lado, e o lado oposto fica vazio
    # porque e la que o codigo escreve o nome. Sem esse contrato o nome caia
    # em cima da vinheta — nao ha como o codigo adivinhar onde ela foi parar.
    assert "in the RIGHT half" in prompt
    assert "in the LEFT half" in prompt
    assert "MUST STAY EMPTY" in prompt
    # E a rota e do codigo: duas rotas na mesma pagina seria o defeito obvio.
    assert "application draws the route itself" in prompt


def test_destination_intro_prompt_stays_text_free_and_forbids_people():
    prompt = destination_intro_page_prompt(
        title="Londres",
        city="Londres",
        country="Inglaterra",
        learning_points=[
            "Londres é uma cidade cheia de história.",
            "O Rio Tâmisa passa por lugares importantes da cidade.",
        ],
        curiosity="O Big Ben é o nome do sino que fica dentro da torre.",
        curiosity_label="Você sabia?",
        landmark_names=["Tower Bridge", "Big Ben"],
    )

    # O texto saiu do prompt: o compositor escreve o destino, as notas e a
    # curiosidade em volta da cena, na fonte do caderno.
    assert "TEXT-FREE CONTRACT" in prompt
    for copia in (
        "Descubra este destino",
        "Londres é uma cidade cheia de história.",
        "O Big Ben é o nome do sino que fica dentro da torre.",
    ):
        assert copia not in prompt
    # A arte e a pagina inteira, sem janela e sem faixa.
    assert "no framed area" in prompt and "no strip" in prompt
    assert "Do not add or infer any fact" in prompt
    assert "Do not depict any person" in prompt


def test_destination_intro_uses_generation_then_only_selected_page_for_revision(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#6f9fb8"))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    first = tmp_path / "destination-1.png"
    generator.generate_destination_intro_page(
        output_path=first,
        title="Paris",
        city="Paris",
        country="França",
        learning_points=["Paris é cheia de história.", "A cidade reúne arte e jardins."],
        curiosity="A Torre Eiffel foi inaugurada em 1889.",
        curiosity_label="Você sabia?",
        landmark_names=["Torre Eiffel"],
    )
    generator.generate_destination_intro_page(
        output_path=tmp_path / "destination-2.png",
        reference_page=first,
        revision_instruction="Use tons azuis e uma ilustração maior.",
        title="Paris",
        city="Paris",
        country="França",
        learning_points=["Paris é cheia de história.", "A cidade reúne arte e jardins."],
        curiosity="A Torre Eiffel foi inaugurada em 1889.",
        curiosity_label="Você sabia?",
        landmark_names=["Torre Eiffel"],
    )

    assert calls[0][1].endswith("/images/generations")
    assert "files" not in calls[0][2]
    assert calls[1][1].endswith("/images/edits")
    assert [file_data[0] for _field, file_data in calls[1][2]["files"]] == ["destination-1.png"]
    revision_prompt = calls[1][2]["data"]["prompt"]
    assert '"Use tons azuis e uma ilustração maior."' in revision_prompt
    assert "Remove every person that may appear in it" in revision_prompt


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


def test_summary_shows_the_route_and_never_the_family(tmp_path):
    """O sumário é do roteiro; a família ocupava metade da página repetindo a capa."""

    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#69b482"))

    output = tmp_path / "summary.png"
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    generator.generate_summary_page(
        output_path=output,
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
    )
    _method, url, kwargs = calls[0]
    # Sem referência nenhuma, a chamada é de geração, não de edição de imagem.
    assert url.endswith("/images/generations")
    prompt = kwargs["json"]["prompt"]
    assert "2. Coliseu" in prompt
    assert "PEOPLE-FREE CONTRACT" in prompt
    assert "Do not depict a person" in prompt
    # Nada de foto, capa aprovada ou contagem de gente.
    assert "original family photo" not in prompt
    assert "approved cover" not in prompt
    assert "family members together" not in prompt


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
    assert "TEXT-FREE CONTRACT" in prompt
    assert '"Família Moraes"' not in prompt
    assert "the required\nmember count" in prompt
    # A referencia da revisao e a pagina JA composta, com o brasao impresso por
    # cima. Sem avisar, o modelo redesenhava aquelas letras e o compositor
    # carimbava de novo: duas tipografias na mesma capa.
    assert "the lettering is not part of the artwork" in prompt


def test_summary_revision_uses_selected_page_and_visible_variation_default(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#cc825f"))

    reference = tmp_path / "summary-1.png"
    reference.write_bytes(_png_bytes())
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)

    generator.generate_summary_page(
        output_path=tmp_path / "summary-2.png",
        reference_page=reference,
        family_title="Família Moraes",
        trip_date="2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    # A única referência é a tentativa anterior desta mesma página.
    assert [file_data[0] for _field, file_data in kwargs["files"]] == ["summary-1.png"]
    assert "selected current-page attempt" in kwargs["data"]["prompt"]
    assert "Create a visibly different alternative" in kwargs["data"]["prompt"]
    assert "2. Coliseu" in kwargs["data"]["prompt"]


def test_landmark_page_defaults_to_generation_without_people_or_family_inputs(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#d09a55"))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    output = tmp_path / "landmark.png"
    generator.generate_landmark_page(
        family_photo=None,
        family_cover=None,
        output_path=output,
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
    # O texto saiu do prompt: quem escreve o nome, o lugar e os dois blocos e o
    # compositor, na fonte do caderno. Enquanto o modelo desenhava o titulo,
    # cada parada saia numa tipografia diferente da anterior.
    assert "TEXT-FREE CONTRACT" in prompt
    assert '"Uma torre de ferro que virou símbolo de Paris."' not in prompt
    assert "Conheça o lugar" not in prompt
    assert "checkbox" in prompt
    with Image.open(output) as image:
        page = image.convert("RGB")
        assert page.getpixel((390, 1447)) == (255, 255, 255)
        # Sem faixa nenhuma: a arte chega ate as quatro bordas da folha, e e a
        # mesma cor em cima, embaixo e no meio.
        arte = (208, 154, 85)
        assert page.getpixel((12, 12)) == arte
        assert page.getpixel((12, 1520)) == arte
        # Abaixo da zona de texto e acima do carimbo: arte pura.
        assert page.getpixel((512, 1150)) == arte


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
    assert "TEXT-FREE CONTRACT" in prompt
    assert '"Uma torre de ferro que virou símbolo de Paris."' not in prompt


def test_openai_page_generator_rejects_missing_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(PageGenerationConfigurationError):
        OpenAIGuidePageGenerator(api_key="")


def test_openai_page_generator_rejects_wrong_dimensions(tmp_path):
    def transport(_method, _url, **_kwargs):
        return _response(_png_bytes(size=(512, 512)))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    with pytest.raises(PageGenerationError, match="dimensões"):
        generator.generate_summary_page(
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
    with pytest.raises(PageGenerationError) as captured:
        generator.generate_summary_page(
            output_path=tmp_path / "bad.png",
            family_title="Família Moraes",
            trip_date="2026",
            landmark_names=["Torre Eiffel"],
        )

    assert "code=invalid_input_fidelity_model" in str(captured.value)
    assert "private family prompt" not in str(captured.value)


def test_landmark_prompt_stays_text_free_and_keeps_the_page_whole_during_revision():
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

    assert '"Use tons mais quentes."' in prompt
    assert "TEXT-FREE CONTRACT" in prompt
    # A arte e a pagina inteira, sem janela e sem faixa: a versao com janela
    # deitada abria dois cortes horizontais na folha.
    assert "no framed area" in prompt and "no strip" in prompt
    # E a grade do texto vem do compositor, nao de numero redigitado no prompt.
    alto = round(SCENE_TEXT_BOTTOM / 1536 * 100)
    assert f"ABOVE {alto} percent of the page height stays CALM" in prompt


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


@pytest.mark.parametrize(
    ("age_complexity", "expected_contract"),
    [
        ("preschool", "8 to 18 very large closed coloring regions"),
        ("early_reader", "15 to 30 large closed coloring regions"),
        ("older_child", "25 to 45 comfortably sized closed coloring regions"),
        ("family", "mixed-age family"),
    ],
)
def test_coloring_prompt_requires_child_usable_age_aware_lineart(age_complexity, expected_contract):
    prompt = activity_artwork_prompt(
        activity_type="coloring",
        landmark_name="Torre Eiffel",
        city="Paris",
        country="França",
        age_complexity=age_complexity,
        has_landmark_reference=False,
        has_revision_reference=False,
    )

    assert expected_contract in prompt
    assert "large closed shapes that a child can fill comfortably with crayons" in prompt
    assert "22 percent completely white" in prompt
    assert "Add at most two simple large context elements" in prompt
    assert "do not create a dense cityscape" in prompt
    assert "tiny windows, brick patterns, repeated micro-details" in prompt


def test_family_coloring_prompt_preserves_family_and_uses_original_trait_contract():
    prompt = family_coloring_artwork_prompt(
        landmark_name="Torre Eiffel",
        city="Paris",
        country="França",
        age_complexity="early_reader",
        expected_visible_family_member_count=4,
        has_family_cover=True,
        has_landmark_reference=True,
        has_landmark_page_reference=True,
        has_revision_reference=True,
        revision_instruction="Deixe os personagens ainda mais fofos e arredondados.",
    )

    assert "Input image 1 is the sanitized original family photo" in prompt
    assert "Input image 2 is the approved family cover" in prompt
    assert "Input image 3 is a sanitized landmark reference" in prompt
    assert "Input image 4 is the approved landmark guide page" in prompt
    assert "Input image 5 is the selected current activity attempt" in prompt
    assert "Depict exactly 4 family members together" in prompt
    assert "original cozy, cute and rounded children's coloring-book" in prompt
    assert "Do not imitate, name or reproduce any artist" in prompt
    assert "22 percent completely white" in prompt
    assert "do not render any letter" in prompt


def test_investigator_artwork_prompt_preserves_family_and_reserves_mission_grid():
    prompt = investigator_artwork_prompt(
        landmark_name="Museu do Louvre",
        city="Paris",
        country="França",
        age_complexity="preschool",
        child_count=2,
        expected_visible_family_member_count=4,
        has_family_cover=True,
        has_landmark_reference=True,
        has_landmark_page_reference=True,
        has_revision_reference=True,
        revision_instruction="Use uma paleta mais clara.",
    )

    assert "Input image 1 is the sanitized original family photo" in prompt
    assert "Input image 2 is the approved family cover" in prompt
    assert "Input image 3 is a sanitized landmark reference" in prompt
    assert "Input image 4 is the approved landmark page" in prompt
    assert "Input image 5 is the selected current Investigator attempt" in prompt
    assert "Show exactly 4 recognizable family members" in prompt
    assert "contains 2 registered children" in prompt
    assert "lower 50 percent pale" in prompt
    assert "do not render any letter" in prompt


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
        landmark_page_reference=approved,
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


def test_family_coloring_generation_uses_family_first_and_optional_references(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_lineart_png_bytes())

    family, cover = _family_references(tmp_path)
    landmark = tmp_path / "landmark-source.png"
    landmark.write_bytes(_png_bytes(size=(800, 600)))
    approved_landmark = tmp_path / "approved-landmark.png"
    approved_landmark.write_bytes(_png_bytes())
    selected = tmp_path / "selected-family-coloring.png"
    selected.write_bytes(_png_bytes())
    output = tmp_path / "family-coloring.png"
    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)

    generator.generate_family_coloring_page(
        family_photo=family,
        family_cover=cover,
        output_path=output,
        family_title="Família Silva",
        expected_visible_family_member_count=4,
        landmark_reference=landmark,
        landmark_page_reference=approved_landmark,
        landmark_context={
            "selection_id": "paris:eiffel",
            "name": "Torre Eiffel",
            "city": "Paris",
            "country": "França",
            "age_complexity": "early_reader",
        },
        activity_spec={"instruction": "Texto aplicado pelo compositor."},
        revision_instruction="Use linhas mais largas.",
        reference_page=selected,
    )

    _method, url, kwargs = calls[0]
    assert url.endswith("/images/edits")
    assert [file_data[0] for _field, file_data in kwargs["files"]] == [
        "family.png",
        "cover-approved.png",
        "landmark-source.png",
        "approved-landmark.png",
        "selected-family-coloring.png",
    ]
    assert "authoritative for membership" in kwargs["data"]["prompt"]
    assert "Do not imitate, name or reproduce any artist" in kwargs["data"]["prompt"]
    assert not (tmp_path / ".family-coloring.provider.png").exists()
    with Image.open(output) as image:
        assert image.size == (1024, 1536)
        colors = image.convert("RGB").getcolors(maxcolors=1024 * 1536)
        assert colors is not None
        assert {color for _count, color in colors} <= {(0, 0, 0), (255, 255, 255)}


def test_investigator_generation_creates_structured_missions_then_family_first_artwork(tmp_path):
    calls = []
    missions = [
        {
            "child_index": 1,
            "child_name": "Lia",
            "clue": "Procure uma forma triangular.",
            "mission": "Aponte para ela e desenhe a forma no ar.",
        },
        {
            "child_index": 2,
            "child_name": "Ravi",
            "clue": "Observe uma obra com muitas cores.",
            "mission": "Compare duas cores e anote a principal diferença.",
        },
    ]

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/responses"):
            return _mission_response(missions)
        return _response(_png_bytes())

    family, cover = _family_references(tmp_path)
    landmark = tmp_path / "louvre-source.png"
    landmark.write_bytes(_png_bytes(size=(800, 600)))
    approved_landmark = tmp_path / "approved-louvre.png"
    approved_landmark.write_bytes(_png_bytes())
    selected = tmp_path / "selected-investigator.png"
    selected.write_bytes(_png_bytes())
    output = tmp_path / "investigator.png"
    generator = OpenAIGuidePageGenerator(
        api_key="test-key",
        activity_model="test-activity-model",
        transport=transport,
    )

    generator.generate_investigator_page(
        family_photo=family,
        family_cover=cover,
        output_path=output,
        family_title="Família Lima",
        expected_visible_family_member_count=4,
        landmark_reference=landmark,
        landmark_page_reference=approved_landmark,
        landmark_context={
            "selection_id": "paris:louvre",
            "name": "Museu do Louvre",
            "city": "Paris",
            "country": "França",
            "description": "Museu instalado em um antigo palácio.",
            "curiosity": "A entrada conhecida tem formato de pirâmide.",
            "curiosity_kind": "trusted",
            "age_complexity": "preschool",
        },
        activity_spec={
            "children": [
                {"name": "Lia", "age": 4},
                {"name": "Ravi", "age": 11},
            ]
        },
        revision_instruction="Use uma paleta mais clara.",
        reference_page=selected,
    )

    assert calls[0][1].endswith("/responses")
    assert calls[0][2]["json"]["model"] == "test-activity-model"
    assert calls[0][2]["json"]["text"]["format"]["strict"] is True
    assert calls[1][1].endswith("/images/edits")
    assert [file_data[0] for _field, file_data in calls[1][2]["files"]] == [
        "family.png",
        "cover-approved.png",
        "louvre-source.png",
        "approved-louvre.png",
        "selected-investigator.png",
    ]
    assert not (tmp_path / ".investigator.provider.png").exists()
    with Image.open(output) as image:
        assert image.size == (1024, 1536)


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
            {"prompt": "Crie uma pintura do lugar do seu jeito."},
            "blank painting canvas",
        ),
    ],
)
def test_activity_generators_use_available_landmark_page_reference_and_exact_subtype(
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
        landmark_page_reference=approved,
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
        "landmark_page_reference": approved,
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


def test_homecoming_generation_preserves_family_reference_order_and_revision(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes(color="#e7c78e"))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    family_photo, family_cover = _family_references(tmp_path)
    first = tmp_path / "homecoming-1.png"
    generator.generate_homecoming_page(
        family_photo=family_photo,
        family_cover=family_cover,
        output_path=first,
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        age_complexity="early_reader",
        expected_visible_family_member_count=2,
    )
    generator.generate_homecoming_page(
        family_photo=family_photo,
        family_cover=family_cover,
        output_path=tmp_path / "homecoming-2.png",
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        age_complexity="early_reader",
        expected_visible_family_member_count=2,
        revision_instruction="Mostre uma janela maior do aeroporto.",
        reference_page=first,
    )

    assert calls[0][1].endswith("/images/edits")
    assert [file_data[0] for _field, file_data in calls[0][2]["files"]] == [
        "family.png",
        "cover-approved.png",
    ]
    assert [file_data[0] for _field, file_data in calls[1][2]["files"]] == [
        "family.png",
        "cover-approved.png",
        "homecoming-1.png",
    ]
    prompt = calls[1][2]["data"]["prompt"]
    assert "FAMILY CONTINUITY CONTRACT" in prompt
    assert "Input image 3 is the selected current-page attempt" in prompt
    assert "Keep the upper 26 percent and lower 25 percent pale" in prompt
    assert "TEXT-FREE CLOSING CONTRACT" in prompt
    assert "Do not infer or depict a home country" in prompt
    assert '"Mostre uma janela maior do aeroporto."' in prompt


def test_homecoming_prompt_requires_the_complete_existing_family_and_no_model_copy():
    prompt = homecoming_page_prompt(
        family_title="Família Moraes",
        trip_date="Julho de 2026",
        landmark_names=["Torre Eiffel", "Coliseu"],
        age_complexity="preschool",
        expected_visible_family_member_count=4,
    )

    assert "Show exactly 4 family members together" in prompt
    assert "original family photo" in prompt
    assert "approved cover" in prompt
    assert "same family" in prompt
    assert "Render no readable word, letter, number" in prompt
    assert "Uma coisa que quero contar" not in prompt


def test_activity_generation_without_visual_reference_uses_prompt_generation(tmp_path):
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_png_bytes())

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    output = generator.generate_drawing_page(
        output_path=tmp_path / "drawing.png",
        landmark_reference=None,
        landmark_page_reference=None,
        landmark_context={"name": "Torre Eiffel", "city": "Paris", "country": "França"},
        activity_spec={"prompt": "Desenhe."},
    )

    assert calls[0][1].endswith("/images/generations")
    assert "Torre Eiffel" in calls[0][2]["json"]["prompt"]
    assert output.exists()


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
            landmark_page_reference=approved,
            landmark_context={"name": "Torre Eiffel", "city": "Paris", "country": "França"},
            activity_spec={"prompt": "Desenhe."},
        )

    assert not output.exists()
    assert not (tmp_path / ".drawing.provider.png").exists()
    assert not (tmp_path / ".drawing.png.tmp").exists()


def _spot_scene_bytes(recolored: bool) -> bytes:
    """Cena deitada com seis objetos; na variante, quatro trocam de matiz."""

    buffer = BytesIO()
    image = Image.new("RGB", SPOT_SCENE_SIZE, "#f7f0de")
    draw = ImageDraw.Draw(image)
    palette = [
        ("#6c94c4", "#c46c6c"),
        ("#c48460", "#60c484"),
        ("#b0606c", "#6c60b0"),
        ("#789c6c", "#9c6c94"),
        ("#c6a85c", "#5ca8c6"),
        ("#6084a8", "#a88460"),
    ]
    for index, (x, y) in enumerate(
        [(180, 180), (520, 200), (1180, 210), (200, 780), (640, 800), (1240, 790)]
    ):
        base_color, changed = palette[index]
        fill = changed if recolored and index < 4 else base_color
        draw.ellipse((x - 90, y - 90, x + 90, y + 90), fill=fill)
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_the_spot_the_difference_scene_is_requested_in_landscape(tmp_path):
    """Em pé, o painel largo cortava 65% da arte e decapitava o monumento.

    A proporção da cena e a do painel são iguais hoje; se alguém devolver o
    pedido para retrato, o corte volta calado. Aqui ele não volta.
    """

    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return _response(_spot_scene_bytes(recolored=len(calls) > 1))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    output = tmp_path / "spot.png"

    assert (
        generator.generate_spot_the_difference_page(
            output_path=output,
            landmark_reference=None,
            landmark_page_reference=None,
            landmark_context={
                "name": "Torre Eiffel",
                "city": "Paris",
                "country": "França",
                "age_complexity": "early_reader",
            },
            activity_spec={},
        )
        == output
    )

    scene, variant = calls[0], calls[1]
    assert scene[1].endswith("/images/generations")
    assert scene[2]["json"]["size"] == "1536x1024"
    # A variante é uma edição da cena base e precisa do mesmo enquadramento.
    assert variant[1].endswith("/images/edits")
    assert variant[2]["data"]["size"] == "1536x1024"
    # A página entregue continua retrato: é o PDF inteiro que depende disso.
    with Image.open(output) as image:
        assert image.size == (1024, 1536)


def test_a_portrait_scene_from_the_provider_is_refused(tmp_path):
    """Aceitar retrato aqui reabriria o corte central pela porta dos fundos."""

    def transport(method, url, **kwargs):
        return _response(_png_bytes())

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)

    with pytest.raises(PageGenerationError):
        generator.generate_spot_the_difference_page(
            output_path=tmp_path / "spot.png",
            landmark_reference=None,
            landmark_page_reference=None,
            landmark_context={
                "name": "Torre Eiffel",
                "city": "Paris",
                "country": "França",
                "age_complexity": "early_reader",
            },
            activity_spec={},
        )


def test_the_route_prompt_and_the_printed_names_agree_on_which_half_is_empty(tmp_path):
    """O prompt reserva uma metade por parada; o nome tem que cair nela.

    Enquanto o modelo escrevia os nomes, o código não tinha como saber onde a
    vinheta caiu. Agora ele dita as faixas — e é a divergência entre o que se
    pede e o que se desenha que já cortou o monumento pelos pés na página do
    ponto turístico. Aqui os dois lados vêm de `summary_band`, e este teste é
    o que impede que um mude sem o outro.
    """

    paradas = ["Torre Eiffel", "Museu do Louvre", "Catedral de Notre-Dame"]
    prompt = summary_page_prompt(
        family_title="Família Moraes", trip_date="Setembro de 2026", landmark_names=paradas
    )

    arte = tmp_path / "roteiro-art.png"
    Image.new("RGB", (1024, 1536), "#dfe8dc").save(arte, "PNG")
    saida = tmp_path / "roteiro.png"
    compose_summary_page(
        arte,
        saida,
        family_title="Família Moraes",
        trip_date="Setembro de 2026",
        landmark_names=paradas,
    )

    metade = 1024 // 2
    with Image.open(saida) as imagem:
        pagina = imagem.convert("RGB")
        for indice, parada in enumerate(paradas):
            topo, base, vinheta_a_direita = summary_band(indice, len(paradas))
            # O prompt precisa declarar exatamente este lado para esta parada.
            lado_da_vinheta = "RIGHT" if vinheta_a_direita else "LEFT"
            assert f"{indice + 1}. {parada} — between" in prompt
            assert f"in the {lado_da_vinheta} half" in prompt

            # A rota cruza as duas metades por construção, então a medição
            # olha só para fora do corredor por onde ela passa.
            corredor = SUMMARY_ROUTE_INSET + 40
            fora_a_esquerda = (0, topo, metade - corredor, base)
            fora_a_direita = (metade + corredor, topo, 1024, base)
            do_nome = fora_a_esquerda if vinheta_a_direita else fora_a_direita
            da_vinheta = fora_a_direita if vinheta_a_direita else fora_a_esquerda

            assert _tem_tinta_escura(pagina, do_nome), f"o nome sumiu da faixa {indice + 1}"
            assert not _tem_tinta_escura(
                pagina, da_vinheta
            ), f"o nome invadiu a vinheta {indice + 1}"


def _tem_tinta_escura(pagina: Image.Image, caixa: tuple[int, int, int, int]) -> bool:
    """Procura tinta de texto, ignorando a rota pontilhada e o fundo."""

    recorte = pagina.crop(caixa)
    cores = recorte.getcolors(maxcolors=recorte.width * recorte.height) or []
    escuros = sum(
        quantidade
        for quantidade, (r, g, b) in cores
        if r < 120 and g < 140 and b < 140
    )
    # Longe do corredor da rota, tinta escura só pode ser texto.
    return escuros > 200


def _route_artwork(*, intrudes: bool) -> bytes:
    """Arte de roteiro chapada, com ou sem vinheta subindo até a cabeceira."""

    imagem = Image.new("RGB", (1024, 1536), "#FDF4DC")
    desenho = ImageDraw.Draw(imagem)
    for indice in range(2):
        topo, base, a_direita = summary_band(indice, 2)
        cx = 768 if a_direita else 256
        # Na versão que invade, a primeira vinheta sobe acima da linha do título.
        alto = topo + 40 - (340 if intrudes and indice == 0 else 0)
        desenho.polygon([(cx, alto), (cx - 130, base - 60), (cx + 130, base - 60)], fill="#2E5FA3")
    buffer = BytesIO()
    imagem.save(buffer, format="PNG")
    return buffer.getvalue()


def test_the_route_page_asks_for_new_art_instead_of_beheading_a_landmark(tmp_path):
    """Arte que sobe até a faixa do título vale outra tentativa, não um guia perdido.

    A guarda existe para não decapitar a parada em silêncio, mas na primeira
    versão ela derrubava o guia inteiro — e um guia sem a página do roteiro não
    vira PDF nenhum. Uma vinheta mal posicionada é problema transitório.
    """

    entregas = [
        _route_artwork(intrudes=True),
        _route_artwork(intrudes=False),
    ]
    chamadas = []

    def transport(_method, _url, **_kwargs):
        chamadas.append(1)
        return _response(entregas[min(len(chamadas) - 1, len(entregas) - 1)])

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    saida = generator.generate_summary_page(
        output_path=tmp_path / "roteiro.png",
        family_title="Família Moraes",
        trip_date="Setembro de 2026",
        landmark_names=["Torre Eiffel", "Museu do Louvre"],
    )

    assert saida.is_file()
    assert len(chamadas) == 2, "a arte que invadia devia ter sido descartada"


def test_the_route_page_still_ships_when_every_attempt_intrudes(tmp_path):
    """Na última tentativa a página sai assim mesmo: pior é não existir."""

    def transport(_method, _url, **_kwargs):
        return _response(_route_artwork(intrudes=True))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    saida = generator.generate_summary_page(
        output_path=tmp_path / "roteiro.png",
        family_title="Família Moraes",
        trip_date="Setembro de 2026",
        landmark_names=["Torre Eiffel", "Museu do Louvre"],
    )

    assert saida.is_file()
