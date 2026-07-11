"""Remove expired guides and server-side drafts from local persistence."""

from minerva_travel.persistence import cleanup_expired_drafts, cleanup_expired_guides


def main() -> None:
    guides_deleted = cleanup_expired_guides()
    drafts_deleted = cleanup_expired_drafts()
    print(f"Expired guides removed: {guides_deleted}")
    print(f"Expired drafts removed: {drafts_deleted}")


if __name__ == "__main__":
    main()
