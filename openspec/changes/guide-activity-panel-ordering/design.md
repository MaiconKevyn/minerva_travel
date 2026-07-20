## Context

The wizard currently offers four optional landmark-bound activities in a dedicated step. The final
review submits those selections when it creates a builder session. The backend then materializes an
ordered list containing cover, summary, destination introductions, tourist points, selected
activities, `Minha melhor memória`, and homecoming. Every page has a numeric `position`; generation
can happen independently and the PDF compositor sorts by that position.

`GuideAssembly` already lets the parent open and generate any page while other pages are running,
but it treats the page plan as immutable. The existing activity examples are lightweight SVG cards,
not realistic previews of a completed portrait page. Supporting activity additions and placement
inside the builder therefore requires an owner-scoped structural mutation rather than frontend-only
state.

## Goals / Non-Goals

**Goals:**

- Make optional activities easy to understand and add from the final 6/6 page builder.
- Show honest, realistic examples before a parent commits a page to the guide.
- Keep every activity bound to a canonical selected tourist point.
- Make page placement visual, responsive, keyboard accessible, and persistent.
- Keep generation state, attempts, approvals, and provider requests independent from page order.
- Guarantee the exact approved browser order is the final PDF order.

**Non-Goals:**

- Arbitrary reordering of narrative pages.
- Cross-guide activity templates or a marketplace.
- A free-form visual page editor.
- A provider call while browsing or adding an activity.
- Retrofitting activity placement into the legacy non-progressive PDF engine.

## Proposed User Journey

1. The parent reaches the final builder and sees the ordered guide outline.
2. `Adicionar atividades` opens a right-side sheet on desktop and a full-width sheet on mobile
   without losing the selected guide page.
3. The catalog shows the four existing activities with a realistic portrait example, label,
   explanation, age, time, materials, and `Ver exemplo` action.
4. The parent chooses a tourist point. Cards that already reached the two-per-point limit or would
   duplicate an existing type explain why they cannot be added.
5. `Adicionar ao guia` creates a `ready` activity page at the default slot immediately after the
   linked tourist point (and after its existing activities). No OpenAI call occurs.
6. The panel switches to `Organizar páginas`, where the activity block can be dragged among legal
   insertion slots. The same action is available through `Inserir depois de`, `Mover para cima`, and
   `Mover para baixo` controls.
7. The changed outline displays the resulting page numbers and a short saved/saving/error state.
8. The parent can close the panel, open the new block, and generate it at any time. Generating a
   different page concurrently remains supported.
9. The PDF uses the latest ordered pages. A structural change after an earlier PDF export removes
   that cached PDF and requires a fresh export.

## Layout Model

The server owns two classes of pages:

- **fixed pages**: cover, summary, destination introductions, tourist points, best memory, and
  homecoming. Their relative order cannot change;
- **movable pages**: `landmark_activity` pages only.

An activity is always bound to `metadata.landmark_selection_id` and
`metadata.linked_landmark_page_id`. Its default anchor is the linked tourist point. A legal target
must be after the linked tourist point and before `best-memory`; it may be after a later fixed page
when the parent deliberately chooses that location. `best-memory` and `homecoming` remain the final
two pages.

The browser displays numbered insertion slots rather than accepting a raw page number. A move is
expressed with stable page IDs:

```json
{
  "after_page_id": "landmark-2",
  "layout_revision": 4
}
```

After each structural mutation, the server rebuilds contiguous positions `1..N`. Numeric positions
are response data, never authoritative client input.

## Decisions

### Decision 1: Extend the final builder without removing the earlier activity step

The earlier `Atividades da aventura` screen remains available for fast initial selection and draft
compatibility. The final builder adds a richer activity catalog and layout editor backed by the
same four activity types and limits. This avoids a wizard migration and gives parents a second,
better-informed decision point after they can see the whole guide.

### Decision 2: Use representative full-page examples, not thumbnails invented at runtime

Each catalog card uses a committed optimized WebP or PNG made from a synthetic, non-user guide and
representative of the real portrait output. The examples are generated once through the same visual
pipeline, reviewed for readable copy and child usability, stripped of metadata, and clearly marked
`Exemplo`. A click opens the full portrait image with meaningful alt text.

Static examples make catalog browsing instant and free. They must not contain a real customer's
family, name, itinerary, upload, or generated private asset. The implementation replaces the
current schematic SVG card art only after the new raster files pass size and visual checks.

### Decision 3: Adding an activity is a structural operation, not generation

The client sends only `landmark_selection_id`, one allowed `activity_type`, an optional stable
`after_page_id`, and the current `layout_revision`. The backend resolves the selected landmark from
the private immutable context already stored on its landmark page, builds `required_copy` and
activity metadata through the existing `_activity_spec` path, and creates a `ready` page with zero
attempts.

The operation rejects unknown/unselected landmarks, duplicate point/type pairs, more than two
activities for a point, more than eight for a guide, invalid anchors, completed/expired/foreign
sessions, and changes while that same structural page is being mutated. It never accepts prompt
copy, asset paths, source URLs, position numbers, or arbitrary metadata.

### Decision 4: Add focused owner-scoped layout endpoints

Proposed authenticated routes:

```text
POST   /api/guide-builder/{session_id}/activities
PATCH  /api/guide-builder/{session_id}/activities/{page_id}/position
DELETE /api/guide-builder/{session_id}/activities/{page_id}
```

Request shapes remain narrow:

```json
// add
{
  "landmark_selection_id": "paris:eiffel-tower",
  "activity_type": "coloring",
  "after_page_id": "landmark-1",
  "layout_revision": 4
}

// move
{
  "after_page_id": "landmark-2",
  "layout_revision": 5
}
```

