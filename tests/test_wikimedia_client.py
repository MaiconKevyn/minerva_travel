from minerva_travel.wikimedia_client import (
    extension_from_url,
    is_allowed_license,
    is_representative_candidate,
    normalize_search_text,
    strip_html,
)


def test_is_allowed_license_accepts_commercial_friendly_commons_licenses():
    assert is_allowed_license("CC BY-SA 4.0")
    assert is_allowed_license("CC BY 2.0")
    assert is_allowed_license("CC0")
    assert is_allowed_license("Public domain")


def test_is_allowed_license_rejects_unknown_license():
    assert not is_allowed_license("Fair use")


def test_strip_html_removes_credit_markup():
    assert strip_html('<a href="/wiki/User:Jane">Jane Doe</a>') == "Jane Doe"


def test_extension_from_url_keeps_supported_image_suffix():
    assert extension_from_url("https://upload.wikimedia.org/example.png?width=1200") == ".png"
    assert extension_from_url("https://upload.wikimedia.org/example.tiff") == ".jpg"


def test_representative_candidate_accepts_required_terms():
    metadata = {
        "source_url": "https://commons.wikimedia.org/wiki/File:Big_Ben_clock_tower_London.jpg",
        "image_url": "https://upload.wikimedia.org/big-ben-clock-tower.jpg",
        "author": "Jane Doe",
        "credit": "Big Ben clock tower in London",
    }

    assert is_representative_candidate(
        "File:Big Ben clock tower London.jpg",
        metadata,
        required_terms=["big", "ben", "clock"],
        rejected_terms=["leiden", "stained glass"],
    )


def test_representative_candidate_rejects_wrong_landmark():
    metadata = {
        "source_url": "https://commons.wikimedia.org/wiki/File:AcademiegebouwLeiden1.JPG",
        "image_url": "https://upload.wikimedia.org/academiegebouw-leiden-stained-glass.jpg",
        "author": "Jane Doe",
        "credit": "Academiegebouw Leiden stained glass",
    }

    assert not is_representative_candidate(
        "File:AcademiegebouwLeiden1.JPG",
        metadata,
        required_terms=["big", "ben", "clock"],
        rejected_terms=["leiden", "stained glass"],
    )


def test_normalize_search_text_treats_punctuation_as_spaces():
    assert normalize_search_text("Musée de l'Opéra, Palais-Garnier") == (
        "musee de l opera palais garnier"
    )
