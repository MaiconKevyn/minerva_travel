"""Stable product/API limits shared by validation, OpenAPI and generated clients."""

MAX_GUIDE_CHILDREN = 10
MAX_GUIDE_PARENTS = 10
MAX_GUIDE_DESTINATIONS = 10
MAX_GUIDE_LANDMARKS = 30
MAX_VISIBLE_FAMILY_MEMBERS = 20

MIN_GUIDE_YEAR = 2024
MAX_GUIDE_YEAR = 2100

DEFAULT_IMAGE_UPLOAD_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_IMAGE_UPLOAD_MAX_PIXELS = 40_000_000
DEFAULT_IMAGE_UPLOAD_MAX_WIDTH = 12_000
DEFAULT_IMAGE_UPLOAD_MAX_HEIGHT = 12_000


def public_contract_limits() -> dict[str, int]:
    return {
        "max_guide_children": MAX_GUIDE_CHILDREN,
        "max_guide_parents": MAX_GUIDE_PARENTS,
        "max_guide_destinations": MAX_GUIDE_DESTINATIONS,
        "max_guide_landmarks": MAX_GUIDE_LANDMARKS,
        "max_visible_family_members": MAX_VISIBLE_FAMILY_MEMBERS,
        "min_guide_year": MIN_GUIDE_YEAR,
        "max_guide_year": MAX_GUIDE_YEAR,
        "image_upload_max_bytes": DEFAULT_IMAGE_UPLOAD_MAX_BYTES,
        "image_upload_max_pixels": DEFAULT_IMAGE_UPLOAD_MAX_PIXELS,
        "image_upload_max_width": DEFAULT_IMAGE_UPLOAD_MAX_WIDTH,
        "image_upload_max_height": DEFAULT_IMAGE_UPLOAD_MAX_HEIGHT,
    }
