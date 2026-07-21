## Why

The guide wizard already saves most form fields in an authenticated draft and the progressive
builder already persists generated page attempts. However, the builder session identifier exists
only in React state. Reloading the browser therefore returns a family to the review screen without
the generated pages, and the debounced draft save can miss the last edits made immediately before a
reload.

## What Changes

- Save a versioned, owner-scoped browser checkpoint immediately after every meaningful wizard
  change, excluding photo bytes and consent.
- Continue saving the canonical draft through the authenticated API, while reconciling the newest
  local or server checkpoint on startup.
- Persist the progressive builder `session_id` in the draft and in the `/create` URL after the
  session is created.
- Reopen the owner-scoped builder session automatically on reload, including generated, selected,
  approved and in-progress page states.
- Show an explicit restoration state instead of briefly presenting an empty first step.
- Recover gracefully when a saved builder session has expired or is unavailable.

## Impact

- Conversational guide state hydration and autosave.
- Step 6/6 review and progressive builder restoration.
- Browser-storage helpers, frontend unit tests and Playwright coverage.

## Non-Goals

- Storing the uploaded family photo in `localStorage` or in the draft JSON.
- Extending the existing builder-session retention period.
- Replacing owner authorization on draft, session or asset endpoints.
