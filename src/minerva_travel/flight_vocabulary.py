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

WORDS_PER_PAGE = 8
EVERYDAY_WORDS_PER_PAGE = 4


@dataclass(frozen=True)
class FlightWord:
    word: str
    pronunciation: str
    meaning: str


@dataclass(frozen=True)
class FlightVocabulary:
    language: str
    country: str
    words: tuple[FlightWord, ...]


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

# Substantivo do tipo de lugar que a família vai visitar. A categoria sai do
# nome do ponto turístico; sem categoria reconhecida, entram as palavras
# gerais mais abaixo.
PLACE_WORDS: dict[str, dict[str, FlightWord]] = {
    "frances": {
        "torre": FlightWord("La tour", "la TUR", "A torre"),
        "museu": FlightWord("Le musée", "lê mu-ZÊ", "O museu"),
        "ponte": FlightWord("Le pont", "lê PON", "A ponte"),
        "castelo": FlightWord("Le château", "lê cha-TÔ", "O castelo"),
        "igreja": FlightWord("L'église", "le-GLIZ", "A igreja"),
        "palacio": FlightWord("Le palais", "lê pa-LÊ", "O palácio"),
        "parque": FlightWord("Le jardin", "lê jar-DAN", "O jardim"),
        "templo": FlightWord("Le temple", "lê TAN-ple", "O templo"),
        "montanha": FlightWord("La montagne", "la mon-TÁ-nhe", "A montanha"),
        "estatua": FlightWord("La statue", "la sta-TU", "A estátua"),
        "mercado": FlightWord("Le marché", "lê mar-CHÊ", "O mercado"),
    },
    "ingles": {
        "torre": FlightWord("The tower", "dê TÁ-uer", "A torre"),
        "museu": FlightWord("The museum", "dê miu-ZÍ-am", "O museu"),
        "ponte": FlightWord("The bridge", "dê BRIDJ", "A ponte"),
        "castelo": FlightWord("The castle", "dê CÁ-sol", "O castelo"),
        "igreja": FlightWord("The church", "dê TCHÊRTCH", "A igreja"),
        "palacio": FlightWord("The palace", "dê PÁ-lis", "O palácio"),
        "parque": FlightWord("The park", "dê PARK", "O parque"),
        "templo": FlightWord("The temple", "dê TÉM-pol", "O templo"),
        "montanha": FlightWord("The mountain", "dê MÁUN-tin", "A montanha"),
        "estatua": FlightWord("The statue", "dê STÁ-tchu", "A estátua"),
        "mercado": FlightWord("The market", "dê MAR-quet", "O mercado"),
    },
    "espanhol": {
        "torre": FlightWord("La torre", "la TÔ-rre", "A torre"),
        "museu": FlightWord("El museo", "el mu-SÊ-o", "O museu"),
        "ponte": FlightWord("El puente", "el PUÊN-te", "A ponte"),
        "castelo": FlightWord("El castillo", "el cas-TI-io", "O castelo"),
        "igreja": FlightWord("La iglesia", "la i-GLÊ-sia", "A igreja"),
        "palacio": FlightWord("El palacio", "el pa-LÁ-sio", "O palácio"),
        "parque": FlightWord("El parque", "el PAR-que", "O parque"),
        "templo": FlightWord("El templo", "el TEM-plo", "O templo"),
        "montanha": FlightWord("La montaña", "la mon-TÁ-nha", "A montanha"),
        "estatua": FlightWord("La estatua", "la es-TÁ-tua", "A estátua"),
        "mercado": FlightWord("El mercado", "el mer-CÁ-do", "O mercado"),
    },
    "italiano": {
        "torre": FlightWord("La torre", "la TÔR-re", "A torre"),
        "museu": FlightWord("Il museo", "il mu-ZÊ-o", "O museu"),
        "ponte": FlightWord("Il ponte", "il PON-te", "A ponte"),
        "castelo": FlightWord("Il castello", "il cas-TÉL-lo", "O castelo"),
        "igreja": FlightWord("La chiesa", "la QUIÉ-za", "A igreja"),
        "palacio": FlightWord("Il palazzo", "il pa-LÁT-tso", "O palácio"),
        "parque": FlightWord("Il giardino", "il jar-DÍ-no", "O jardim"),
        "templo": FlightWord("Il tempio", "il TÉM-pio", "O templo"),
        "montanha": FlightWord("La montagna", "la mon-TÁ-nha", "A montanha"),
        "estatua": FlightWord("La statua", "la STÁ-tua", "A estátua"),
        "mercado": FlightWord("Il mercato", "il mer-CÁ-to", "O mercado"),
    },
    "alemao": {
        "torre": FlightWord("Der Turm", "der TURM", "A torre"),
        "museu": FlightWord("Das Museum", "das mu-ZÊ-um", "O museu"),
        "ponte": FlightWord("Die Brücke", "di BRÜ-que", "A ponte"),
        "castelo": FlightWord("Das Schloss", "das CHLÓS", "O castelo"),
        "igreja": FlightWord("Die Kirche", "di QUIR-rre", "A igreja"),
        "palacio": FlightWord("Der Palast", "der pa-LÁST", "O palácio"),
        "parque": FlightWord("Der Park", "der PARK", "O parque"),
        "templo": FlightWord("Der Tempel", "der TÉM-pel", "O templo"),
        "montanha": FlightWord("Der Berg", "der BÉRK", "A montanha"),
        "estatua": FlightWord("Die Statue", "di CHTÁ-tu-e", "A estátua"),
        "mercado": FlightWord("Der Markt", "der MARKT", "O mercado"),
    },
    "japones": {
        "torre": FlightWord("Tawaa", "TA-uá", "A torre"),
        "museu": FlightWord("Hakubutsukan", "ra-cu-BUT-su-can", "O museu"),
        "ponte": FlightWord("Hashi", "RA-shi", "A ponte"),
        "castelo": FlightWord("Shiro", "SHI-ro", "O castelo"),
        "igreja": FlightWord("Kyoukai", "kió-CÁI", "A igreja"),
        "palacio": FlightWord("Kyuuden", "KIÚ-den", "O palácio"),
        "parque": FlightWord("Kouen", "CÔ-en", "O parque"),
        "templo": FlightWord("Otera", "o-TÉ-ra", "O templo"),
        "montanha": FlightWord("Yama", "IÁ-ma", "A montanha"),
        "estatua": FlightWord("Zou", "ZÔ", "A estátua"),
        "mercado": FlightWord("Ichiba", "i-TCHI-ba", "O mercado"),
    },
}

