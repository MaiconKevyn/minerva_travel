"""Private page-first guide-builder sessions."""

from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock, RLock
from typing import Any
from uuid import uuid4

from minerva_travel import storage
from minerva_travel.config import guide_draft_retention_days

MAX_ATTEMPTS_PER_PAGE = 4
MAX_REVISION_INSTRUCTION_LENGTH = 600


class BuilderSessionNotFound(Exception):
    pass


class BuilderAttemptLimitReached(Exception):
    pass


class BuilderAttemptInProgress(Exception):
    pass


class BuilderPageOutOfOrder(Exception):
    pass


class BuilderPageDependencyMissing(Exception):
    pass


class BuilderAttemptNotFound(Exception):
    pass


class BuilderIncomplete(Exception):
    pass


class BuilderLayoutConflict(Exception):
    def __init__(self, current_revision: int) -> None:
        super().__init__(str(current_revision))
        self.current_revision = current_revision


class BuilderActivityDuplicate(Exception):
    pass


class BuilderActivityNotFound(Exception):
    pass


class BuilderActivityAnchorInvalid(Exception):
    pass


class BuilderActivityRemovalConfirmationRequired(Exception):
    pass


@dataclass
class BuilderAttempt:
    id: str
    filename: str
    created_at: str
    idempotency_key: str
    revision_instruction: str = ""
    include_family: bool = False


@dataclass
class BuilderPage:
    id: str
    kind: str
    title: str
    position: int
    required_copy: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    attempts: list[BuilderAttempt] = field(default_factory=list)
    selected_attempt_id: str | None = None
    approved_at: str | None = None
    pending_attempt_id: str | None = None
    pending_idempotency_key: str | None = None
    pending_revision_instruction: str = ""
    pending_include_family: bool = False
    error: str | None = None

    def selected_attempt(self) -> BuilderAttempt | None:
        if self.selected_attempt_id:
            for attempt in self.attempts:
                if attempt.id == self.selected_attempt_id:
                    return attempt
        return self.attempts[-1] if self.attempts else None

    @property
    def status(self) -> str:
        if self.approved_at:
            return "approved"
        if self.pending_attempt_id:
            return "generating"
        if self.error:
            return "error"
        if self.attempts:
            return "awaiting_approval"
        return "ready"


@dataclass
class BuilderSession:
    id: str
    owner_id: str
    created_at: str
    expires_at: str
    form: dict[str, Any]
    photo_filename: str
    pages: list[BuilderPage]
    privacy_consent: dict[str, Any] | None = None
    revision: int = 0
    layout_revision: int = 0

    def page(self, page_id: str) -> BuilderPage | None:
        return next((page for page in self.pages if page.id == page_id), None)

    def active_page(self) -> BuilderPage | None:
        return next((page for page in self.ordered_pages() if page.approved_at is None), None)

    def ordered_pages(self) -> list[BuilderPage]:
        return sorted(self.pages, key=lambda page: (page.position, page.id))

    @property
    def is_complete(self) -> bool:
        return bool(self.pages) and all(page.approved_at for page in self.pages)

    @property
    def is_expired(self) -> bool:
        return datetime.fromisoformat(self.expires_at) <= datetime.now(UTC)

    def allowed_asset_filenames(self) -> set[str]:
        return {attempt.filename for page in self.pages for attempt in page.attempts}

    def public_payload(self) -> dict[str, Any]:
        active_page = self.active_page()
        return {
            "session_id": self.id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "title": self.form.get("title", ""),
            "revision": self.revision,
            "layout_revision": self.layout_revision,
            "active_page_id": active_page.id if active_page else None,
            "is_complete": self.is_complete,
            "pages": [self._page_payload(page) for page in self.ordered_pages()],
        }

    def approved_manifest(self) -> list[dict[str, Any]]:
        manifest: list[dict[str, Any]] = []
        for page in self.ordered_pages():
            attempt = page.selected_attempt()
            if not page.approved_at or attempt is None:
                raise BuilderIncomplete(self.id)
            manifest.append(
                {
                    "page_id": page.id,
                    "kind": page.kind,
                    "title": page.title,
                    "position": page.position,
                    "attempt_id": attempt.id,
                    "asset_url": self._asset_url(attempt.filename),
                    "approved_at": page.approved_at,
                    "required_copy": page.required_copy,
                }
            )
        return manifest

    def approved_asset_filenames(self) -> list[str]:
        self.approved_manifest()
        return [
            attempt.filename
            for page in self.ordered_pages()
            if (attempt := page.selected_attempt()) is not None
        ]

    def _page_payload(self, page: BuilderPage) -> dict[str, Any]:
        chosen = page.selected_attempt()
        return {
            "id": page.id,
            "kind": page.kind,
            "title": page.title,
            "position": page.position,
            "status": page.status,
            "required_copy": page.required_copy,
            "attempts": [
                {
                    "id": attempt.id,
                    "asset_url": self._asset_url(attempt.filename),
                    "created_at": attempt.created_at,
                    "revision_instruction": attempt.revision_instruction,
                    "include_family": attempt.include_family,
                }
                for attempt in page.attempts
            ],
            "selected_attempt_id": chosen.id if chosen else None,
            "attempts_left": MAX_ATTEMPTS_PER_PAGE - len(page.attempts),
            "approved_at": page.approved_at,
            "error": page.error,
            "metadata": _public_page_metadata(page.metadata),
        }

    def _asset_url(self, filename: str) -> str:
        return f"/guide-builder/{self.id}/assets/{filename}"


