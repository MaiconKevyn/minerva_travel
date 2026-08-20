"""As primeiras palavras do idioma, para treinar no avião antes de chegar.

Diferente da "Sobrevivência no idioma", que é opcional e ensina cinco frases
prontas para uma parada: aqui são palavras soltas, uma página por país, e
metade delas fala do que a família vai visitar. Quem vai ver a Torre Eiffel
aprende ``la tour``; quem vai ao Templo Senso-ji aprende ``otera``. A palavra
reaparece na viagem inteira, e é isso que faz ela grudar.

Nome que não entrega a categoria — "Alhambra", "Machu Picchu" — cai nas
palavras gerais, que servem para falar de qualquer lugar.

A pronúncia é escrita como a criança brasileira leria em português, não em
alfabeto fonético. Um idioma sem curadoria simplesmente não gera página:
inventar pronúncia ensina errado, e errado sai impresso.
"""

import unicodedata
from dataclasses import dataclass

from minerva_travel.child_phrasebook import COUNTRY_LANGUAGES


@dataclass(frozen=True)
class FlightWord:
    word: str
    pronunciation: str
    meaning: str


# As quatro que a criança usa no primeiro dia, na ordem em que precisa delas.
EVERYDAY_WORDS: dict[str, tuple[FlightWord, ...]] = {
    "frances": (
        FlightWord("Bonjour", "bon-JUR", "Olá / bom dia"),
        FlightWord("Merci", "mer-SI", "Obrigado"),
        FlightWord("S'il vous plaît", "siu-vu-PLÊ", "Por favor"),
        FlightWord("Ça va ?", "sá-VÁ", "Tudo bem?"),
    ),
    "ingles": (
        FlightWord("Hello", "ré-LOU", "Olá"),
        FlightWord("Thank you", "TÊNK-iu", "Obrigado"),
        FlightWord("Please", "PLÍZ", "Por favor"),
        FlightWord("How are you?", "RAU ar iú", "Tudo bem?"),
    ),
    "espanhol": (
        FlightWord("Hola", "Ó-la", "Olá"),
        FlightWord("Gracias", "GRA-sias", "Obrigado"),
        FlightWord("Por favor", "por fa-VOR", "Por favor"),
        FlightWord("¿Qué tal?", "que TAL", "Tudo bem?"),
    ),
    "italiano": (
        FlightWord("Ciao", "TCHÁU", "Oi / tchau"),
        FlightWord("Grazie", "GRÁ-tsie", "Obrigado"),
        FlightWord("Per favore", "per fa-VÔ-re", "Por favor"),
        FlightWord("Come va?", "CÔ-me VA", "Tudo bem?"),
    ),
    "alemao": (
        FlightWord("Hallo", "RÁ-lo", "Olá"),
        FlightWord("Danke", "DÂN-que", "Obrigado"),
        FlightWord("Bitte", "BI-te", "Por favor"),
        FlightWord("Wie geht's?", "vi GUÊTS", "Tudo bem?"),
    ),
    "japones": (
        FlightWord("Konnichiwa", "co-ni-tchi-UÁ", "Olá"),
        FlightWord("Arigatou", "a-ri-GA-tô", "Obrigado"),
        FlightWord("Onegaishimasu", "o-ne-GÁI-shi-más", "Por favor"),
        FlightWord("Genki desu ka?", "GUEN-ki dés-ca", "Tudo bem?"),
    ),
}

LANGUAGE_NAMES: dict[str, str] = {
    "frances": "francês",
    "ingles": "inglês",
    "espanhol": "espanhol",
    "italiano": "italiano",
    "alemao": "alemão",
    "japones": "japonês",
}

def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(value).strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def language_for_country(country: str) -> str | None:
    return COUNTRY_LANGUAGES.get(_normalize(country))


def country_has_flight_vocabulary(country: str) -> bool:
    return language_for_country(country) in EVERYDAY_WORDS


