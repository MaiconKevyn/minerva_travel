import time
import unicodedata
from pathlib import Path
from string import punctuation
from urllib.parse import quote

import httpx

from minerva_travel.models import Catalog, Destination, Landmark
from minerva_travel.wikimedia_assets import WikimediaAsset

COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
ALLOWED_LICENSE_PREFIXES = ("cc0", "public domain", "cc by", "cc-by")
USER_AGENT = "MinervaTravelMVP/0.1"
QUERY_OVERRIDES = {
    "paris:eiffel-tower": "Eiffel Tower Paris",
    "paris:arc-de-triomphe": "Arc de Triomphe Paris",
    "paris:champs-elysees": "Champs-Elysees Paris avenue",
    "paris:louvre": "Louvre Museum Paris",
    "paris:orsay": "Musee d'Orsay Paris",
    "paris:sacre-coeur": "Basilique du Sacre-Coeur de Montmartre Paris",
    "paris:luxembourg": "Luxembourg Garden Paris",
    "paris:versailles": "Palace of Versailles",
    "paris:seine": "Seine river Paris",
    "paris:palais-garnier": "Palais Garnier Paris",
    "london:big-ben": "Big Ben London",
    "london:london-eye": "London Eye ferris wheel",
    "london:buckingham-palace": "Buckingham Palace London",
    "london:westminster-abbey": "Westminster Abbey London",
    "london:tower-bridge": "Tower Bridge London",
    "london:red-phone-booth": "red telephone box London",
    "london:red-bus": "London red bus",
    "cambridge:cambridge-university": "King's College Cambridge",
    "cambridge:river-cam": "punting River Cam Cambridge",
    "lisbon:oceanario": "Oceanario de Lisboa",
    "lisbon:yellow-tram": "Tram 28 Lisbon",
    "lisbon:jeronimos": "Jeronimos Monastery Lisbon",
    "lisbon:descobrimentos": "Padrao dos Descobrimentos Lisbon",
    "lisbon:santo-antonio": "Igreja de Santo Antonio Lisboa",
    "lisbon:pastel-de-belem": "Pasteis de Belem Lisbon",
    "lisbon:praca-comercio": "Praca do Comercio Lisbon",
}


def fetch_wikimedia_assets(
    catalog: Catalog,
    output_dir: Path = Path("runtime/wikimedia"),
    limit: int | None = None,
) -> list[WikimediaAsset]:
    assets: list[WikimediaAsset] = []
    with httpx.Client(
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for destination in catalog.destinations:
            for landmark in destination.landmarks:
                if limit is not None and len(assets) >= limit:
                    return assets
                try:
                    asset = fetch_landmark_asset(client, destination, landmark, output_dir)
                except httpx.HTTPStatusError:
                    asset = None
                if asset:
                    assets.append(asset)
    return assets


def fetch_landmark_asset(
    client: httpx.Client,
    destination: Destination,
    landmark: Landmark,
    output_dir: Path,
) -> WikimediaAsset | None:
    selection_id = f"{destination.id}:{landmark.id}"
    query = (
        landmark.representative_query
        or QUERY_OVERRIDES.get(selection_id)
        or f"{landmark.name} {destination.city}"
    )
    titles = search_commons_files(client, query)
    candidates: list[tuple[str, dict[str, str]]] = []
    for title in titles:
        metadata = fetch_file_metadata(client, title)
        if not metadata:
            continue
        if not is_allowed_license(metadata["license_short_name"]):
            continue
        if not is_representative_candidate(
            title,
            metadata,
            required_terms=landmark.required_terms,
            rejected_terms=landmark.rejected_terms,
        ):
            continue
        candidates.append((title, metadata))
    best_candidate = choose_best_representative_candidate(
        candidates,
        required_terms=landmark.required_terms,
        rejected_terms=landmark.rejected_terms,
    )
    if best_candidate:
        title, metadata = best_candidate
        local_path = output_dir / destination.id / f"{landmark.id}{metadata['extension']}"
        try:
            download_file(client, metadata["image_url"], local_path)
        except httpx.HTTPStatusError:
            download_file(client, metadata["original_url"], local_path)
        return WikimediaAsset(
            selection_id=selection_id,
            title=title,
            source_url=metadata["source_url"],
            image_url=metadata["image_url"],
            local_path=local_path,
            author=metadata["author"],
            license_short_name=metadata["license_short_name"],
            license_url=metadata["license_url"],
            credit=metadata["credit"],
        )
    return None


def find_landmark_asset_metadata(
    client: httpx.Client,
    destination: Destination,
    landmark: Landmark,
) -> dict[str, str] | None:
    selection_id = f"{destination.id}:{landmark.id}"
    query = (
        landmark.representative_query
        or QUERY_OVERRIDES.get(selection_id)
        or f"{landmark.name} {destination.city}"
    )
    titles = search_commons_files(client, query)
    candidates: list[tuple[str, dict[str, str]]] = []
    for title in titles:
        metadata = fetch_file_metadata(client, title)
        if not metadata:
            continue
        if not is_allowed_license(metadata["license_short_name"]):
            continue
        if not is_representative_candidate(
            title,
            metadata,
            required_terms=landmark.required_terms,
            rejected_terms=landmark.rejected_terms,
        ):
            continue
        candidates.append((title, metadata))
    best_candidate = choose_best_representative_candidate(
        candidates,
        required_terms=landmark.required_terms,
        rejected_terms=landmark.rejected_terms,
    )
    if best_candidate:
        title, metadata = best_candidate
        return {
            "title": title,
            "image_url": metadata["image_url"],
            "source_url": metadata["source_url"],
            "author": metadata["author"],
            "license_short_name": metadata["license_short_name"],
            "license_url": metadata["license_url"],
            "credit": metadata["credit"],
        }
    return None


def choose_best_representative_candidate(
    candidates: list[tuple[str, dict[str, str]]],
    *,
    required_terms: list[str],
    rejected_terms: list[str],
) -> tuple[str, dict[str, str]] | None:
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda candidate: _representative_score(
            candidate[0],
            candidate[1],
            required_terms=required_terms,
            rejected_terms=rejected_terms,
        ),
        reverse=True,
    )
    return ranked[0]


