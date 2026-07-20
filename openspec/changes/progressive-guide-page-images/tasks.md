## 1. Contracts And Configuration

- [x] 1.1 Replace builder blocks with an ordered page-session model and immutable page attempts.
- [x] 1.2 Add OpenAI image model, quality, timeout, and page-attempt configuration with safe production validation.
- [x] 1.3 Define response models for page state, attempts, approval, and completed approved-page manifests.
- [x] 1.4 Add stable error codes for provider configuration, retryable generation failure, attempt exhaustion, and out-of-order actions.

## 2. OpenAI Page Generator

- [x] 2.1 Implement the OpenAI Image API client using the existing `OPENAI_API_KEY` without logging credentials.
- [x] 2.2 Implement complete cover-page editing with family-photo input, exact title/date copy, vertical size, and model-compatible input fidelity.
- [x] 2.3 Implement complete trip-summary generation with exact confirmed stop labels and vertical infographic composition.
- [x] 2.4 Validate returned base64, image format, dimensions, and bounded response size before persisting an attempt.
- [x] 2.5 Add prompt and transport unit tests using fake HTTP responses.

## 3. Session Lifecycle And Controls

- [x] 3.1 Persist page sessions atomically with owner ID, expiry, photo path, ordered page plan, attempts, and approval state.
- [x] 3.2 Reserve attempt capacity before calling the provider and prevent concurrent writes for one session.
- [x] 3.3 Add idempotency and expensive-request controls to page generation.
- [x] 3.4 Add cleanup and account-deletion support for session JSON, uploaded photos, and generated page images.
- [x] 3.5 Add tests for expiry, ownership, concurrency, attempt limits, retries, and deletion.

## 4. Page API

- [x] 4.1 Create an authenticated page-builder session without generating a PDF or image automatically.
- [x] 4.2 Add an endpoint to generate/regenerate one active page attempt.
- [x] 4.3 Add an endpoint to select an existing attempt.
- [x] 4.4 Add an endpoint to approve the selected attempt and advance the ordered workflow.
- [x] 4.5 Add an authenticated allowlisted PNG asset endpoint.
- [x] 4.6 Add a completion endpoint returning only the approved page manifest, with no PDF fields.

## 5. Progressive Frontend

- [x] 5.1 Replace automatic block bootstrapping with an explicit active-page state machine.
- [x] 5.2 Render the complete generated page at readable portrait scale with version thumbnails.
- [x] 5.3 Implement generate, regenerate, select, approve-and-continue, retry, and approved-gallery states.
- [x] 5.4 Remove the silent legacy generator fallback and all PDF actions from the active page workflow.
- [x] 5.5 Revoke authenticated object URLs and prevent stale selection races.
- [x] 5.6 Add frontend contract and behavior tests for the sequential workflow.

## 6. Verification

- [x] 6.1 Run the full Python suite, Ruff, format check, and Mypy.
- [x] 6.2 Run frontend tests, ESLint, production build, and bundle checks.
- [x] 6.3 Run a synthetic live OpenAI cover smoke at low quality and inspect its exact copy and dimensions.
- [x] 6.4 Run a local API/UI lifecycle with fake provider: cover generation, regeneration, approval, summary generation, approval, and completion.
- [x] 6.5 Review the final diff for secrets, user uploads, PDFs, runtime artifacts, and unrelated changes.

## 7. Delivery

- [x] 7.1 Commit the OpenSpec artifacts and implementation to `main` and push `origin/main`.
- [x] 7.2 Build the frontend from the pushed `main`, preserve Hostinger production configuration, and publish it to `hostinger-frontend`.
- [x] 7.3 Confirm both remote branch heads and report live-test limitations or required Render environment changes.

## 8. Directed Page Revisions

- [x] 8.1 Extend the attempt contract and persistence with a bounded normalized revision instruction while remaining compatible with existing sessions.
- [x] 8.2 Regenerate from the selected attempt through the Image edits endpoint, preserving original family input and mandatory copy/composition rules.
- [x] 8.3 Add the optional revision field, empty-field variation behavior, and clear retry states to the progressive UI.
- [x] 8.4 Add provider, API, frontend-contract, and browser lifecycle coverage for directed revisions.
- [x] 8.5 Run complete automated and synthetic live visual validation, then publish `main` and `hostinger-frontend`.