def country_flight_vocabulary_languages() -> dict[str, str]:
    """País normalizado → nome do idioma, para o contrato público.

    O frontend precisa dizer de qual idioma serão as palavras antes de gerar
    nada. Sem publicar este mapa, ele manteria uma cópia à mão que envelhece
    em silêncio e promete um idioma que o guia não tem.
    """

    return {
        country: LANGUAGE_NAMES[language]
        for country, language in sorted(COUNTRY_LANGUAGES.items())
        if language in EVERYDAY_WORDS
    }


# ---------------------------------------------------------------------------
# "O primeiro olá" — a abertura de idioma de cada país.
#
# Diferente das palavras de voo (treino no avião, com vocabulário das paradas)
# e da "Sobrevivência no idioma" (cinco frases prontas, opcional por parada):
# esta é a página que abre o capítulo do país e ensina a criança a CONVERSAR —
# o arco inteiro de uma conversa com alguém de lá: olá, tudo bem?, por favor,
# obrigado, tchau. Como todo dado de idioma, é curado em código: pronúncia
# inventada sai impressa errada.
# ---------------------------------------------------------------------------

WELCOME_WORDS_PER_PAGE = 5

# A saudação que vira o TÍTULO da página, com a pontuação do próprio idioma.
# Não deriva de EVERYDAY_WORDS porque o título carrega pontuação ("¡Hola!")
# que a linha de treino não usa.
GREETINGS: dict[str, str] = {
    "frances": "Bonjour !",
    "ingles": "Hello!",
    "espanhol": "¡Hola!",
    "italiano": "Ciao!",
    "alemao": "Hallo!",
    "japones": "Konnichiwa!",
}

# O tchau fecha o arco da conversa; as outras quatro palavras vêm de
# EVERYDAY_WORDS, que já cobre olá, obrigado, por favor e tudo bem.
GOODBYE_WORDS: dict[str, FlightWord] = {
    "frances": FlightWord("Au revoir", "ô-rê-VUÁR", "Tchau / até logo"),
    "ingles": FlightWord("Bye!", "BÁI", "Tchau"),
    "espanhol": FlightWord("Adiós", "a-di-ÓS", "Tchau"),
    "italiano": FlightWord("Arrivederci", "a-ri-ve-DÉR-tchi", "Até logo"),
    "alemao": FlightWord("Tschüss", "TCHUS", "Tchau"),
    "japones": FlightWord("Sayounara", "sa-iô-NÁ-ra", "Tchau / até logo"),
}

# Uma curiosidade por idioma, no tom do cartão "Você sabia?". Fatos simples e
# conferíveis; nada de superlativo que envelhece.
LANGUAGE_CURIOSITIES: dict[str, str] = {
    "frances": (
        "Abajur, buquê e croissant são palavras que o português pegou emprestadas do francês."
    ),
    "ingles": (
        "Futebol e sanduíche vieram do inglês: football e sandwich, ditas do nosso jeito."
    ),
    "espanhol": (
        "Espanhol e português são línguas irmãs: as duas nasceram do latim, por isso se "
        "parecem tanto."
    ),
    "italiano": (
        "As palavras da música são italianas no mundo inteiro: piano quer dizer 'baixinho'."
    ),
    "alemao": "O alemão adora juntar palavras: luva se diz Handschuh — 'sapato de mão'.",
    "japones": "Karaokê é uma palavra japonesa: kara ('vazia') + okê (pedaço de 'orquestra').",
}


@dataclass(frozen=True)
class LanguageWelcome:
    language: str
    country: str
    greeting: str
    words: tuple[FlightWord, ...]
    curiosity: str


def language_welcome_for(country: str) -> LanguageWelcome | None:
    """A abertura de idioma do país, ou None quando o idioma não foi curado."""

    language = language_for_country(country)
    if not language:
        return None
    everyday = EVERYDAY_WORDS[language]
    # A ordem é o arco de uma conversa: olá, tudo bem?, por favor, obrigado, tchau.
    words = (everyday[0], everyday[3], everyday[2], everyday[1], GOODBYE_WORDS[language])
    return LanguageWelcome(
        language=LANGUAGE_NAMES[language],
        country=str(country).strip(),
        greeting=GREETINGS[language],
        words=words,
        curiosity=LANGUAGE_CURIOSITIES[language],
    )
