"""Remove expired guides, drafts, and progressive builder sessions."""

from minerva_travel.builder import cleanup_expired_builder_sessions
from minerva_travel.persistence import cleanup_expired_drafts, cleanup_expired_guides


def main() -> None:
    guides_deleted = cleanup_expired_guides()
    drafts_deleted = cleanup_expired_drafts()
    builder_sessions_deleted = cleanup_expired_builder_sessions()
    print(f"Expired guides removed: {guides_deleted}")
    print(f"Expired drafts removed: {drafts_deleted}")
    print(f"Expired builder sessions removed: {builder_sessions_deleted}")


if __name__ == "__main__":
    main()
