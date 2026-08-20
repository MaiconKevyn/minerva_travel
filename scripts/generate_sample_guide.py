"""Regenera as páginas de amostra do guia demonstrativo pelo pipeline de produção.

As amostras aparecem em três lugares — o folheável da página inicial, os cards
de exemplo e `docs/amostras-identidade/` — e envelhecem juntas a cada mudança de
identidade ou de tipografia. Rodar isto à mão em scripts descartáveis fazia as
três cópias divergirem, então o roteiro mora aqui.

A família é inventada de ponta a ponta: nenhuma foto de pessoa real entra neste
fluxo. O retrato de referência é gerado, serve de âncora de identidade para a
capa e é descartado — é o mesmo papel que a foto da família cumpre em produção.

    python scripts/generate_sample_guide.py --tudo
    python scripts/generate_sample_guide.py --capa

Precisa de OPENAI_API_KEY no .env e de crédito na conta.
"""

from __future__ import annotations

import argparse
import base64
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from minerva_travel.config import load_project_env, openai_api_key  # noqa: E402
from minerva_travel.page_generation import (  # noqa: E402
    OpenAIGuidePageGenerator,
    PageGenerationError,
)
from minerva_travel.visual_identity import ILLUSTRATION_STYLE  # noqa: E402

FAMILIA = "Família Knopp"
DATA = "Setembro de 2026"
CIDADE, PAIS = "Paris", "França"
PARADAS = ["Torre Eiffel", "Museu do Louvre"]
PESSOAS_VISIVEIS = 4

# A família de demonstração é fictícia e descrita por escrito, nunca fotografada.
# O retrato existe só para ancorar quem aparece na capa: quantas pessoas, que
# idades, que tons de pele. Sem ele o modelo inventa uma família diferente a
# cada geração, e a capa deixa de parecer o guia de alguém.
RETRATO_DA_FAMILIA = f"""
A warm group portrait of one invented family of four, standing together, facing the viewer,
full body, on a plain pale background with no scenery and no props.
{ILLUSTRATION_STYLE}

The four people, left to right:
- a Black woman in her mid thirties, warm deep brown skin, short natural curly hair
- a white man in his mid thirties, light skin, short brown hair, a short trimmed beard
- a girl of about five, mixed heritage, medium brown skin, curly hair tied in two puffs
- a boy of about four, mixed heritage, medium brown skin, short curly hair

Everyday casual clothes in the house palette. Relaxed, friendly expressions. Keep all four
whole and clearly separate, standing side by side, none overlapping another's face.

These are invented people. Do not reproduce the likeness of any real or public person.
Do not render any letter, word, number or signature anywhere.
""".strip()

BRIEF_DA_CAPA = (
    "A família toda junta na parte de baixo da capa, de pé, com a Torre Eiffel e o Louvre "
    "compondo o cenário acima deles."
)

NOTAS_DE_PARIS = [
    "Paris cresceu nas duas margens do rio Sena, atravessado por dezenas de pontes.",
    "A cidade guarda museus, jardins e mercados de rua espalhados por bairros bem diferentes.",
]
CURIOSIDADE_DE_PARIS = "Muitas ruas ainda têm o calçamento de pedra colocado há mais de cem anos."

PONTOS = {
    "torre": {
        "landmark_name": "Torre Eiffel",
        "description": (
            "Uma torre de ferro com 300 metros, construída para uma grande feira e hoje o "
            "símbolo da cidade."
        ),
        "curiosity": (
            "Em dias quentes o ferro se estica e a torre chega a ficar alguns centímetros "
            "mais alta."
        ),
    },
    "louvre": {
        "landmark_name": "Museu do Louvre",
        "description": (
            "Um antigo palácio de reis que virou museu e hoje guarda obras de milhares de anos."
        ),
        "curiosity": (
            "A pirâmide de vidro da entrada é feita de centenas de losangos e triângulos "
            "encaixados."
        ),
    },
}


@dataclass(frozen=True)
class Destino:
    """Onde cada página gerada precisa pousar."""

    folheavel: str | None = None  # public/sample-guide/
    exemplo: str | None = None  # public/activity-examples/
    amostra: str | None = None  # docs/amostras-identidade/


DESTINOS = {
    "capa": Destino("page-01.webp", "cover-sample.webp", "01-capa.webp"),
    "roteiro": Destino("page-02.webp", "route-sample.webp", "02-nosso-roteiro.webp"),
    "destino": Destino("page-03.webp", None, "03-destino-paris.webp"),
    "torre": Destino("page-04.webp", None, "04-torre-eiffel.webp"),
    "louvre": Destino("page-11.webp", None, None),
}

PASTA_FOLHEAVEL = REPO / "frontend_atual/apps/web/public/sample-guide"
PASTA_EXEMPLOS = REPO / "frontend_atual/apps/web/public/activity-examples"
PASTA_AMOSTRAS = REPO / "docs/amostras-identidade"

# As amostras do site são servidas em conexões de celular; 82 mantém o grão do
# giz sem triplicar o peso da página inicial.
QUALIDADE_WEBP = 82


