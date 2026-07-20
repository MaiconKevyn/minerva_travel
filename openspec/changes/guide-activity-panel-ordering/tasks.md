## 1. Contracts And Example Assets

- [x] 1.1 Define strict add, move, and delete request/response contracts plus stable error codes and
  a backward-compatible `layout_revision` field.
- [x] 1.2 Extract one shared server helper that builds a safe activity page from a persisted canonical
  landmark context and the existing activity specification.
- [x] 1.3 Produce four synthetic realistic full-page examples through the representative generation
  and compositor pipeline, remove metadata, optimize them, and add descriptive alt/caption metadata.
- [x] 1.4 Add contract fixtures for old sessions, multiple destinations, custom tourist points,
  duplicate activities, quota limits, and pages with existing attempts.

## 2. Builder Structural Mutations

- [x] 2.1 Persist and expose `layout_revision=0` for old sessions without changing their page order.
- [x] 2.2 Implement owner-scoped activity creation with canonical landmark resolution, strict limits,
  a stable page ID, zero generation attempts, and default placement after the linked point.
- [x] 2.3 Implement activity movement by stable `after_page_id`, legal-anchor validation, immutable
  fixed-page relative order, and contiguous position rebuilding.
- [x] 2.4 Implement confirmed activity removal, block removal while that activity is generating, and
  delete only its private generated assets.
- [x] 2.5 Invalidate cached PDF/completion state after every structural edit while preserving existing
  attempts and approvals for unchanged pages.
- [x] 2.6 Serialize mutations with the session lock and layout-specific optimistic concurrency without
  blocking generation requests for other pages.

## 3. Builder API And Client

- [x] 3.1 Add authenticated POST activity, PATCH position, and DELETE activity endpoints returning the
  complete authoritative builder session.
- [x] 3.2 Map validation, ownership, conflict, quota, duplicate, and in-progress errors to structured
  bounded API responses.
- [x] 3.3 Add typed frontend request helpers that preserve structured errors and current abort behavior.
- [x] 3.4 Cover endpoint and client contracts, malformed payloads, stale layout revisions, owner
  isolation, and duplicate handling.

## 4. Final Activity Catalog Panel

- [x] 4.1 Add the `Adicionar atividades` entry point, responsive sheet, activity cards, realistic
  preview modal, age/time/material metadata, and clear `Exemplo` labeling to `GuideAssembly`.
- [x] 4.2 Add tourist-point selection plus available, already-added, per-point-limit, and guide-limit
  states without triggering image generation.
- [x] 4.3 Add server-authoritative creation plus optimistic removal with saving/error feedback,
  rollback, focus restoration, and destructive confirmation when generated assets exist.
- [x] 4.4 Keep the earlier activity-selection step compatible and make both surfaces use one catalog
  metadata source.

## 5. Accessible Guide Ordering

- [x] 5.1 Add an ordered block outline to the panel with fixed-page lock cues, activity drag handles,
  legal insertion targets, and resulting page numbers.
- [x] 5.2 Implement pointer drag placement plus `Inserir depois de`, move-up/down, keyboard, touch, and
  live-region alternatives.
- [x] 5.3 Save only the affected activity move, merge the authoritative returned session, rollback on
  failure, and keep the current page and unrelated generations active.
- [x] 5.4 Update completion/PDF UI after structural edits and clearly distinguish guide order from
  generation order.

## 6. Automated Verification

- [x] 6.1 Add backend unit/API/security/concurrency/lifecycle/PDF tests for add, move, remove, old
  sessions, legal boundaries, asset cleanup, and exact exported order.
- [x] 6.2 Add frontend catalog, API, responsive panel, accessibility, drag/move, optimistic rollback,
  and concurrent-generation tests.
- [x] 6.3 Run the full Python suite, Ruff, format check, and Mypy.
- [x] 6.4 Run frontend unit tests, ESLint, production build, and bundle-size checks.
- [x] 6.5 Run desktop, mobile, and keyboard browser flows; visually inspect all real examples and a
  reordered synthetic PDF.

## 7. Delivery

- [x] 7.1 Review the diff for credentials, private uploads, paid-test output, PDFs, runtime files, and
  unrelated user changes.
- [x] 7.2 Commit and push the implementation to `main` (`f3ba599`).
- [x] 7.3 Build from pushed `main`, preserve Hostinger production configuration, publish the actual
  `hostinger-frontend` branch, and confirm both remote heads.

Delivery record: static deployment `fe2ffdf` was built from implementation commit `f3ba599`; root
and `public_html` contain matching production config and activity preview assets.