_locks_guard = Lock()
_session_locks: dict[str, RLock] = {}


@contextmanager
def builder_session_lock(session_id: str) -> Iterator[None]:
    with _locks_guard:
        lock = _session_locks.setdefault(session_id, RLock())
    with lock:
        yield


def builder_sessions_dir() -> Path:
    return storage.RUNTIME_DIR / "builder"


def builder_asset_dir(session_id: str) -> Path:
    return storage.RUNTIME_DIR / "generated" / "builder" / session_id


def builder_pdf_path(session_id: str) -> Path:
    return builder_asset_dir(session_id) / "approved-guide.pdf"


def create_builder_session(
    *,
    owner_id: str,
    form: dict[str, Any],
    photo_path: Path,
    pages: list[BuilderPage],
    privacy_consent: dict[str, Any] | None,
) -> BuilderSession:
    now = datetime.now(UTC)
    session = BuilderSession(
        id=uuid4().hex,
        owner_id=owner_id,
        created_at=now.isoformat(),
        expires_at=(now + timedelta(days=guide_draft_retention_days())).isoformat(),
        form=form,
        photo_filename=str(photo_path),
        pages=pages,
        privacy_consent=privacy_consent,
    )
    save_builder_session(session)
    return session


def save_builder_session(session: BuilderSession) -> None:
    path = builder_sessions_dir() / f"{session.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    session.revision += 1
    temporary.write_text(json.dumps(asdict(session), ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def load_builder_session(session_id: str, owner_id: str) -> BuilderSession:
    session = _load_builder_session(session_id)
    if session.owner_id != owner_id or session.is_expired:
        raise BuilderSessionNotFound(session_id)
    return session


def _load_builder_session(session_id: str) -> BuilderSession:
    safe_id = "".join(char for char in session_id if char.isalnum())
    if not safe_id or safe_id != session_id:
        raise BuilderSessionNotFound(session_id)
    path = builder_sessions_dir() / f"{safe_id}.json"
    if not path.is_file():
        raise BuilderSessionNotFound(session_id)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return BuilderSession(
            id=payload["id"],
            owner_id=payload["owner_id"],
            created_at=payload["created_at"],
            expires_at=payload["expires_at"],
            form=payload["form"],
            photo_filename=payload["photo_filename"],
            privacy_consent=payload.get("privacy_consent"),
            revision=int(payload.get("revision", 0)),
            layout_revision=int(payload.get("layout_revision", 0)),
            pages=[
                BuilderPage(
                    **{
                        **page,
                        "attempts": [
                            BuilderAttempt(**{"include_family": True, **item})
                            for item in page.get("attempts", [])
                        ],
                    }
                )
                for page in payload["pages"]
            ],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise BuilderSessionNotFound(session_id) from error


def reserve_page_attempt(
    session: BuilderSession,
    page_id: str,
    idempotency_key: str,
    revision_instruction: str = "",
    include_family: bool = False,
) -> tuple[str, bool]:
    page = session.page(page_id)
    if page is None:
        raise BuilderPageOutOfOrder(page_id)
    for attempt in page.attempts:
        if attempt.idempotency_key == idempotency_key:
            return attempt.id, True
    if page.approved_at:
        raise BuilderPageOutOfOrder(page_id)
    if page.pending_attempt_id:
        raise BuilderAttemptInProgress(page_id)
    if len(page.attempts) >= MAX_ATTEMPTS_PER_PAGE:
        raise BuilderAttemptLimitReached(page_id)
    attempt_id = f"{page.id}-{len(page.attempts) + 1}"
    page.pending_attempt_id = attempt_id
    page.pending_idempotency_key = idempotency_key
    page.pending_revision_instruction = normalize_revision_instruction(revision_instruction)
    page.pending_include_family = include_family
    page.error = None
    save_builder_session(session)
    return attempt_id, False


def commit_page_attempt(
    session: BuilderSession, page_id: str, attempt_id: str, filename: str
) -> BuilderAttempt:
    page = session.page(page_id)
    if page is None or page.pending_attempt_id != attempt_id or not page.pending_idempotency_key:
        raise BuilderAttemptInProgress(page_id)
    attempt = BuilderAttempt(
        id=attempt_id,
        filename=filename,
        created_at=datetime.now(UTC).isoformat(),
        idempotency_key=page.pending_idempotency_key,
        revision_instruction=page.pending_revision_instruction,
        include_family=page.pending_include_family,
    )
    page.attempts.append(attempt)
    page.selected_attempt_id = attempt.id
    page.pending_attempt_id = None
    page.pending_idempotency_key = None
    page.pending_revision_instruction = ""
    page.pending_include_family = False
    page.error = None
    save_builder_session(session)
    return attempt


def rollback_page_attempt(
    session: BuilderSession, page_id: str, attempt_id: str, message: str
) -> None:
    page = session.page(page_id)
    if page is None or page.pending_attempt_id != attempt_id:
        return
    page.pending_attempt_id = None
    page.pending_idempotency_key = None
    page.pending_revision_instruction = ""
    page.pending_include_family = False
    page.error = message
    save_builder_session(session)


def select_page_attempt(session: BuilderSession, page_id: str, attempt_id: str) -> None:
    page = session.page(page_id)
    if page is None or not any(attempt.id == attempt_id for attempt in page.attempts):
        raise BuilderAttemptNotFound(attempt_id)
    if page.approved_at:
        raise BuilderPageOutOfOrder(page_id)
    page.selected_attempt_id = attempt_id
    page.error = None
    save_builder_session(session)


def approve_page_attempt(session: BuilderSession, page_id: str, attempt_id: str | None) -> None:
    page = session.page(page_id)
    if page is None or page.approved_at:
        raise BuilderPageOutOfOrder(page_id)
    if page.pending_attempt_id:
        raise BuilderAttemptInProgress(page_id)
    selected = attempt_id or page.selected_attempt_id
    if not selected or not any(attempt.id == selected for attempt in page.attempts):
        raise BuilderAttemptNotFound(selected or "")
    page.selected_attempt_id = selected
    page.approved_at = datetime.now(UTC).isoformat()
    page.error = None
    save_builder_session(session)


def add_activity_page(
    session: BuilderSession,
    page: BuilderPage,
    *,
    after_page_id: str | None,
    expected_layout_revision: int,
) -> None:
    """Add one server-built activity page at a legal, canonical layout position."""

    _assert_layout_revision(session, expected_layout_revision)
    if page.kind != "landmark_activity":
        raise BuilderActivityNotFound(page.id)
    if session.page(page.id) is not None:
        raise BuilderActivityDuplicate(page.id)

    ordered = session.ordered_pages()
    linked_page_id = str(page.metadata.get("linked_landmark_page_id") or "")
    if after_page_id is None:
        anchor_index = _default_activity_anchor_index(ordered, linked_page_id)
    else:
        anchor_index = _activity_anchor_index(ordered, after_page_id, linked_page_id)
    ordered.insert(anchor_index + 1, page)
    _commit_layout(session, ordered)


def move_activity_page(
    session: BuilderSession,
    page_id: str,
    *,
    after_page_id: str,
    expected_layout_revision: int,
) -> None:
    """Move only an optional activity while keeping all fixed pages in relative order."""

    _assert_layout_revision(session, expected_layout_revision)
    page = session.page(page_id)
    if page is None or page.kind != "landmark_activity":
        raise BuilderActivityNotFound(page_id)
    if page_id == after_page_id:
        raise BuilderActivityAnchorInvalid(after_page_id)

    ordered = [item for item in session.ordered_pages() if item.id != page_id]
    linked_page_id = str(page.metadata.get("linked_landmark_page_id") or "")
    anchor_index = _activity_anchor_index(ordered, after_page_id, linked_page_id)
    ordered.insert(anchor_index + 1, page)
    _commit_layout(session, ordered)


def remove_activity_page(
    session: BuilderSession,
    page_id: str,
    *,
    expected_layout_revision: int,
    confirm_generated: bool,
) -> None:
    """Remove one optional activity and its private attempts from the session."""

    _assert_layout_revision(session, expected_layout_revision)
    page = session.page(page_id)
    if page is None or page.kind != "landmark_activity":
        raise BuilderActivityNotFound(page_id)
    if page.pending_attempt_id:
        raise BuilderAttemptInProgress(page_id)
    if page.attempts and not confirm_generated:
        raise BuilderActivityRemovalConfirmationRequired(page_id)

    asset_root = builder_asset_dir(session.id)
    for attempt in page.attempts:
        candidate = asset_root / attempt.filename
        if candidate.parent == asset_root and candidate.name == attempt.filename:
            candidate.unlink(missing_ok=True)
    _commit_layout(
        session,
        [item for item in session.ordered_pages() if item.id != page_id],
    )


def _assert_layout_revision(session: BuilderSession, expected: int) -> None:
    if session.layout_revision != expected:
        raise BuilderLayoutConflict(session.layout_revision)


def _default_activity_anchor_index(ordered: list[BuilderPage], linked_page_id: str) -> int:
    linked_index = next(
        (index for index, item in enumerate(ordered) if item.id == linked_page_id),
        None,
    )
    if linked_index is None:
        raise BuilderActivityAnchorInvalid(linked_page_id)
    anchor_index = linked_index
    for index in range(linked_index + 1, len(ordered)):
        item = ordered[index]
        if (
            item.kind != "landmark_activity"
            or item.metadata.get("linked_landmark_page_id") != linked_page_id
        ):
            break
        anchor_index = index
    return anchor_index


def _activity_anchor_index(
    ordered: list[BuilderPage], after_page_id: str, linked_page_id: str
) -> int:
    anchor_index = next(
        (index for index, item in enumerate(ordered) if item.id == after_page_id),
        None,
    )
    linked_index = next(
        (index for index, item in enumerate(ordered) if item.id == linked_page_id),
        None,
    )
    if anchor_index is None or linked_index is None:
        raise BuilderActivityAnchorInvalid(after_page_id)
    anchor = ordered[anchor_index]
    if anchor.kind in {"best_memory", "homecoming"} or anchor_index < linked_index:
        raise BuilderActivityAnchorInvalid(after_page_id)
    return anchor_index


def _commit_layout(session: BuilderSession, ordered: list[BuilderPage]) -> None:
    for position, page in enumerate(ordered, start=1):
        page.position = position
    session.pages = ordered
    _sync_activity_selections(session)
    session.layout_revision += 1
    builder_pdf_path(session.id).unlink(missing_ok=True)
    save_builder_session(session)


def _sync_activity_selections(session: BuilderSession) -> None:
    counts: dict[str, int] = {}
    selections: list[dict[str, Any]] = []
    for page in session.ordered_pages():
        if page.kind != "landmark_activity":
            continue
        landmark_id = str(page.metadata.get("landmark_selection_id") or "")
        activity_type = str(page.metadata.get("activity_type") or "")
        if not landmark_id or not activity_type:
            continue
        counts[landmark_id] = counts.get(landmark_id, 0) + 1
        selections.append(
            {
                "landmark_selection_id": landmark_id,
                "activity_type": activity_type,
                "order": counts[landmark_id],
            }
        )
    session.form["activity_selections"] = selections


def delete_builder_sessions_for_owner(owner_id: str) -> int:
    deleted_files = 0
    root = builder_sessions_dir()
    if not root.is_dir():
        return 0
    for path in root.glob("*.json"):
        try:
            with builder_session_lock(path.stem):
                session = _load_builder_session(path.stem)
                if session.owner_id == owner_id:
                    deleted_files += delete_builder_session(session)
        except BuilderSessionNotFound:
            continue
    return deleted_files


def cleanup_expired_builder_sessions(*, now: datetime | None = None) -> int:
    deleted_sessions = 0
    current = now or datetime.now(UTC)
    root = builder_sessions_dir()
    if not root.is_dir():
        return 0
    for path in root.glob("*.json"):
        with builder_session_lock(path.stem):
            try:
                session = _load_builder_session(path.stem)
                expired = datetime.fromisoformat(session.expires_at) <= current
            except BuilderSessionNotFound:
                expired = True
                session = None
            if not expired:
                continue
            if session is not None:
                delete_builder_session(session)
            else:
                path.unlink(missing_ok=True)
            deleted_sessions += 1
    return deleted_sessions


def delete_builder_session(session: BuilderSession) -> int:
    deleted = 0
    photo = Path(session.photo_filename)
    if _is_private_runtime_path(photo) and photo.is_file():
        photo.unlink()
        deleted += 1
    assets = builder_asset_dir(session.id)
    if _is_private_runtime_path(assets) and assets.is_dir():
        deleted += sum(1 for item in assets.rglob("*") if item.is_file())
        shutil.rmtree(assets)
    session_path = builder_sessions_dir() / f"{session.id}.json"
    if _is_private_runtime_path(session_path) and session_path.is_file():
        session_path.unlink()
        deleted += 1
    with _locks_guard:
        _session_locks.pop(session.id, None)
    return deleted


def _is_private_runtime_path(path: Path) -> bool:
    try:
        root = storage.RUNTIME_DIR.resolve()
        candidate = path.resolve()
    except OSError:
        return False
    return candidate == root or root in candidate.parents


def normalize_revision_instruction(value: str) -> str:
    """Normalize bounded human design feedback before storing or prompting."""

    return " ".join(value.split())[:MAX_REVISION_INSTRUCTION_LENGTH]


_PUBLIC_PAGE_METADATA_FIELDS = {
    "trip_date",
    "landmark_names",
    "destination_id",
    "destination_title",
    "landmark_selection_id",
    "landmark_name",
    "city",
    "country",
    "description",
    "curiosity",
    "curiosity_kind",
    "curiosity_label",
    "learning_points",
    "activity_type",
    "activity_label",
    "instruction",
    "age_complexity",
    "source_image_available",
    "linked_landmark_page_id",
}


def _public_page_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Expose review copy while keeping private paths and provider specs server-side."""

    return {
        key: value
        for key, value in metadata.items()
        if key in _PUBLIC_PAGE_METADATA_FIELDS and value is not None
    }
