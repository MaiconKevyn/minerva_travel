from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from minerva_travel.activity_page_compositor import (
    ACCENT,
    BEST_MEMORY_REQUIRED_COPY,
    COLORING_ART_REGION,
    COLORING_INSTRUCTION_TEMPLATE,
    COLORING_MIN_WHITE_FRACTION,
    COLORING_TITLE,
    COVER_LOCKUP_BOTTOM,
    COVER_LOCKUP_TOP,
    DETAIL_HUNT_TITLE,
    DRAWING_BLANK_REGION,
    FAMILY_COLORING_INSTRUCTION_TEMPLATE,
    FAMILY_COLORING_TITLE,
    HOMECOMING_REQUIRED_COPY,
    HOMECOMING_WRITING_BLANK_REGIONS,
    INK,
    INVESTIGATOR_INSTRUCTION,
    INVESTIGATOR_TITLE,
    LANDMARK_VISITED_CHECKBOX,
    LANDMARK_VISITED_LABEL,
    MEMORY_BLANK_REGION,
    PAINTING_TITLE,
    PAPER,
    SCENE_ARTWORK_SIZE,
    SPOT_PANEL_GAP,
    SPOT_PANEL_LEFT,
    SPOT_PANEL_SIZE,
    SPOT_PANEL_TOP,
    SPOT_SCENE_SIZE,
    WORD_SEARCH_TITLE,
    ActivityPageCompositionError,
    coloring_instruction_for,
    compose_best_memory_page,
    compose_coloring_page,
    compose_cover_page,
    compose_detail_hunt_page,
    compose_drawing_page,
    compose_family_coloring_page,
    compose_homecoming_page,
    compose_investigator_page,
    compose_landmark_page,
    compose_spot_the_difference_page,
    compose_summary_page,
    compose_word_search_page,
    crop_scene_for_panel,
    family_coloring_instruction_for,
    summary_band,
    validate_activity_page,
)
from minerva_travel.investigator_activity import (
    InvestigatorMission,
    normalize_investigator_children,
)
from minerva_travel.spot_the_difference import MAX_DIFFERENCES, DifferenceRegion
from minerva_travel.word_search import build_word_search_grid

# Do token, nao de um literal: trocar a identidade nao pode exigir reescrever
# coordenada de pixel em teste.
PAPEL_RGB = tuple(int(PAPER[i : i + 2], 16) for i in (1, 3, 5))
TINTA_RGB = tuple(int(INK[i : i + 2], 16) for i in (1, 3, 5))
ACENTO_RGB = tuple(int(ACCENT[i : i + 2], 16) for i in (1, 3, 5))


def _scene(path: Path, color: str = "#d9eaf2") -> Path:
    """A cena deitada que as páginas ilustradas recebem do provedor."""

    image = Image.new("RGB", SCENE_ARTWORK_SIZE, color)
    draw = ImageDraw.Draw(image)
    draw.ellipse((560, 180, 980, 800), fill="#7ca6bd", outline="#31566c", width=16)
    image.save(path, "PNG")
    return path


def _artwork(path: Path, color: str = "#d9eaf2") -> Path:
    image = Image.new("RGB", (1024, 1536), color)
    draw = ImageDraw.Draw(image)
    draw.ellipse((330, 290, 694, 780), fill="#7ca6bd", outline="#31566c", width=16)
    image.save(path, "PNG")
    return path


