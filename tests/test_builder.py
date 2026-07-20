import json
from datetime import UTC, datetime, timedelta

import pytest

from minerva_travel.builder import (
    BuilderAttemptInProgress,
    BuilderPage,
    cleanup_expired_builder_sessions,
    commit_page_attempt,
    create_builder_session,
    load_builder_session,
    reserve_page_attempt,
    save_builder_session,
)


def _page() -> BuilderPage:
    return BuilderPage(
        id="cover",
        kind="cover",
        title="Capa",
        position=1,
        required_copy=["Família Teste", "2026"],
    )


def test_pending_attempt_prevents_a_second_provider_reservation(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    photo = tmp_path / "uploads" / "family.png"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"private-photo")
    session = create_builder_session(
        owner_id="owner",
        form={"title": "Família Teste"},
        photo_path=photo,
        pages=[_page()],
        privacy_consent=None,
    )

    attempt_id, replayed = reserve_page_attempt(session, "cover", "request-one")

    assert attempt_id == "cover-1"
    assert replayed is False
    with pytest.raises(BuilderAttemptInProgress):
        reserve_page_attempt(session, "cover", "request-two")


def test_idempotent_replay_does_not_change_the_selected_version(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    photo = tmp_path / "family.png"
    photo.write_bytes(b"private-photo")
    session = create_builder_session(
        owner_id="owner",
        form={"title": "Família Teste"},
        photo_path=photo,
        pages=[_page()],
        privacy_consent=None,
    )

    first_id, _ = reserve_page_attempt(session, "cover", "request-one")
    commit_page_attempt(session, "cover", first_id, "cover-1.png")
    second_id, _ = reserve_page_attempt(session, "cover", "request-two")
    commit_page_attempt(session, "cover", second_id, "cover-2.png")

    replayed_id, replayed = reserve_page_attempt(session, "cover", "request-one")

    assert replayed_id == first_id
    assert replayed is True
    assert session.page("cover").selected_attempt_id == second_id


def test_expired_cleanup_removes_manifest_photo_and_generated_assets(tmp_path, monkeypatch):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    photo = tmp_path / "uploads" / "family.png"
    photo.parent.mkdir(parents=True)
    photo.write_bytes(b"private-photo")
    session = create_builder_session(
        owner_id="owner",
        form={"title": "Família Teste"},
        photo_path=photo,
        pages=[_page()],
        privacy_consent=None,
    )
    assets = tmp_path / "generated" / "builder" / session.id
    assets.mkdir(parents=True)
    (assets / "cover-1.png").write_bytes(b"private-image")
    session.expires_at = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    save_builder_session(session)

    assert cleanup_expired_builder_sessions() == 1
    assert not photo.exists()
    assert not assets.exists()
    assert not (tmp_path / "builder" / f"{session.id}.json").exists()


def test_revision_instruction_is_normalized_persisted_and_old_sessions_remain_readable(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("minerva_travel.storage.RUNTIME_DIR", tmp_path)
    photo = tmp_path / "family.png"
    photo.write_bytes(b"private-photo")
    session = create_builder_session(
        owner_id="owner",
        form={"title": "Família Teste"},
        photo_path=photo,
        pages=[_page()],
        privacy_consent=None,
    )

    attempt_id, _ = reserve_page_attempt(
        session, "cover", "request-one", "  Mude   para colagem\ncom tons azuis.  "
    )
    commit_page_attempt(session, "cover", attempt_id, "cover-1.png")
    loaded = load_builder_session(session.id, "owner")
    assert loaded.pages[0].attempts[0].revision_instruction == ("Mude para colagem com tons azuis.")
    assert (
        loaded.public_payload()["pages"][0]["attempts"][0]["revision_instruction"]
        == "Mude para colagem com tons azuis."
    )

    session_path = tmp_path / "builder" / f"{session.id}.json"
    legacy_payload = json.loads(session_path.read_text(encoding="utf-8"))
    legacy_payload["pages"][0].pop("pending_revision_instruction")
    legacy_payload["pages"][0]["attempts"][0].pop("revision_instruction")
    session_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

    legacy = load_builder_session(session.id, "owner")
    assert legacy.pages[0].pending_revision_instruction == ""
    assert legacy.pages[0].attempts[0].revision_instruction == ""
