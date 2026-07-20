## 1. Contracts And Test Fixtures

- [x] 1.1 Define shared optional activity types, per-point limit, total-page limit, and strict
  request/response models.
- [x] 1.2 Add catalog/custom landmark activity-context fixtures, including a non-catalog point with
  no trusted curiosity or source image.
- [x] 1.3 Add representative committed preview assets for coloring, detail hunt, word search, and
  painting, clearly labeled as examples rather than generated output.
- [x] 1.4 Add failing contract tests for malformed JSON, unknown points, unselected points,
  duplicate types, unsupported types, and limit overflow.

## 2. Landmark Context And Content

- [x] 2.1 Preserve selection ID, name, city, country, description, curiosity fallback, `place_id`,
  source image metadata, and itinerary order when building progressive landmark contexts.
- [x] 2.2 Add optional landmark-specific curiosity data and a safe observation fallback that never
  invents a factual claim.
- [x] 2.3 Normalize bounded child-friendly description and curiosity copy into immutable landmark
  page metadata and `required_copy`.
- [x] 2.4 Extend landmark-page prompt and API tests for exact description/curiosity copy across first
  generation and directed revisions.

## 3. Frontend Activity Selection

- [x] 3.1 Add `landmarkActivitySelections` to guide context, draft save/restore/reset, and route-reset
  pruning.
- [x] 3.2 Add the dedicated activity step after family details and update step navigation/progress for
  known and suggested itinerary modes.
- [x] 3.3 Render one accessible point section with visual activity cards, age/time/material metadata,
  selected state, page-count feedback, and an explicit no-optional-activities path.
- [x] 3.4 Enforce shared per-point and total limits without losing prior valid choices.
- [x] 3.5 Show point-to-activity mappings and the mandatory `Minha melhor memória` page in final
  review.
- [x] 3.6 Serialize normalized selections as bounded `activity_selections_json` form data and cover
  draft/API contracts with frontend tests.

## 4. Builder Page Plan And Persistence

- [x] 4.1 Parse and validate activity selections only against server-resolved selected landmarks.
- [x] 4.2 Include normalized activities in idempotency hashing and the private builder-session form
  snapshot.
- [x] 4.3 Insert optional `landmark_activity` pages immediately after their linked point in stable
  order.
- [x] 4.4 Append exactly one mandatory `best_memory` page after all point content for every new
  session.
- [x] 4.5 Keep existing saved sessions backward compatible and include all new assets in expiry,
  account deletion, allowlisting, and PDF cleanup.
- [x] 4.6 Add page-plan and persistence tests for zero activities, multiple points/types, custom
  points, old sessions, and limit boundaries.

## 5. OpenAI Activity Page Generation

- [x] 5.1 Extend the page-generator protocol and fake generator with explicit coloring, detail-hunt,
  word-search, drawing, and best-memory methods.
- [x] 5.2 Resolve available landmark attempts and sanitized local landmark references in a fixed,
  owner-safe order without accepting client paths or external URLs.
- [x] 5.3 Implement coloring through OpenAI image edits, strict people/text removal prompts, and the
  existing line-art simplification pipeline.
- [x] 5.4 Implement detail-hunt visual generation with validated landmark-specific clues and exact
  composited checkboxes/copy.
- [x] 5.5 Reuse the seeded word-search generator and composite its exact grid/word list over an
  OpenAI-generated landmark activity background.
- [x] 5.6 Implement the backward-compatible `drawing` page as a painting activity with a measurable blank canvas and exact
  composited prompt.
- [x] 5.7 Implement mandatory best-memory generation with blank response areas, trip context, age
  adaptation, and edit-based revisions.
- [x] 5.8 Add activity-specific output validation, atomic persistence, error normalization, and
  provider prompt/transport tests.

## 6. Progressive Review And PDF

- [x] 6.1 Dispatch new page kinds through the existing reservation, idempotency, attempt, selection,
  approval, and retry state machine.
- [x] 6.2 Ensure family references and `Incluir família` remain restricted to their existing page
  kinds and never leak into activity or memory requests.
- [x] 6.3 Add activity badges, linked-point context, instructions, and suitable previews to
  `GuideAssembly` while preserving directed regeneration.
- [x] 6.4 Recalculate expensive-request quotas for the bounded expanded page plan.
- [x] 6.5 Prove completion and PDF export require every selected activity and the memory page, then
  preserve exact approved sequence with one image per PDF page.

## 7. Automated Verification

- [x] 7.1 Run backend activity/page-plan/API/security/deletion/PDF tests, the full Python suite,
  Ruff, formatting, and Mypy.
