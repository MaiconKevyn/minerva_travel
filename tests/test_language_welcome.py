"""A abertura de idioma: dados curados, composição e contrato do prompt."""

import pytest
from PIL import Image

from minerva_travel.activity_page_compositor import (
    ActivityPageCompositionError,
    compose_language_welcome_page,
)
from minerva_travel.app import _builder_page_plan
from minerva_travel.catalog import load_catalog
from minerva_travel.flight_vocabulary import (
    EVERYDAY_WORDS,
    GOODBYE_WORDS,
    GREETINGS,
    LANGUAGE_CURIOSITIES,
    language_welcome_for,
)
from minerva_travel.page_generation import (
    OpenAIGuidePageGenerator,
    PageGenerationError,
    language_welcome_artwork_prompt,
)
from tests.test_page_generation import _png_bytes, _response


def test_every_curated_language_has_the_full_welcome_kit():
    """Idioma sem kit completo geraria página com buraco — melhor nem existir.

    Os quatro dicionários precisam andar juntos: quem adicionar um idioma novo
    em EVERYDAY_WORDS descobre aqui que faltou a saudação, o tchau ou a
    curiosidade.
    """

    for language in EVERYDAY_WORDS:
        assert language in GREETINGS, language
        assert language in GOODBYE_WORDS, language
        assert language in LANGUAGE_CURIOSITIES, language
        tchau = GOODBYE_WORDS[language]
        assert tchau.word and tchau.pronunciation and tchau.meaning


def test_the_welcome_is_the_arc_of_a_conversation():
    welcome = language_welcome_for("França")
    assert welcome is not None
    assert welcome.greeting == "Bonjour !"
    assert welcome.language == "francês"
    meanings = [word.meaning for word in welcome.words]
    # olá → tudo bem? → por favor → obrigado → tchau, nessa ordem.
    assert len(welcome.words) == 5
    assert "Olá" in meanings[0]
    assert "Tudo bem" in meanings[1]
    assert "Tchau" in meanings[4] or "Até logo" in meanings[4]


def test_a_country_without_curated_language_gets_no_welcome():
    """Pronúncia inventada sai impressa errada: sem curadoria, sem página."""

    assert language_welcome_for("Brasil") is None
    assert language_welcome_for("Mongólia") is None


def _artwork(tmp_path, color="#DDE8EC"):
    path = tmp_path / "arte.png"
    Image.new("RGB", (1024, 1536), color).save(path, "PNG")
    return path


def test_the_composed_page_has_words_card_and_mission(tmp_path):
    welcome = language_welcome_for("Japão")
    saida = tmp_path / "ola.png"
    compose_language_welcome_page(
        _artwork(tmp_path),
        saida,
        language=welcome.language,
        greeting=welcome.greeting,
        words=[(w.word, w.pronunciation, w.meaning) for w in welcome.words],
        curiosity=welcome.curiosity,
    )

    with Image.open(saida) as imagem:
        pagina = imagem.convert("RGB")
        # O quadradinho da missão está branco e pronto para marcar. A posição
        # horizontal depende da largura do rótulo ("Eu disse Konnichiwa!"),
        # então procuramos a linha do pill em vez de um pixel fixo.
        linha = [pagina.getpixel((x, 1447)) for x in range(200, 824)]
        assert (255, 255, 255) in linha, "o quadradinho da missão sumiu"


def test_the_composer_refuses_an_incomplete_conversation(tmp_path):
    with pytest.raises(ActivityPageCompositionError, match="cinco"):
        compose_language_welcome_page(
            _artwork(tmp_path),
            tmp_path / "ola.png",
            language="francês",
            greeting="Bonjour !",
            words=[("Bonjour", "bon-JUR", "Olá")],
            curiosity="",
        )


def test_the_artwork_prompt_keeps_bubbles_empty_and_derives_the_grid():
    prompt = language_welcome_artwork_prompt(
        language="francês", country="França", landmark_name="Torre Eiffel"
    )
    assert "TEXT-FREE CONTRACT" in prompt
    # Balões vazios por contrato: o modelo escreveria a saudação com a
    # ortografia que inventasse.
    assert "COMPLETELY EMPTY" in prompt
    assert "Torre Eiffel" in prompt
    # A grade vem do compositor (59% hoje), nunca redigitada no prompt.
    assert "ABOVE 59 percent" in prompt
    assert "do not depict any person" in prompt