# Servem para falar de qualquer lugar, quando o nome do ponto turístico não
# entrega a categoria — "Machu Picchu" e "Alhambra" não dizem o que são.
GENERAL_PLACE_WORDS: dict[str, tuple[FlightWord, ...]] = {
    "frances": (
        FlightWord("Regarde !", "re-GARD", "Olha!"),
        FlightWord("C'est beau", "sé BÔ", "É bonito"),
        FlightWord("Très grand", "trê GRAN", "Muito grande"),
        FlightWord("Une photo", "iun fo-TÔ", "Uma foto"),
    ),
    "ingles": (
        FlightWord("Look!", "LUK", "Olha!"),
        FlightWord("It's beautiful", "its BIU-ti-ful", "É bonito"),
        FlightWord("Very big", "VÉ-ri BIG", "Muito grande"),
        FlightWord("A photo", "a FÔ-tou", "Uma foto"),
    ),
    "espanhol": (
        FlightWord("¡Mira!", "MI-ra", "Olha!"),
        FlightWord("Es bonito", "es bo-NI-to", "É bonito"),
        FlightWord("Muy grande", "mui GRAN-de", "Muito grande"),
        FlightWord("Una foto", "u-na FÔ-to", "Uma foto"),
    ),
    "italiano": (
        FlightWord("Guarda!", "GUÁR-da", "Olha!"),
        FlightWord("È bello", "é BÉL-lo", "É bonito"),
        FlightWord("Molto grande", "MOL-to GRAN-de", "Muito grande"),
        FlightWord("Una foto", "u-na FÔ-to", "Uma foto"),
    ),
    "alemao": (
        FlightWord("Schau!", "CHÁU", "Olha!"),
        FlightWord("Sehr schön", "zer CHÊN", "Muito bonito"),
        FlightWord("Sehr groß", "zer GRÔS", "Muito grande"),
        FlightWord("Ein Foto", "áin FÔ-to", "Uma foto"),
    ),
    "japones": (
        FlightWord("Mite!", "MI-te", "Olha!"),
        FlightWord("Kirei", "qui-RÊI", "É bonito"),
        FlightWord("Ookii", "Ô-kii", "Muito grande"),
        FlightWord("Shashin", "SHA-shin", "Uma foto"),
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

# Palavra no nome do ponto turístico → categoria. Cobre português, inglês e a
# forma local, porque o nome chega como a família escreveu.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "torre": ("torre", "tower", "turm", "tour eiffel", "big ben", "campanile", "pisa"),
    "museu": ("museu", "museum", "louvre", "prado", "uffizi", "hermitage", "musee", "musée"),
    "ponte": ("ponte", "bridge", "brucke", "brücke", "pont"),
    "castelo": ("castelo", "castle", "schloss", "chateau", "château", "neuschwanstein", "windsor"),
    "igreja": (
        "igreja",
        "church",
        "catedral",
        "cathedral",
        "basilica",
        "basílica",
        "sagrada familia",
        "sagrada família",
        "duomo",
        "notre dame",
        "sacre coeur",
        "sacré-cœur",
    ),
    "palacio": ("palacio", "palácio", "palace", "palast", "alhambra", "versalhes", "versailles"),
    "parque": ("parque", "park", "jardim", "garden", "jardin", "central park", "retiro"),
    "templo": ("templo", "temple", "tempel", "senso-ji", "sensoji", "pagoda", "pagode"),
    "montanha": ("monte", "montanha", "mountain", "berg", "fuji", "pico", "machu picchu", "alpes"),
    "estatua": ("estatua", "estátua", "statue", "cristo redentor", "sereia", "david"),
    "mercado": ("mercado", "market", "markt", "bazar", "boqueria"),
}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(value).strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def landmark_category(landmark_name: str) -> str | None:
    """A categoria de lugar que o nome do ponto turístico revela, se revelar."""

    haystack = _normalize(landmark_name)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(_normalize(keyword) in haystack for keyword in keywords):
            return category
    return None


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


def flight_vocabulary_for(
    country: str,
    landmark_names: list[str],
) -> FlightVocabulary | None:
    """Metade palavras do dia a dia, metade sobre o que a família vai ver.

    Devolve ``None`` quando não temos o idioma conferido — é melhor não ter a
    página do que imprimir uma pronúncia inventada.
    """

    language = language_for_country(country)
    if language is None or language not in EVERYDAY_WORDS:
        return None

    words: list[FlightWord] = list(EVERYDAY_WORDS[language][:EVERYDAY_WORDS_PER_PAGE])
    place_words = PLACE_WORDS[language]

    # A ordem das paradas manda: a primeira coisa que a família vê é a
    # primeira palavra que ela aprende.
    seen_categories: list[str] = []
    for name in landmark_names:
        category = landmark_category(name)
        if category and category not in seen_categories and category in place_words:
            seen_categories.append(category)

    for category in seen_categories:
        if len(words) >= WORDS_PER_PAGE:
            break
        words.append(place_words[category])

    for filler in GENERAL_PLACE_WORDS[language]:
        if len(words) >= WORDS_PER_PAGE:
            break
        words.append(filler)

    return FlightVocabulary(
        language=LANGUAGE_NAMES[language],
        country=str(country).strip(),
        words=tuple(words[:WORDS_PER_PAGE]),
    )
