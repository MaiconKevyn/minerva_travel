## 1. Contracts And Fixtures

- [ ] 1.1 Define shared family-profile limits, strict parent/child request models, response models,
  optional creation revision, and stale-update error contract.
- [ ] 1.2 Define profile-to-guide normalization, approximate-age calculation, provenance, and manual
  override helpers without changing the existing generation payload's effective-age contract.
- [ ] 1.3 Add synthetic family fixtures with stable member IDs, boundary birth years, multiple
  responsible adults, and no real personal data.
- [ ] 1.4 Add failing contract tests for empty/oversized names, missing members, malformed JSON,
  duplicate IDs, invalid birth years, unknown fields, count overflow, and stale revisions.

## 2. Persistence And Supabase Migration

- [ ] 2.1 Add the `FamilyProfileRecord` aggregate and owner-scoped repository protocol with atomic
  create/read/replace/delete and optimistic revision behavior.
- [ ] 2.2 Add a forward-compatible SQLite `family_profiles` table and adapter for local development
  and hermetic tests.
- [ ] 2.3 Add a Supabase migration for the private one-row-per-owner profile table, Auth user cascade,
  constraints, timestamp trigger, explicit grants/revokes, forced RLS, and rollback guard.
- [ ] 2.4 Implement the production Supabase profile repository through server-only credentials;
  never add the service role or secret key to Vite/runtime frontend configuration.
- [ ] 2.5 Add pgTAP migration tests for table shape, constraints, grants, RLS, owner isolation posture,
  Auth cascade, and safe rollback.
- [ ] 2.6 Run Supabase Security and Performance Advisors after applying the migration in a safe
  non-production environment and resolve relevant findings.

## 3. Owner-Scoped API And Privacy Lifecycle

- [ ] 3.1 Add `GET /api/family-profile` returning a nullable profile with private no-store headers.
- [ ] 3.2 Add revisioned `PUT /api/family-profile` with atomic validation and a structured `409`
  conflict response.
- [ ] 3.3 Add idempotent `DELETE /api/family-profile` without affecting drafts or completed guides.
- [ ] 3.4 Include the profile in `GET /api/account/export` and purge it in
  `DELETE /api/account/data`.
- [ ] 3.5 Add safe observability events with no family names, member names, birth years, request
  bodies, or raw owner identifiers.
- [ ] 3.6 Add API tests for two-user isolation/BOLA, missing profile, concurrent update, no-cache
  headers, export allowlisting, account deletion, and repeated deletion.
- [ ] 3.7 Regenerate the checked-in OpenAPI contract and extend frontend contract verification.

## 4. Dashboard Family Profile Experience

- [ ] 4.1 Add frontend API functions for nullable read, revisioned save, and delete through the
  authenticated FastAPI client.
- [ ] 4.2 Add the `Minha família` dashboard card with independent loading, empty, loaded, error, and
  retry states so a profile failure never hides the guide library.
- [ ] 4.3 Build an accessible create/edit dialog or panel for family name, responsible adults, child
  names, and birth year using existing guide count/name limits.
- [ ] 4.4 Explain age estimation and the deliberate absence of stored family photos; show only the
  minimum useful profile summary while the editor is closed.
- [ ] 4.5 Add explicit save feedback, stale-revision recovery, and destructive profile-deletion
  confirmation.
- [ ] 4.6 Add `Criar guia com esta família` linking to the profile-prefill entry point while retaining
  a generic empty-guide path.
- [ ] 4.7 Cover dashboard profile states, validation, keyboard/focus behavior, mobile layout, and
  light/dark themes with component/browser tests.

## 5. Guide Bootstrap And Draft Conflict Resolution

- [ ] 5.1 Parse the profile-prefill launch intent inside the routed guide provider without trusting
  arbitrary client owner/profile IDs.
- [ ] 5.2 Refactor initialization into one bootstrap state machine that coordinates current-draft and
  optional profile reads before enabling autosave or rendering form steps.
- [ ] 5.3 With no active draft, copy the normalized profile and its source revision into fresh guide
  state and let the existing autosave create the new owner draft.
- [ ] 5.4 With an active draft, present `Continuar rascunho`, confirmed
  `Começar novo com minha família`, and `Cancelar` without merging states silently.
- [ ] 5.5 Delete the prior draft before applying profile defaults; preserve it and show retry on any
  deletion failure.
- [ ] 5.6 Keep the normal `/create` behavior and missing-profile behavior backward compatible.
- [ ] 5.7 Add race tests for slow profile/draft responses, unmount/abort, two tabs, autosave gating,
  stale draft revisions, and failed draft deletion.

## 6. Family Step, Ages, Review, And Activities

- [ ] 6.1 Copy profile parents/children with stable guide IDs, source member IDs, birth year, source
  revision, effective age, and `age_override` provenance into draft state.
- [ ] 6.2 Derive approximate ages from the selected trip year, recalculate only untouched derived
  ages, and require correction when the result is outside the guide's accepted age range.
- [ ] 6.3 Show `Dados carregados do perfil`, the birthday-boundary explanation, and the rule that
  guide edits do not update the saved profile.
- [ ] 6.4 Let the parent remove a non-travelling member or edit an age/name for this guide without
  mutating the dashboard profile.
- [ ] 6.5 Derive the expected visible family count from the guide snapshot while keeping the photo
  confirmation editable and requiring a fresh upload/consent.
- [ ] 6.6 Ensure review, generation, and the planned landmark-activity feature consume only effective
  guide ages and the immutable builder-session snapshot.
- [ ] 6.7 Add draft restore/backward-compatibility tests for old drafts without provenance and assert
  no photo path or consent is introduced by profile prefill.

## 7. Automated And Manual Verification

- [ ] 7.1 Run profile repository/API/security/account-lifecycle tests and the full Python suite.
- [ ] 7.2 Run Ruff, formatter verification, Mypy, frontend unit/contract tests, ESLint, production
  build, and bundle budget checks.
- [ ] 7.3 Run desktop and mobile end-to-end flows for profile create/edit/delete, fresh prefill,
  existing-draft choices, missing profile, revision conflict, and API recovery.
- [ ] 7.4 Verify keyboard-only use, focus restoration, screen-reader labels/live regions, responsive
  member editing, and destructive confirmations.
- [ ] 7.5 Verify an edited guide snapshot and a later profile edit cannot rewrite each other or alter
  an already-approved progressive page/PDF.
- [ ] 7.6 Review privacy and operational documentation for retained child fields, export, deletion,
  and the per-guide photo consent boundary.

## 8. Integration And Delivery

- [ ] 8.1 Land this change before `landmark-activity-pages`, then rebase the activity work onto the
  finalized guide bootstrap/family provenance model.
- [ ] 8.2 Reuse existing `.env` credentials without logging them; never stage runtime config, keys,
  real profile data, uploaded photos, generated PDFs, or `docs/Exploradores.pdf`.
- [ ] 8.3 Review the final diff for unrelated user changes, migration/rollback parity, OpenAPI drift,
  secrets, and production environment assumptions.
- [ ] 8.4 Commit and push the implementation to `main`, confirm the remote head, and build the
  frontend from pushed `main`.
- [ ] 8.5 Publish the verified static build to `hostinger-frontend`, preserve Hostinger runtime
  configuration, and confirm both remote branch heads plus the live profile-prefill flow.