def test_the_generator_refuses_an_uncurated_country(tmp_path):
    generator = OpenAIGuidePageGenerator(
        api_key="test-key", transport=lambda *a, **k: _response(_png_bytes())
    )
    with pytest.raises(PageGenerationError, match="conferido"):
        generator.generate_language_welcome_page(
            output_path=tmp_path / "ola.png",
            country="Mongólia",
            landmark_name="Deserto de Gobi",
        )


def test_the_generator_composes_a_full_page(tmp_path):
    def transport(_method, _url, **_kwargs):
        return _response(_png_bytes(color="#dce8ee"))

    generator = OpenAIGuidePageGenerator(api_key="test-key", transport=transport)
    saida = generator.generate_language_welcome_page(
        output_path=tmp_path / "ola.png",
        country="Alemanha",
        landmark_name="Portão de Brandemburgo",
    )
    assert saida.is_file()


# ---------------------------------------------------------------------------
# O plano de montagem: onde "O primeiro olá" entra no livro.
# ---------------------------------------------------------------------------


def _plan(selected, **form_extra):
    catalog = load_catalog()
    pages, _ = _builder_page_plan(
        {
            "title": "Família Lima",
            "year": 2026,
            "children_ages": [8],
            "activity_selections": [],
            **form_extra,
        },
        catalog.destinations,
        selected,
    )
    return pages


def test_one_welcome_per_country_right_after_the_country_is_introduced():
    """Conheça Paris, aprenda a dizer Bonjour, Torre Eiffel — nessa ordem.

    Uma página por país, não por destino: Paris e o Louvre são a mesma França.
    E ela vem DEPOIS da abertura do destino, porque primeiro se apresenta o
    lugar, depois se aprende a falar com ele.
    """

    pages = _plan(["paris:eiffel-tower", "paris:louvre", "london:tower-bridge"])
    kinds = [page.kind for page in pages]

    welcome_positions = [i for i, kind in enumerate(kinds) if kind == "flight_vocabulary"]
    assert len(welcome_positions) == 2
    for index in welcome_positions:
        assert kinds[index - 1] == "destination_intro"
        assert kinds[index + 1] == "landmark"

    welcome_pages = [page for page in pages if page.kind == "flight_vocabulary"]
    assert [page.metadata["country"] for page in welcome_pages] == ["França", "Inglaterra"]
    # A âncora visual é o primeiro ponto confirmado do país.
    assert welcome_pages[0].metadata["landmark_name"] == "Torre Eiffel"
    assert welcome_pages[0].title == "O primeiro olá em francês"


def test_the_welcome_is_on_by_default_and_can_be_switched_off():
    """Cliente antigo que não conhece o campo não perde a página em silêncio."""

    assert any(page.kind == "flight_vocabulary" for page in _plan(["paris:eiffel-tower"]))
    assert not any(
        page.kind == "flight_vocabulary"
        for page in _plan(["paris:eiffel-tower"], flight_vocabulary_pages=False)
    )


def test_the_printed_contract_lists_the_whole_conversation():
    page = next(
        page for page in _plan(["paris:eiffel-tower"]) if page.kind == "flight_vocabulary"
    )
    welcome = language_welcome_for("França")

    assert welcome is not None
    assert "O primeiro olá" in page.required_copy
    assert welcome.greeting in page.required_copy
    assert welcome.curiosity in page.required_copy
    for word in welcome.words:
        assert word.word in page.required_copy
        assert word.meaning in page.required_copy


def test_a_country_without_curated_language_gets_no_welcome_in_the_plan():
    """Sem curadoria, o capítulo abre direto no ponto turístico — sem chute."""

    catalog = load_catalog()
    rio = [d for d in catalog.destinations if "rio" in d.id.lower()]
    if not rio:
        pytest.skip("catálogo sem destino de país sem curadoria")
    selecao = [f"{rio[0].id}:{rio[0].landmarks[0].id}"]
    assert not any(page.kind == "flight_vocabulary" for page in _plan(selecao))