Every success returns the complete `BuilderSessionResponse`, so existing session hydration and
asset handling remain authoritative. Errors contain stable codes for duplicate, quota, illegal
anchor, in-progress removal, and layout conflict.

### Decision 5: Track layout conflicts separately from generation revisions

The current session `revision` changes for generation and approval updates. Reusing it for drag
conflict detection would make a harmless page-generation response reject a layout move. Add a
backward-compatible `layout_revision` field, defaulting to `0` for saved sessions. Only add, remove,
and move operations increment it; normal session persistence still increments `revision`.

Structural writes run inside `builder_session_lock`, compare `layout_revision`, update positions,
delete any invalid cached PDF atomically, and save once. On a conflict, the API returns the latest
session and the UI refreshes the outline before asking the parent to repeat the move.

### Decision 6: Preserve independent concurrent generation

Adding or moving an activity does not touch `pending_attempt_id`, idempotency keys, attempts,
selected versions, approvals, or errors on any existing page. Because generation reserves a page,
releases the session lock for the provider call, and later reacquires it, structural writes can
complete while another page is with OpenAI.

Removing an activity is blocked while that page is generating. Removing a generated or approved
activity requires a destructive confirmation, deletes only that page's allowlisted attempts, and
invalidates the PDF cache. Other pages and in-flight requests are unaffected. Responses are merged
by server revision so an older async generation response cannot restore a deleted or stale order.

### Decision 7: Make drag and drop progressive enhancement

The ordered outline is the source UI. Activity cards expose a drag handle on pointer-capable
screens, but every action is also available without dragging:

- `Inserir depois de` select listing only legal anchors;
- `Mover para cima` and `Mover para baixo` buttons;
- keyboard activation and visible focus;
- live-region announcements such as `Página para colorir movida para a página 7`.

Fixed page cards show a lock cue and act as drop anchors, not draggable items. Mobile uses the same
block list and explicit move sheet to avoid fragile long-press behavior. During a save, only the
affected activity is disabled; failures roll the optimistic order back and preserve focus.

No third-party drag dependency is required unless implementation proves native pointer/keyboard
handling insufficient. If a library is added, its bundle and accessibility impact must be measured.

### Decision 8: Keep PDF order canonical and invalidate cached exports

`ordered_pages()` remains the single ordering rule for completion manifests and PDF creation. Every
structural mutation rewrites contiguous `position` values and removes `approved-guide.pdf` if it
exists. Moving an approved page does not revoke approval because its pixels did not change, but the
next export must rebuild the PDF in the new order.

Adding a page makes an otherwise complete session incomplete until the new activity is generated and
approved. Removing the only unapproved activity can make the session complete again. The completion
response is never cached on the client across a structural edit.

### Decision 9: Retain safe backward compatibility

Persisted sessions without `layout_revision` load with `0`. Their existing positions and activity
pages remain unchanged. The new panel derives availability from current server pages, so it also
works for older sessions that contain valid landmark metadata. If an old landmark lacks the private
context required to build a safe activity, its catalog entry is disabled with an explanation rather
than trusting client-supplied fallback data.

## Error And Empty States

- No tourist points: the panel explains that activities require a tourist point and links back to
  itinerary editing where possible.
- Point limit reached: cards remain visible but disabled with `2 de 2 atividades adicionadas`.
- Guide limit reached: all remaining add actions explain the eight-page limit.
- Duplicate: show `Já está no guia` and focus the existing page block.
- Layout conflict: refresh the authoritative session, announce that the order changed, and retain the
  panel state.
- Temporary network failure: rollback the optimistic block and offer retry; never generate artwork.
- In-progress removal: keep the page and explain that it can be removed after generation ends.

## Validation Strategy

### Backend

- Contract tests for strict add/move/delete payloads, ownership, expiry, unknown IDs, duplicate
  types, quotas, illegal anchors, and layout conflicts.
- Persistence tests for backward-compatible `layout_revision`, stable page IDs, contiguous
  positions, and immutable fixed-page relative order.
- Concurrency tests covering a move during another page's generation and refusal to remove the
  activity currently generating.
- Lifecycle tests proving removed attempt assets and cached PDFs are deleted without touching other
  session files.
- PDF tests proving approved pages use the exact new order after one or several moves.

### Frontend

- Component tests for opening/closing the panel, realistic preview modal, landmark selection,
  duplicate/quota states, add/remove, optimistic rollback, and generated-vs-ungenerated copy.
- Ordering tests for pointer drag, keyboard controls, mobile move controls, legal drop targets,
  page renumbering, live announcements, and preserved selected page.
- API tests for all new requests and structured errors.
- Tests proving browsing and adding never call the image-generation endpoint.

### Browser And Visual QA

- Desktop and mobile flows: add one activity, add to two landmarks, reorder, generate in parallel,
  approve, remove with confirmation, and export the resulting PDF.
- Keyboard-only and screen-reader-label checks for the panel and move controls.
- Visual review of all four full-page examples at card, modal, mobile, and dark-mode sizes.
- Inspect a reordered synthetic PDF page by page and compare it with the numbered UI outline.

## Delivery

Implementation is complete only after the full Python and frontend suites, Ruff, Mypy, ESLint,
production build, targeted browser tests, and PDF visual inspection pass. The implementation is then
committed and pushed to `main`; the frontend is built from that pushed commit and deployed to
`frontend-hostinger` using the repository's actual `hostinger-frontend` branch while preserving its
production configuration files.