def _gerador() -> OpenAIGuidePageGenerator:
    load_project_env()
    chave = openai_api_key()
    if not chave:
        raise SystemExit("Falta OPENAI_API_KEY no .env.")
    return OpenAIGuidePageGenerator(api_key=chave)


def _retrato(gerador: OpenAIGuidePageGenerator, destino: Path) -> Path:
    """Gera o retrato da família inventada que ancora a capa."""

    # O retrato nao e uma pagina do guia, entao nao passa pelo _persist_page_image
    # (que exige o formato da pagina). Reusar o transporte do gerador traz o
    # retry e o timeout ja configurados, que e o que importa aqui.
    resposta = gerador._generate_from_prompt(RETRATO_DA_FAMILIA)  # noqa: SLF001
    destino.write_bytes(base64.b64decode(resposta.json()["data"][0]["b64_json"]))
    with Image.open(destino) as imagem:
        imagem.verify()
    return destino


def gerar_capa(gerador: OpenAIGuidePageGenerator, trabalho: Path) -> Path:
    retrato = _retrato(gerador, trabalho / "retrato-familia.png")
    saida = trabalho / "capa.png"
    gerador.generate_cover_page(
        family_photo=retrato,
        output_path=saida,
        family_title=FAMILIA,
        trip_date=DATA,
        landmark_names=PARADAS,
        expected_visible_family_member_count=PESSOAS_VISIVEIS,
        cover_brief=BRIEF_DA_CAPA,
    )
    return saida


def gerar_roteiro(gerador: OpenAIGuidePageGenerator, trabalho: Path) -> Path:
    saida = trabalho / "roteiro.png"
    gerador.generate_summary_page(
        output_path=saida,
        family_title=FAMILIA,
        trip_date=DATA,
        landmark_names=PARADAS,
    )
    return saida


def gerar_destino(gerador: OpenAIGuidePageGenerator, trabalho: Path) -> Path:
    saida = trabalho / "destino.png"
    gerador.generate_destination_intro_page(
        output_path=saida,
        title=CIDADE,
        city=CIDADE,
        country=PAIS,
        learning_points=NOTAS_DE_PARIS,
        curiosity=CURIOSIDADE_DE_PARIS,
        curiosity_label="Você sabia?",
        landmark_names=PARADAS,
    )
    return saida


def _gerar_ponto(gerador: OpenAIGuidePageGenerator, trabalho: Path, chave: str) -> Path:
    ponto = PONTOS[chave]
    saida = trabalho / f"{chave}.png"
    gerador.generate_landmark_page(
        family_photo=None,
        family_cover=None,
        output_path=saida,
        family_title=FAMILIA,
        trip_date=DATA,
        city=CIDADE,
        country=PAIS,
        curiosity_label="Você sabia?",
        **ponto,
    )
    return saida


PASSOS = {
    "capa": gerar_capa,
    "roteiro": gerar_roteiro,
    "destino": gerar_destino,
    "torre": lambda g, t: _gerar_ponto(g, t, "torre"),
    "louvre": lambda g, t: _gerar_ponto(g, t, "louvre"),
}


def publicar(pagina: Path, destino: Destino) -> list[Path]:
    escritos = []
    with Image.open(pagina) as imagem:
        rgb = imagem.convert("RGB")
        for pasta, nome in (
            (PASTA_FOLHEAVEL, destino.folheavel),
            (PASTA_EXEMPLOS, destino.exemplo),
            (PASTA_AMOSTRAS, destino.amostra),
        ):
            if not nome:
                continue
            alvo = pasta / nome
            rgb.save(alvo, "WEBP", quality=QUALIDADE_WEBP, method=6)
            escritos.append(alvo)
    return escritos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paginas",
        nargs="+",
        choices=sorted(PASSOS),
        help="quais páginas regenerar (padrão: todas as afetadas pela identidade)",
    )
    parser.add_argument("--tudo", action="store_true", help="regenera todas as páginas")
    parser.add_argument("--capa", action="store_true", help="atalho para --paginas capa")
    parser.add_argument(
        "--rascunho",
        type=Path,
        default=Path("build/amostras"),
        help="onde guardar os PNGs intermediários",
    )
    parser.add_argument(
        "--sem-publicar",
        action="store_true",
        help="gera e para, sem escrever nos diretórios do site",
    )
    argumentos = parser.parse_args()

    escolhidas = list(PASSOS) if argumentos.tudo else (argumentos.paginas or [])
    if argumentos.capa:
        escolhidas = ["capa"]
    if not escolhidas:
        parser.error("escolha --tudo, --capa ou --paginas")

    trabalho = argumentos.rascunho.resolve()
    trabalho.mkdir(parents=True, exist_ok=True)
    gerador = _gerador()

    for chave in escolhidas:
        inicio = time.time()
        print(f"» {chave}…", flush=True)
        try:
            pagina = PASSOS[chave](gerador, trabalho)
        except PageGenerationError as erro:
            print(f"  falhou: {erro}", file=sys.stderr)
            return 1
        print(f"  gerada em {time.time() - inicio:.0f}s: {pagina}")
        if argumentos.sem_publicar:
            continue
        for alvo in publicar(pagina, DESTINOS[chave]):
            print(f"  publicada: {alvo.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
