import unicodedata
from dataclasses import dataclass

from minerva_travel.models import Destination, LanguageTip


@dataclass(frozen=True)
class DestinationLanguage:
    name: str
    tips: tuple[LanguageTip, ...]


CURATED_LANGUAGE_TIPS = {
    "italia": DestinationLanguage(
        name="italiano",
        tips=(
            LanguageTip(
                phrase="Ciao",
                pronunciation="tchau",
                meaning="Oi / tchau",
                use_case="Use para cumprimentar alguem de forma simples.",
            ),
            LanguageTip(
                phrase="Grazie",
                pronunciation="GRAT-tsie",
                meaning="Obrigado/obrigada",
                use_case="Use para agradecer em lojas, restaurantes ou passeios.",
            ),
        ),
    ),
    "italy": DestinationLanguage(
        name="italiano",
        tips=(
            LanguageTip(
                phrase="Ciao",
                pronunciation="tchau",
                meaning="Oi / tchau",
                use_case="Use para cumprimentar alguem de forma simples.",
            ),
            LanguageTip(
                phrase="Grazie",
                pronunciation="GRAT-tsie",
                meaning="Obrigado/obrigada",
                use_case="Use para agradecer em lojas, restaurantes ou passeios.",
            ),
        ),
    ),
    "espanha": DestinationLanguage(
        name="espanhol",
        tips=(
            LanguageTip(
                phrase="Hola",
                pronunciation="O-la",
                meaning="Oi",
                use_case="Use para cumprimentar alguem.",
            ),
            LanguageTip(
                phrase="Gracias",
                pronunciation="GRA-sias",
                meaning="Obrigado/obrigada",
                use_case="Use para agradecer durante o passeio.",
            ),
        ),
    ),
    "spain": DestinationLanguage(
        name="espanhol",
        tips=(
            LanguageTip(
                phrase="Hola",
                pronunciation="O-la",
                meaning="Oi",
                use_case="Use para cumprimentar alguem.",
            ),
            LanguageTip(
                phrase="Gracias",
                pronunciation="GRA-sias",
                meaning="Obrigado/obrigada",
                use_case="Use para agradecer durante o passeio.",
            ),
        ),
    ),
}

FAMILY_LANGUAGE_COUNTRIES = {"brasil", "brazil"}


def lookup_destination_language(destination: Destination) -> DestinationLanguage | None:
    if _normalize_text(destination.country) in FAMILY_LANGUAGE_COUNTRIES:
        return None
    if destination.language_name and destination.language_tips:
        return DestinationLanguage(
            name=destination.language_name,
            tips=tuple(destination.language_tips),
        )
    for key in [_normalize_text(destination.country), _normalize_text(destination.city)]:
        if key in CURATED_LANGUAGE_TIPS:
            return CURATED_LANGUAGE_TIPS[key]
    return None


def preferred_language_tip(language: DestinationLanguage) -> LanguageTip:
    preferred_by_language = {
        "ingles": "Thank you",
        "portugues de portugal": "Obrigado/obrigada",
    }
    preferred_phrase = preferred_by_language.get(_normalize_text(language.name))
    if preferred_phrase:
        for tip in language.tips:
            if tip.phrase == preferred_phrase:
                return tip
    return language.tips[0]


def _normalize_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value or "")
    ascii_value = "".join(
        character for character in ascii_value if not unicodedata.combining(character)
    )
    return " ".join(ascii_value.strip().casefold().split())
