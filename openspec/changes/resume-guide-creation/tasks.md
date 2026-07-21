## 1. Contracts And Checkpoints

- [x] 1.1 Add a versioned, owner-scoped browser checkpoint helper with newest-source reconciliation.
- [x] 1.2 Add `builder_session_id` and schema metadata to the existing authenticated draft payload.
- [x] 1.3 Prevent an empty wizard from rendering before authentication and draft hydration complete.

## 2. Builder Restoration

- [x] 2.1 Checkpoint the builder identifier locally and in the `/create` URL after session creation.
- [x] 2.2 Fetch and display the persisted owner session automatically on reload.
- [x] 2.3 Preserve the draft while clearing an expired session, and retain retryable failures.

## 3. Save Reliability

- [x] 3.1 Queue changes that occur during an authenticated draft save.
- [x] 3.2 Clear local and addressable checkpoints when the draft is discarded.

## 4. Verification

- [x] 4.1 Add unit tests for checkpoint parsing and reconciliation.
- [x] 4.2 Add Playwright coverage for reload restoration and expired-session recovery.
- [x] 4.3 Run frontend tests, ESLint, production build, bundle checks and Playwright.
- [x] 4.4 Run Python tests, Ruff, formatting and Mypy.

## 5. Delivery

- [x] 5.1 Review for credentials, photo bytes, generated runtime files and unrelated user changes.
- [ ] 5.2 Commit and push to `main`.
- [ ] 5.3 Build committed `main`, publish `hostinger-frontend` and confirm both remote heads.