def search_commons_files(client: httpx.Client, query: str) -> list[str]:
    response = request_with_retry(
        client,
        COMMONS_API_URL,
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit": 20,
        },
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    return [page["title"] for page in pages.values() if page.get("title", "").startswith("File:")]


def fetch_file_metadata(client: httpx.Client, title: str) -> dict[str, str] | None:
    response = request_with_retry(
        client,
        COMMONS_API_URL,
        params={
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1400,
        },
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    image_info = (page.get("imageinfo") or [{}])[0]
    image_url = image_info.get("thumburl") or image_info.get("url")
    if not image_url:
        return None
    extmetadata = image_info.get("extmetadata", {})
    license_short_name = ext_value(extmetadata, "LicenseShortName")
    author = strip_html(ext_value(extmetadata, "Artist") or "Wikimedia Commons contributor")
    credit = strip_html(ext_value(extmetadata, "Credit") or author)
    license_url = ext_value(extmetadata, "LicenseUrl")
    return {
        "image_url": image_url,
        "original_url": image_info.get("url", image_url),
        "source_url": f"https://commons.wikimedia.org/wiki/{quote(title.replace(' ', '_'))}",
        "author": author,
        "license_short_name": license_short_name,
        "license_url": license_url,
        "credit": credit,
        "extension": extension_from_url(image_url),
    }


def download_file(client: httpx.Client, url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    response = request_with_retry(
        client,
        url,
        headers={
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://commons.wikimedia.org/",
        },
    )
    response.raise_for_status()
    path.write_bytes(response.content)


def request_with_retry(client: httpx.Client, url: str, **kwargs: object) -> httpx.Response:
    last_response: httpx.Response | None = None
    time.sleep(0.8)
    for attempt in range(6):
        response = client.get(url, **kwargs)
        last_response = response
        if response.status_code != 429:
            return response
        retry_after = response.headers.get("retry-after")
        wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        time.sleep(min(wait_seconds, 16))
    assert last_response is not None
    return last_response


def is_allowed_license(license_short_name: str) -> bool:
    normalized = license_short_name.strip().lower()
    return any(normalized.startswith(prefix) for prefix in ALLOWED_LICENSE_PREFIXES)


def is_representative_candidate(
    title: str,
    metadata: dict[str, str],
    required_terms: list[str],
    rejected_terms: list[str],
) -> bool:
    haystack = normalize_search_text(
        " ".join(
            [
                title,
                metadata.get("source_url", ""),
                metadata.get("image_url", ""),
                metadata.get("author", ""),
                metadata.get("credit", ""),
            ]
        )
    )
    if any(normalize_search_text(term) in haystack for term in rejected_terms):
        return False
    return all(normalize_search_text(term) in haystack for term in required_terms)


def _representative_score(
    title: str,
    metadata: dict[str, str],
    *,
    required_terms: list[str],
    rejected_terms: list[str],
) -> int:
    haystack = normalize_search_text(
        " ".join(
            [
                title,
                metadata.get("source_url", ""),
                metadata.get("image_url", ""),
                metadata.get("author", ""),
                metadata.get("credit", ""),
            ]
        )
    )
    score = 0
    for term in required_terms:
        normalized_term = normalize_search_text(term)
        if normalized_term and normalized_term in haystack:
            score += 50
    for term in rejected_terms:
        normalized_term = normalize_search_text(term)
        if normalized_term and normalized_term in haystack:
            score -= 200
    title_text = normalize_search_text(title)
    score += sum(8 for term in required_terms if normalize_search_text(term) in title_text)
    if "logo" in haystack or "map" in haystack:
        score -= 40
    if "svg" in metadata.get("image_url", "").lower():
        score -= 30
    return score


def normalize_search_text(value: str) -> str:
    without_accents = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    lowered = without_accents.lower()
    separator_map = str.maketrans({character: " " for character in f"{punctuation}_"})
    return " ".join(lowered.translate(separator_map).split())


def ext_value(metadata: dict[str, dict[str, str]], key: str) -> str:
    value = metadata.get(key, {}).get("value", "")
    return str(value)


def strip_html(value: str) -> str:
    import re

    cleaned = re.sub(r"<[^>]+>", "", value)
    return " ".join(cleaned.split())


def extension_from_url(url: str) -> str:
    suffix = Path(url.split("?", maxsplit=1)[0]).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return suffix
    return ".jpg"
