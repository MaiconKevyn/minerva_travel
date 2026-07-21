## Persistence Model

The authenticated draft remains the canonical cross-device checkpoint. Its payload gains a schema
version and an optional `builder_session_id`. Existing drafts remain valid because missing fields
normalize to their safe defaults.

The browser stores a small JSON checkpoint under a key scoped by the authenticated user ID. This
checkpoint contains only the same serializable wizard payload as the draft, plus `updated_at` and a
schema version. It never contains `File`, object URLs, raw photo bytes, access tokens or photo
consent. Browser persistence closes the debounce/unload window; the next successful API save makes
the server copy available on other devices.

At startup the application waits for authentication, reads both sources and chooses the newest
valid payload. If the local payload is newer, it is subsequently uploaded using the current server
draft revision. Malformed, differently versioned or differently owned browser data is ignored.

## Addressable Builder Session

After `POST /api/guide-builder` succeeds, the returned stable identifier is checkpointed in three
places before the builder is displayed:

1. React guide state;
2. the owner-scoped browser checkpoint;
3. the `builder` query parameter on `/create`.

The normal draft autosave then copies it to the authenticated server draft. The URL makes an
immediate reload safe even before that network save finishes, while the draft enables cross-device
resume. The identifier never grants access by itself: `GET /api/guide-builder/{session_id}` still
requires the owning user.

## Restoration Flow

The create page does not render an empty wizard while hydration is pending. After hydration, a
saved builder identifier forces the final wizard step and `Step5Review` fetches the latest session.
`GuideAssembly` receives exactly the same response contract used after initial creation, so page
order, attempts, selected versions, approvals and provider retry state remain server-authoritative.

A `404` means that the owner-scoped session no longer exists, normally because it expired or was
deleted. The stale identifier is removed from React state, browser checkpoint and URL, while the
form draft remains available so the family can upload the photo and start a new builder. Temporary
network failures retain the identifier and offer an explicit retry action.

## Save Coordination

Every state change writes synchronously to browser storage after initial hydration. Server writes
remain debounced to avoid request amplification. A queued-save loop ensures changes made while a
save is in flight trigger another save with the latest payload and latest optimistic revision,
instead of being silently skipped.

Discard removes the authenticated draft, owner-scoped browser checkpoint and builder query
parameter, then resets wizard state. It does not delete an existing builder session because the
current discard action historically only owns the draft; server expiry/account deletion continue
to govern private builder assets.

## Validation

- Unit tests cover owner-scoped keys, invalid snapshots, timestamp reconciliation and URL parsing.
- Browser tests reload a final-step draft with a builder identifier and assert that the server
  session and generated image are restored without creating a new builder.
- Browser tests cover an expired builder session and verify that form data remains available.
- Existing API, frontend, lint, build and progressive-guide suites must remain green.