- [x] 7.2 Run frontend unit/contract tests, ESLint, production build, and bundle budget checks.
- [x] 7.3 Run desktop/mobile browser flows for no optional activities, multiple point-bound
  activities, generation failure/retry, draft restore, mandatory memory approval, and PDF download.
- [x] 7.4 Render a mixed synthetic PDF and inspect every page for order, full-page coverage,
  readability, writing space, and coloring usability.

## 8. Live Validation And Delivery

- [x] 8.1 Using the existing `.env` credentials without logging them, generate one low-quality
  coloring page for a custom non-catalog point and inspect place fidelity, line quality, and absence
  of people/text.
- [x] 8.2 Generate one additional writable activity page and inspect exact copy, point identity, and
  blank response space.
- [x] 8.3 Review the final diff for secrets, user PDFs/uploads, paid-test artifacts, runtime files,
  and unrelated changes.
- [x] 8.4 Commit and push the implementation to `main`, build from pushed `main`, preserve Hostinger
  production configuration, and publish `hostinger-frontend`.
- [x] 8.5 Confirm both remote branch heads and record delivery completion in this change.

### Delivery record

- `main` implementation: `6bb3c05` (`Implement landmark activity pages`).
- `hostinger-frontend` static deployment: `731b24a` (`Deploy landmark activity pages`).
- Remote branch heads were confirmed after both pushes on 2026-07-20.
- Production `config.js` and `.htaccess` were preserved in both the root and `public_html` copy.

## 9. Child-Friendly Coloring Worksheet Refinement

- [x] 9.1 Add the exact server-derived coloring instruction contract for every tourist point and
  include it in builder `required_copy`.
- [x] 9.2 Add age-aware OpenAI line-art constraints, a bounded illustration layout, and stronger
  printable white-space validation.
- [x] 9.3 Update the visual frontend example and automated prompt/compositor/page-plan tests.
- [x] 9.4 Run backend/frontend verification, visually inspect a synthetic coloring page, and review
  the final implementation diff.

## 10. Mandatory Homecoming Closing Page

- [x] 10.1 Define exact closing copy, writable-area geometry, a `homecoming` page kind, and the
  deterministic position after `best_memory`.
- [x] 10.2 Implement family-photo/approved-cover OpenAI editing, identity-preserving airport artwork,
  directed regeneration, exact trusted-code compositing, and output validation.
- [x] 10.3 Integrate the mandatory page with builder review, completion, PDF export, lifecycle rules,
  frontend labels, and final-page explanations.
- [x] 10.4 Add page-plan, API, provider, compositor, frontend contract, backward-compatibility, and
  PDF sequence tests.
- [x] 10.5 Run full backend/frontend verification, inspect synthetic and live rendered pages, and
  review the final implementation scope.

## 11. Approval-Independent Activity Generation And Temporary-Limit Retry

- [x] 11.1 Remove the approved-landmark dependency from activity dispatch while preserving
  owner-safe reference resolution and immutable page order.
- [x] 11.2 Fall back to prompt-only OpenAI generation when neither a local point image nor a
  generated landmark attempt exists.
- [x] 11.3 Preserve structured `Retry-After` metadata in the frontend and retry temporary request
  control failures with the same idempotency key, bounded attempts, and visible waiting state.
- [x] 11.4 Exclude daily quotas and permanent errors from automatic retries, allow other pages to
  keep generating in parallel, and cancel pending timers on component unmount.
- [x] 11.5 Add backend and frontend regression tests, run full validation, and publish both target
  branches.

### Approval-independent generation delivery record

- `main` implementation: `7b222df` (`Fix activity generation and temporary retries`).
- `hostinger-frontend` static deployment: `a0be40d` (`Deploy activity generation retries`).
- Remote branch heads, production `config.js`, and `.htaccess` copies were confirmed on 2026-07-20.

## 12. Replace Free Drawing With `Minha pintura`

- [x] 12.1 Keep the persisted `drawing` identifier for compatibility while replacing all visible
  selection and generated-page copy with the `Minha pintura` experience.
- [x] 12.2 Update the OpenAI artwork contract and trusted compositor for a painting-themed frame,
  point-specific instruction, blank white canvas, painting title, and date fields.
- [x] 12.3 Replace the drawing preview with an accessible painting preview and clearly distinguish
  blank-canvas painting from the ready-to-color activity.
- [x] 12.4 Run backend/frontend regression tests, inspect the preview/build, and publish both target
  branches.

### `Minha pintura` delivery record

- `main` implementation: `cbca3fc` (`Replace drawing activity with painting`).
- `hostinger-frontend` static deployment: `2fdc2b8` (`Deploy painting activity`).
- Preview, composed worksheet, remote heads, production `config.js`, and `.htaccess` copies were
  confirmed on 2026-07-20.