def _lineart(path: Path) -> Path:
    image = Image.new("RGB", (1024, 1536), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((250, 310, 774, 1260), outline="black", width=12)
    draw.polygon([(260, 310), (512, 115), (764, 310)], outline="black", fill="white")
    for x in range(320, 741, 105):
        draw.rectangle((x, 480, x + 55, 570), outline="black", width=8)
    image.save(path, "PNG")
    return path


def _white_fraction(path: Path, region: tuple[int, int, int, int]) -> float:
    with Image.open(path) as image:
        crop = image.convert("RGB").crop(region)
    colors = crop.getcolors(maxcolors=crop.width * crop.height)
    assert colors is not None
    white = next((count for count, color in colors if color == (255, 255, 255)), 0)
    return white / (crop.width * crop.height)


def test_compositor_exact_copy_contract_matches_builder_required_copy():
    assert (
        COLORING_TITLE,
        FAMILY_COLORING_TITLE,
        INVESTIGATOR_TITLE,
        DETAIL_HUNT_TITLE,
        WORD_SEARCH_TITLE,
        PAINTING_TITLE,
    ) == (
        "Atividade para colorir",
        "Família de férias para colorir",
        "Investigador",
        "Caça aos detalhes",
        "Caça-palavras",
        "Minha pintura",
    )
    assert BEST_MEMORY_REQUIRED_COPY == (
        "Minha melhor memória",
        "Meu lugar favorito foi...",
        "O que eu mais gostei foi...",
        "Eu descobri que...",
        "Desenhe sua melhor lembrança",
        "Assinatura",
        "Data",
    )
    assert LANDMARK_VISITED_LABEL == "Já visitei"
    assert HOMECOMING_REQUIRED_COPY == (
        "Hora de voltar para casa",
        "Nossa grande aventura está chegando ao fim.",
        "Depois de conhecer lugares incríveis, chegou a hora de voltar para casa.",
        "Mas todas essas lembranças vão continuar com a gente.",
        "Uma coisa que quero contar quando chegar em casa:",
    )
    assert COLORING_INSTRUCTION_TEMPLATE == (
        "Agora é a vez de colorir {landmark_name} do seu jeito."
    )
    assert FAMILY_COLORING_INSTRUCTION_TEMPLATE == (
        "Agora é a vez de colorir a aventura da sua família em {landmark_name}."
    )
    assert INVESTIGATOR_INSTRUCTION == (
        "Cada criança tem uma missão secreta. Observem com atenção e trabalhem em equipe!"
    )


def test_coloring_instruction_is_exact_point_specific_copy():
    assert coloring_instruction_for("  Torre   Eiffel ") == (
        "Agora é a vez de colorir Torre Eiffel do seu jeito."
    )


def test_family_coloring_instruction_is_exact_point_specific_copy():
    assert family_coloring_instruction_for("  Torre   Eiffel ") == (
        "Agora é a vez de colorir a aventura da sua família em Torre Eiffel."
    )


def test_landmark_compositor_adds_one_empty_printable_visited_checkbox(tmp_path):
    output = tmp_path / "landmark.png"
    compose_landmark_page(
        _scene(tmp_path / "art.png"),
        output,
        landmark_name="Torre Eiffel",
        location="Paris, França",
        family_title="Família Moraes",
        trip_date="Setembro de 2026",
        description="Uma torre de ferro que virou o símbolo da cidade.",
        curiosity="Em dias quentes o ferro se estica e a torre fica mais alta.",
    )

    validate_activity_page(output)
    left, top, right, bottom = LANDMARK_VISITED_CHECKBOX
    with Image.open(output) as image:
        rgb = image.convert("RGB")
        assert rgb.getpixel(((left + right) // 2, (top + bottom) // 2)) == (255, 255, 255)
        assert rgb.getpixel((left, (top + bottom) // 2)) == TINTA_RGB
        label_crop = rgb.crop((438, 1418, 650, 1480))
        colors = label_crop.getcolors(maxcolors=label_crop.width * label_crop.height)
        assert colors is not None
        assert any(color == TINTA_RGB for _count, color in colors)


def test_coloring_compositor_outputs_binary_printable_page(tmp_path):
    output = tmp_path / "coloring.png"
    compose_coloring_page(
        _lineart(tmp_path / "art.png"),
        output,
        landmark_name="Torre Eiffel",
    )

    validate_activity_page(output, monochrome=True)
    with Image.open(output) as image:
        assert image.size == (1024, 1536)
        assert image.format == "PNG"
        colors = image.convert("RGB").getcolors(maxcolors=1024 * 1536)
        assert colors is not None
        assert {color for _count, color in colors} <= {(0, 0, 0), (255, 255, 255)}
        white = next((count for count, color in colors if color == (255, 255, 255)), 0)
        assert white / (1024 * 1536) >= COLORING_MIN_WHITE_FRACTION
        # Provider artwork is fitted below the code-owned heading and instruction.
        art_ink = (
            image.convert("L")
            .crop(COLORING_ART_REGION)
            .point(lambda value: 255 if value < 128 else 0)
        )
        assert art_ink.getbbox() is not None


def test_family_coloring_compositor_outputs_binary_page_with_exact_copy(tmp_path):
    output = tmp_path / "family-coloring.png"
    compose_family_coloring_page(
        _lineart(tmp_path / "family-art.png"),
        output,
        family_title="Família Silva",
        landmark_name="Torre Eiffel",
    )

    validate_activity_page(output, monochrome=True)
    with Image.open(output) as image:
        assert image.size == (1024, 1536)
        colors = image.convert("RGB").getcolors(maxcolors=1024 * 1536)
        assert colors is not None
        assert {color for _count, color in colors} <= {(0, 0, 0), (255, 255, 255)}
        white = next((count for count, color in colors if color == (255, 255, 255)), 0)
        assert white / (1024 * 1536) >= COLORING_MIN_WHITE_FRACTION


@pytest.mark.parametrize("child_count", [1, 2, 10])
def test_investigator_compositor_supports_all_mission_grid_sizes(tmp_path, child_count):
    output = tmp_path / f"investigator-{child_count}.png"
    children = normalize_investigator_children(
        [f"Criança {index}" for index in range(1, child_count + 1)],
        [4 + index for index in range(child_count)],
    )
    missions = [
        InvestigatorMission(
            child_index=index,
            child_name=child.name,
            clue=f"Procure o detalhe número {index}.",
            mission="Observe com atenção e conte o que descobriu ao adulto.",
        )
        for index, child in enumerate(children, start=1)
    ]
    compose_investigator_page(
        _artwork(tmp_path / f"investigator-art-{child_count}.png"),
        output,
        family_title="Família Lima",
        landmark_name="Museu do Louvre",
        children=children,
        missions=missions,
    )

    validate_activity_page(output)
    with Image.open(output) as image:
        assert image.size == (1024, 1536)


def test_coloring_compositor_rejects_unusable_solid_artwork_atomically(tmp_path):
    output = tmp_path / "coloring.png"
    output.write_bytes(b"previous-attempt")

    with pytest.raises(ActivityPageCompositionError, match="traços infantis"):
        compose_coloring_page(
            _artwork(tmp_path / "solid.png", color="black"),
            output,
            landmark_name="Torre Eiffel",
        )

    assert output.read_bytes() == b"previous-attempt"
    assert not (tmp_path / ".coloring.png.tmp").exists()


def test_detail_hunt_composites_bounded_exact_checklist(tmp_path):
    output = tmp_path / "detail.png"
    compose_detail_hunt_page(
        _artwork(tmp_path / "art.png"),
        output,
        landmark_name="Torre Eiffel",
        instruction="Observe a ilustração e marque suas descobertas.",
        clues=[
            "Encontre o contorno principal.",
            "Ache uma forma que se repete.",
            "Observe um detalhe perto do topo.",
        ],
    )

    validate_activity_page(output)
    with Image.open(output) as image:
        # Interior of the first deterministic checkbox is white.
        assert image.convert("RGB").getpixel((107, 951)) == (255, 255, 255)


def test_detail_hunt_rejects_unvalidated_clues(tmp_path):
    with pytest.raises(ActivityPageCompositionError, match="Quantidade"):
        compose_detail_hunt_page(
            _artwork(tmp_path / "art.png"),
            tmp_path / "detail.png",
            landmark_name="Torre Eiffel",
            instruction="Observe.",
            clues=["Somente uma pista"],
        )


def test_word_search_composites_only_a_solvable_seeded_grid(tmp_path):
    grid, words = build_word_search_grid(
        ["TORRE", "EIFFEL", "PARIS", "VIAGEM"], seed="paris:eiffel"
    )
    output = tmp_path / "words.png"
    compose_word_search_page(
        _artwork(tmp_path / "art.png"),
        output,
        landmark_name="Torre Eiffel",
        instruction="Encontre as palavras na horizontal ou vertical.",
        grid=grid,
        words=words,
    )

    validate_activity_page(output)
    with Image.open(output) as image:
        # The code-owned grid panel is opaque and independent from model artwork.
        assert image.convert("RGB").getpixel((170, 258)) == PAPEL_RGB


def test_word_search_rejects_a_word_missing_from_the_grid(tmp_path):
    grid, words = build_word_search_grid(["TORRE", "PARIS"], seed="stable")
    with pytest.raises(ActivityPageCompositionError, match="sem solução"):
        compose_word_search_page(
            _artwork(tmp_path / "art.png"),
            tmp_path / "words.png",
            landmark_name="Torre Eiffel",
            instruction="Encontre.",
            grid=grid,
            words=[*words, "LONDRES"],
        )


def test_drawing_and_memory_preserve_measurable_blank_response_areas(tmp_path):
    artwork = _artwork(tmp_path / "art.png", color="#427a8f")
    drawing = tmp_path / "drawing.png"
    memory = tmp_path / "memory.png"

    compose_drawing_page(
        artwork,
        drawing,
        landmark_name="Torre Eiffel",
        prompt="Agora é a sua vez de criar uma pintura da Torre Eiffel do seu jeito.",
    )
    compose_best_memory_page(
        artwork,
        memory,
        family_title="Família Moraes",
        trip_date="Julho de 2026",
    )

    assert _white_fraction(drawing, DRAWING_BLANK_REGION) == 1
    assert _white_fraction(memory, MEMORY_BLANK_REGION) == 1
    with Image.open(drawing) as drawing_image:
        assert drawing_image.convert("RGB").getpixel((80, 1320)) == PAPEL_RGB
    with Image.open(memory) as memory_image:
        assert memory_image.convert("RGB").getpixel((65, 1265)) == PAPEL_RGB
    validate_activity_page(drawing, blank_regions=[DRAWING_BLANK_REGION])
    validate_activity_page(memory, blank_regions=[MEMORY_BLANK_REGION])


def test_homecoming_compositor_adds_exact_closing_copy_and_blank_writing_lines(tmp_path):
    output = tmp_path / "homecoming.png"
    compose_homecoming_page(_artwork(tmp_path / "homecoming-art.png"), output)

    validate_activity_page(output, blank_regions=HOMECOMING_WRITING_BLANK_REGIONS)
    with Image.open(output) as image:
        rgb = image.convert("RGB")
        assert rgb.size == (1024, 1536)
        assert rgb.getpixel((80, 1200)) == PAPEL_RGB
        assert rgb.getpixel((200, 1340)) == TINTA_RGB
        for left, top, right, bottom in HOMECOMING_WRITING_BLANK_REGIONS:
            assert rgb.getpixel(((left + right) // 2, (top + bottom) // 2)) == PAPEL_RGB


def test_compositor_rejects_wrong_size_provider_artwork(tmp_path):
    source = tmp_path / "small.png"
    Image.new("RGB", (512, 512), "white").save(source, "PNG")

    with pytest.raises(ActivityPageCompositionError, match="1024x1536"):
        compose_drawing_page(
            source,
            tmp_path / "drawing.png",
            landmark_name="Torre Eiffel",
            prompt="Desenhe.",
        )


def _spot_scene(path: Path, *, tint: tuple[int, int, int]) -> Path:
    """Cena larga com marcas coladas na borda de cima e na de baixo."""

    image = Image.new("RGB", SPOT_SCENE_SIZE, "#f7f0de")
    draw = ImageDraw.Draw(image)
    width, height = SPOT_SCENE_SIZE
    draw.rectangle((0, 0, width, 24), fill="#1f3a5f")
    draw.rectangle((0, height - 24, width, height), fill="#1f3a5f")
    draw.ellipse((300, 400, 700, 700), fill=tint)
    image.save(path, "PNG")
    return path


def test_the_spot_scene_reaches_the_page_with_its_top_and_bottom_intact(tmp_path):
    """A arte em pé era cortada ao meio: o monumento saía sem pico e sem base."""

    base = _spot_scene(tmp_path / "base.png", tint=(90, 150, 110))
    variant = _spot_scene(tmp_path / "variant.png", tint=(200, 90, 110))
    base_panel = crop_scene_for_panel(base, tmp_path / "base-panel.png")
    variant_panel = crop_scene_for_panel(variant, tmp_path / "variant-panel.png")

    output = compose_spot_the_difference_page(
        base_panel,
        variant_panel,
        tmp_path / "spot.png",
        landmark_name="Torre Eiffel",
        instruction="Compare os dois desenhos e ache as diferenças.",
        regions=[DifferenceRegion(300, 400, 700, 700)],
    )

    with Image.open(output) as page:
        pixels = page.convert("RGB").load()
    left = SPOT_PANEL_LEFT + SPOT_PANEL_SIZE[0] // 2
    for index in range(2):
        top = SPOT_PANEL_TOP + index * (SPOT_PANEL_SIZE[1] + SPOT_PANEL_GAP)
        bottom = top + SPOT_PANEL_SIZE[1] - 1
        # A faixa escura da borda da cena tem de aparecer nas duas pontas.
        assert sum(pixels[left, top + 2]) < 300, f"o topo da cena {index + 1} foi cortado"
        assert sum(pixels[left, bottom - 2]) < 300, f"a base da cena {index + 1} foi cortada"


def test_the_spot_checklist_stays_inside_its_panel_at_the_maximum_count(tmp_path):
    """Com sete ou mais, a fila de baixo era desenhada fora do painel."""

    base = _spot_scene(tmp_path / "base.png", tint=(90, 150, 110))
    variant = _spot_scene(tmp_path / "variant.png", tint=(200, 90, 110))
    output = compose_spot_the_difference_page(
        crop_scene_for_panel(base, tmp_path / "base-panel.png"),
        crop_scene_for_panel(variant, tmp_path / "variant-panel.png"),
        tmp_path / "spot.png",
        landmark_name="Torre Eiffel",
        instruction="Compare os dois desenhos e ache as diferenças.",
        regions=[
            DifferenceRegion(index * 100, 400, index * 100 + 80, 480)
            for index in range(MAX_DIFFERENCES)
        ],
    )

    with Image.open(output) as page:
        pixels = page.convert("RGB").load()
    width, height = page.size
    for y in range(1502, height):
        for x in range(width):
            assert sum(pixels[x, y]) > 600, f"há tinta desenhada abaixo do painel, em y={y}"


def test_the_generated_scene_and_the_printed_panel_share_one_aspect():
    """Enquanto forem iguais, `crop_scene_for_panel` não descarta nada.

    Foi a divergência entre as duas — arte 2:3 e painel 1,88:1 — que cortava
    65% da altura e decapitava o monumento. Mexer numa sem mexer na outra
    traz o defeito de volta sem que nenhuma outra asserção perceba.
    """

    scene_width, scene_height = SPOT_SCENE_SIZE
    panel_width, panel_height = SPOT_PANEL_SIZE

    assert scene_width / scene_height == panel_width / panel_height


# Nomes e datas que existem de verdade, e que antes derrubavam a página ou
# apagavam a data sem erro nenhum. A checagem é de tinta na folha, porque o
# defeito era justamente o silêncio: a data sumia e nada reclamava.
NOME_LONGO_DE_FAMILIA = "Família Wanderley Mendonça de Albuquerque Filho"
DATA_LONGA = "Última semana de setembro e primeira de outubro de 2026"
PONTO_DE_NOME_LONGO = "Santuário Nacional de Nossa Senhora da Conceição Aparecida"


def _tem_tinta(page: Image.Image, box: tuple[int, int, int, int]) -> bool:
    recorte = page.crop(box)
    cores = recorte.getcolors(maxcolors=recorte.width * recorte.height) or []
    return any(cor == TINTA_RGB for _quantidade, cor in cores)


def test_cover_survives_a_long_family_name_and_a_long_trip_date(tmp_path):
    """Nome comprido quebrava a capa; data comprida sumia dela.

    `_bounded` aceita 60 caracteres, mas o título só cabia em uma linha até
    ~44 e o arco desistia em silêncio quando abria demais. Uma família de nome
    longo ficava sem capa nenhuma, para sempre.
    """

    saida = tmp_path / "capa.png"
    compose_cover_page(
        _artwork(tmp_path / "art.png"),
        saida,
        family_title=NOME_LONGO_DE_FAMILIA,
        trip_date=DATA_LONGA,
    )

    with Image.open(saida) as imagem:
        pagina = imagem.convert("RGB")
        # As caixas vêm da geometria do compositor: número redigitado aqui é
        # número que descola do que o código desenha.
        assert _tem_tinta(pagina, (72, COVER_LOCKUP_TOP + 30, 952, COVER_LOCKUP_BOTTOM - 20))
        # E a data continua na folha, em vez de desaparecer sem aviso.
        assert _tem_tinta(pagina, (72, COVER_LOCKUP_BOTTOM - 20, 952, COVER_LOCKUP_BOTTOM + 60))


def test_a_long_landmark_name_wraps_without_touching_the_arched_place(tmp_path):
    """O nome em duas linhas não pode descer sobre a linha em arco.

    Com o teto antigo a segunda linha parava a 13 px do arco e encostava nele.
    """

    saida = tmp_path / "ponto.png"
    compose_landmark_page(
        _scene(tmp_path / "art.png"),
        saida,
        landmark_name=PONTO_DE_NOME_LONGO,
        location="Aparecida, Brasil",
        family_title="Família Moraes",
        trip_date="Setembro de 2026",
        description="A maior igreja dedicada a Nossa Senhora no mundo.",
        curiosity="A imagem foi encontrada por três pescadores dentro do rio.",
    )

    with Image.open(saida) as imagem:
        pagina = imagem.convert("RGB")
        titulo = [y for y in range(90, 340) if _tem_tinta(pagina, (0, y, 1024, y + 1))]
        assert titulo, "o título não foi impresso"
        arco = [
            y
            for y in range(90, 340)
            if any(
                pagina.getpixel((x, y)) == ACENTO_RGB for x in range(0, 1024, 2)
            )
        ]
        assert arco, "a linha em arco não foi impressa"
        assert arco[0] - titulo[-1] >= 24, "o título encostou no arco"


def _arte_de_roteiro(path: Path, *, invade: bool) -> Path:
    """Arte de roteiro chapada, com ou sem monumento entrando na cabeceira."""

    imagem = Image.new("RGB", (1024, 1536), "#FEF3D4")
    desenho = ImageDraw.Draw(imagem)
    for indice in range(2):
        topo, base, a_direita = summary_band(indice, 2)
        cx = 768 if a_direita else 256
        alto = 140 if not invade else 340
        desenho.polygon(
            [(cx, topo + 40 - alto), (cx - 130, base - 60), (cx + 130, base - 60)],
            fill="#2E5FA3",
        )
    imagem.save(path, "PNG")
    return path


def test_the_route_page_refuses_to_behead_a_landmark(tmp_path):
    """Pintar a cabeceira por cima de um monumento é o pior desfecho: silencioso.

    A folga entre o que o prompt reserva e o que o código pinta é a defesa
    principal; esta guarda é a rede embaixo dela. Sem ela, uma torre que subiu
    demais sai sem a ponta e nada avisa.
    """

    with pytest.raises(ActivityPageCompositionError, match="decapitaria"):
        compose_summary_page(
            _arte_de_roteiro(tmp_path / "invade.png", invade=True),
            tmp_path / "saida.png",
            family_title="Família Moraes",
            trip_date="Setembro de 2026",
            landmark_names=["Torre Eiffel", "Museu do Louvre"],
        )


def test_the_route_page_takes_its_background_colour_from_the_artwork(tmp_path):
    """A página inteira fica de uma cor só, tirada do próprio desenho.

    Pintar a cabeceira com uma cor da paleta abria um corte visível no meio da
    folha, como se fossem duas páginas coladas.
    """

    saida = tmp_path / "roteiro.png"
    compose_summary_page(
        _arte_de_roteiro(tmp_path / "arte.png", invade=False),
        saida,
        family_title="Família Moraes",
        trip_date="Setembro de 2026",
        landmark_names=["Torre Eiffel", "Museu do Louvre"],
    )

    with Image.open(saida) as imagem:
        pagina = imagem.convert("RGB")
        # Um pixel dentro da cabeceira e outro bem abaixo dela, os dois no fundo.
        assert pagina.getpixel((20, 20)) == pagina.getpixel((20, 1500))
