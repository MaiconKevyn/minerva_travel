"""Frases de sobrevivência que uma criança brasileira consegue falar sozinha.

A pronúncia é escrita como a criança leria em português — não em alfabeto
fonético, que ela não sabe ler. As cinco frases cobrem o que ela realmente
quer fazer sozinha: pedir algo, agradecer, achar o banheiro, perguntar o
preço e se apresentar.

Sem idioma curado para o país, a atividade não é oferecida: inventar
pronúncia de um idioma que não conferimos ensinaria errado.
"""

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ChildPhrase:
    phrase: str
    pronunciation: str
    meaning: str


@dataclass(frozen=True)
class ChildPhrasebook:
    language: str
    phrases: tuple[ChildPhrase, ...]


PHRASES_PER_PAGE = 5

PHRASEBOOKS: dict[str, ChildPhrasebook] = {
    "frances": ChildPhrasebook(
        language="francês",
        phrases=(
            ChildPhrase("Bonjour !", "bon-JUR", "Bom dia / olá"),
            ChildPhrase("Merci beaucoup", "mer-SI bo-CU", "Muito obrigado"),
            ChildPhrase(
                "Une glace, s'il vous plaît", "IUN glás, siu-vu-PLÊ", "Um sorvete, por favor"
            ),
            ChildPhrase("Où sont les toilettes ?", "u son lê tua-LÉT", "Onde fica o banheiro?"),
            ChildPhrase("Je m'appelle...", "jê ma-PÉL", "Meu nome é..."),
        ),
    ),
    "ingles": ChildPhrasebook(
        language="inglês",
        phrases=(
            ChildPhrase("Hello!", "ré-LOU", "Olá"),
            ChildPhrase("Thank you", "TÊNK iu", "Obrigado"),
            ChildPhrase("One ice cream, please", "uan ais-crim, plíz", "Um sorvete, por favor"),
            ChildPhrase("Where is the toilet?", "uér iz dê TÓI-let", "Onde fica o banheiro?"),
            ChildPhrase("My name is...", "mai NEIM iz", "Meu nome é..."),
        ),
    ),
    "espanhol": ChildPhrasebook(
        language="espanhol",
        phrases=(
            ChildPhrase("¡Hola!", "Ó-la", "Olá"),
            ChildPhrase("Muchas gracias", "MU-chas GRA-sias", "Muito obrigado"),
            ChildPhrase("Un helado, por favor", "un e-LA-do, por fa-VOR", "Um sorvete, por favor"),
            ChildPhrase("¿Dónde está el baño?", "DON-de es-TÁ el BA-nho", "Onde fica o banheiro?"),
            ChildPhrase("Me llamo...", "me IÁ-mo", "Meu nome é..."),
        ),
    ),
    "italiano": ChildPhrasebook(
        language="italiano",
        phrases=(
            ChildPhrase("Ciao!", "TCHÁU", "Oi / tchau"),
            ChildPhrase("Grazie mille", "GRÁ-tsie MI-le", "Muito obrigado"),
            ChildPhrase(
                "Un gelato, per favore", "un je-LÁ-to, per fa-VÔ-re", "Um sorvete, por favor"
            ),
            ChildPhrase("Dov'è il bagno?", "do-VÉ il BÁ-nho", "Onde fica o banheiro?"),
            ChildPhrase("Mi chiamo...", "mi QUIÁ-mo", "Meu nome é..."),
        ),
    ),
    "alemao": ChildPhrasebook(
        language="alemão",
        phrases=(
            ChildPhrase("Hallo!", "RÁ-lo", "Olá"),
            ChildPhrase("Danke schön", "DÂN-que chên", "Muito obrigado"),
            ChildPhrase("Ein Eis, bitte", "áin áis, BI-te", "Um sorvete, por favor"),
            ChildPhrase("Wo ist die Toilette?", "vô ist di toa-LÉ-te", "Onde fica o banheiro?"),
            ChildPhrase("Ich heiße...", "ir RÁI-se", "Meu nome é..."),
        ),
    ),
    "japones": ChildPhrasebook(
        language="japonês",
        phrases=(
            ChildPhrase("Konnichiwa", "co-ni-tchi-UÁ", "Olá"),
            ChildPhrase("Arigatou", "a-ri-GA-tô", "Obrigado"),
            ChildPhrase(
                "Aisu kurimu kudasai", "ái-su cu-RÍ-mu cu-da-SÁI", "Um sorvete, por favor"
            ),
            ChildPhrase(
                "Toire wa doko desu ka?", "TÔI-re ua DÔ-co dés-ca", "Onde fica o banheiro?"
            ),
            ChildPhrase("Watashi wa ... desu", "ua-TÁ-shi ua ... dés", "Meu nome é..."),
        ),
    ),
}

# País → idioma curado. Um país fora desta lista simplesmente não oferece a
# atividade, em vez de cair num idioma aproximado.
COUNTRY_LANGUAGES: dict[str, str] = {
    "franca": "frances",
    "france": "frances",
    "belgica": "frances",
    "reino unido": "ingles",
    "inglaterra": "ingles",
    "united kingdom": "ingles",
    "escocia": "ingles",
    "irlanda": "ingles",
    "estados unidos": "ingles",
    "united states": "ingles",
    "canada": "ingles",
    "australia": "ingles",
    "nova zelandia": "ingles",
    "espanha": "espanhol",
    "spain": "espanhol",
    "argentina": "espanhol",
    "chile": "espanhol",
    "uruguai": "espanhol",
    "mexico": "espanhol",
    "peru": "espanhol",
    "colombia": "espanhol",
    "italia": "italiano",
    "italy": "italiano",
    "alemanha": "alemao",
    "germany": "alemao",
    "austria": "alemao",
    "suica": "alemao",
    "japao": "japones",
    "japan": "japones",
}


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(value).strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def phrasebook_for_country(country: str) -> ChildPhrasebook | None:
    """Return the curated phrasebook, or None when we have not checked that language."""

    language = COUNTRY_LANGUAGES.get(_normalize(country))
    return PHRASEBOOKS.get(language) if language else None


def country_has_phrasebook(country: str) -> bool:
    return phrasebook_for_country(country) is not None
