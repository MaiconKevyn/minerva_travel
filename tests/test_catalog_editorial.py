import json
import re
from pathlib import Path

CATALOG_PATH = Path("data/destinations/europe_2026.json")
FORBIDDEN_PLAIN_PORTUGUESE = {
    "Franca",
    "aviao",
    "cafe",
    "cerimonia",
    "criancas",
    "educacao",
    "familia",
    "historia",
    "ingles",
    "memoria",
    "onibus",
    "opcao",
    "palacio",
    "piramide",
    "portugues",
    "relogio",
    "simbolo",
    "tambem",
    "voce",
    "voces",
}


def test_catalog_user_facing_copy_does_not_regress_to_known_unaccented_forms():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    copy = json.dumps(catalog, ensure_ascii=False)

    present = sorted(
        token
        for token in FORBIDDEN_PLAIN_PORTUGUESE
        if re.search(rf"(?<![\wÀ-ÿ]){re.escape(token)}(?![\wÀ-ÿ])", copy, flags=re.IGNORECASE)
    )

    assert present == []
