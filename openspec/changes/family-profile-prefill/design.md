## Context

The frontend authenticates with Supabase Auth and sends the resulting bearer token to FastAPI for
application data. `DashboardPage` already renders account information, a guide library, and a
generic `Novo Guia` action. `ConversationalGuideProvider` always attempts to restore the latest
active owner draft when `/create` mounts. That draft stores family name, responsible-adult names,
child names and ages, but expires and deliberately excludes photo bytes and photo consent.

The family step currently represents adults as names and children as `{id, name, age}`. The trip
year belongs to the guide. A reusable literal age would become stale, while a full birth date would
collect more child data than this product needs. The profile therefore stores only birth year and
derives an editable approximate trip age.

Production database migrations target Supabase Postgres; the hermetic local/test adapter is
SQLite. Existing browser application data goes through FastAPI, and that boundary remains intact.
Supabase Auth user metadata remains suitable for the account display name but is not the durable
family-profile store.

## Goals / Non-Goals

**Goals:**

- Let a returning parent start a guide from the dashboard without retyping family details.
- Make saving, using, editing, and deleting the profile explicit and understandable.
- Keep family data owner-scoped and minimize stored information about children.
- Never destroy or merge an existing draft without an explicit parent choice.
- Keep profile state, a guide draft, and a completed guide as separate versioned snapshots.
- Preserve the current photo re-upload and consent boundary for every guide.

**Non-Goals:**

- A household invitation, co-parent sharing, or multiple-family account model.
- A reusable family-image asset library.
- Exact birthday-aware age calculation.
- Automatic backfill from completed-guide metadata.
- Direct browser access to family-profile tables.

## Proposed User Journey

1. The signed-in parent opens the dashboard.
2. A `Minha família` card shows one of three states:
   - no profile: `Cadastrar família`;
   - saved profile: family name, adult/child count, `Editar` and
     `Criar guia com esta família`;
   - load failure: a retry action without hiding the existing guide library.
3. The profile editor collects family name, one or more responsible adults, and one or more
   children with name and birth year. It explains that the year is used only to estimate age for a
   future trip and that no photo is stored.
4. `Criar guia com esta família` navigates to
   `/create?prefill=family-profile`.
5. If there is no meaningful active draft, the wizard copies the profile into fresh guide state,
   derives child ages for the current trip year, and autosaves a new draft through the existing
   mechanism.
6. If an active draft exists, a blocking dialog offers:
   - `Continuar rascunho`, which ignores the profile launch and restores it unchanged;
   - `Começar novo com minha família`, which confirms and deletes the active draft before applying
     the profile snapshot;
   - `Cancelar`, which returns to the dashboard.
7. The family step shows `Dados carregados do perfil` and explains that edits apply only to this
   guide. The parent can remove a non-travelling member or correct an estimated age.
8. The photo step still requires a new file and a new processing consent. The expected visible
   family-member count is derived from the guide's included members and remains editable.

## Decisions

### Decision 1: One explicit, private profile per authenticated owner

The initial product has one `family_profiles` row for each Supabase Auth user. A single bounded
aggregate matches how the guide consumes the data and avoids premature household sharing rules.
The Postgres shape is:

```text
family_profiles
  user_id uuid primary key -> auth.users(id) on delete cascade
  family_name text
  parents jsonb array<{id, name}>
  children jsonb array<{id, name, birth_year}>
  revision integer
  schema_version integer
  created_at timestamptz
  updated_at timestamptz
```

The API enforces the existing maximum responsible-adult and child counts, stable opaque member IDs,
trimmed bounded names, unique IDs per profile, non-empty arrays, and a reasonable birth-year range.
Database checks enforce JSON array types, positive revision/schema versions, family-name length, and
payload byte/element limits. The profile is small and always read/written as a unit, so JSONB keeps
an update atomic while stable member IDs still support predictable React rendering.

No email, photo path, exact birth date, destination, itinerary, activity selection, trip year, or
provider data is duplicated into this table.

### Decision 2: Store birth year, then derive an editable guide age

For a profile-sourced child:

```text
estimated_age = trip_year - birth_year
```

The result must remain in the accepted child age range. The UI labels it as an estimate and allows
the parent to correct it. A child record copied into the draft keeps `profile_member_id` and
`birth_year` as provenance plus the effective `age`; generated-guide requests continue consuming
the existing effective-age contract.

When the trip year changes, untouched profile-derived ages are recalculated. As soon as the parent
edits an age, that guide record becomes an override and later trip-year changes do not silently
replace it. These provenance fields are private draft state, not model prompt text.

This is precise enough for age-band activities while avoiding an exact date of birth. The UI warns
that travel near a birthday can require a one-year correction.

### Decision 3: Keep the FastAPI application-data boundary

The browser does not query `family_profiles` directly. It uses authenticated endpoints:

```text
GET    /api/family-profile
PUT    /api/family-profile
DELETE /api/family-profile
```

`GET` returns `{ "profile": null }` when no profile exists. `PUT` is a strict create-or-replace
aggregate request. Creation sends no revision; an update sends the last observed positive revision.
A stale update returns `409 family_profile_revision_conflict` with the current revision and never
applies a partial member list. `DELETE` is idempotent and returns the common deletion response.

Every handler derives `user_id` from `CurrentUser`; the client never chooses an owner. Responses
containing profile data use `Cache-Control: private, no-store, max-age=0`, `Pragma: no-cache`, and
`X-Content-Type-Options: nosniff`.

The repository abstraction gains an owner-scoped profile aggregate. SQLite implements the same
contract for local development and tests. The production adapter uses the existing server-only
Supabase credentials; no `service_role` or secret key is added to frontend configuration.

### Decision 4: Make Supabase exposure explicit and least-privileged

The migration adds the table, update timestamp trigger, index/primary key, rollback guard, and
pgTAP tests. It explicitly revokes access from `anon` and `authenticated` because browser reads and
writes go through FastAPI, and grants only the operations required by the server role. RLS is
enabled and forced as defense in depth, with no public/support projection of child names.

This follows Supabase's guidance to keep API-accessible user data in an application table that
references `auth.users(id) on delete cascade`, instead of trying to expose the Auth schema. It also
accounts for the 2026 Data API default change: migrations must declare grants explicitly rather
than relying on automatic table exposure.

If implementation chooses to allow owner-token Data API access in a later release, it must first
add explicit `TO authenticated` owner `SELECT`, `INSERT`, `UPDATE`, and `DELETE` policies. An update
policy must contain both `USING` and `WITH CHECK` and must be accompanied by a select policy.

### Decision 5: Snapshot profile data into a guide; never live-link it

Starting a guide copies normalized family values and the source profile revision into the draft.
The draft records `family_profile_source_revision` for traceability, but its member list is
independent after bootstrap.

- Editing or deleting the profile never changes an active draft or old guide.
- Removing a member from one guide never removes that member from the profile.
- Regeneration and progressive page creation use only the builder session's immutable family
  snapshot.
- Guide generation never fetches the current profile to fill missing values.

This prevents a late profile edit from changing the cover, activity age bands, family count, or PDF
after the parent already reviewed a guide.

### Decision 6: Coordinate draft and profile bootstrap before rendering the wizard

`ConversationalGuideProvider` currently restores a draft as soon as it mounts. The new bootstrap
loads the latest draft and, only when the query parameter requests it, the family profile before
allowing autosave or rendering an editable wizard step.

The bootstrap state machine is explicit:

```text
loading -> normal draft restore
loading -> fresh profile prefill
loading -> draft/profile conflict choice
loading -> empty normal wizard
error   -> retry or return to dashboard
```

Autosave remains disabled until bootstrap finishes. This prevents a default empty state or profile
prefill from racing with draft restoration. The profile action does not silently merge itinerary
data from the draft with family data from the profile.

Only one active draft is surfaced today. `Começar novo` therefore calls the existing owner-scoped
draft deletion first and applies the profile only after deletion succeeds. A deletion error keeps
the original draft intact and displays a retryable error.

### Decision 7: Separate profile management from one-guide edits

The dashboard is the authoritative profile editor. The guide family step includes a link back to
profile management, but it does not autosave changes to the profile. This avoids turning a temporary
traveling subset or one corrected age into an accidental household change.

A future explicit `Atualizar meu perfil com estes dados` action can reuse the revisioned API, but it
is not required for the first release. Existing accounts and existing drafts are not backfilled.

### Decision 8: Preserve the photo and consent boundary

The reusable profile stores no image. The dashboard card must not imply that a family photo has
been saved. Every new guide still requires:

- a fresh family-photo upload;
- explicit photo-processing consent for that generation;
- the expected visible-member count confirmation.

No prior upload path, generated cover, consent timestamp, or model reference is copied from a
profile or old guide. This preserves the current draft message and avoids expanding photo retention
without a separate privacy decision.

### Decision 9: Include the profile in privacy lifecycle operations

The account export adds a `family_profile` object containing only the user-facing profile fields,
revision, and timestamps. It does not expose internal database identifiers beyond the stable member
IDs already needed to represent the profile.

`DELETE /api/account/data` purges the profile in the same owner-scoped operation as drafts, jobs,
guides, and assets. Deleting the Supabase Auth user also cascades the Postgres row. Profile deletion
alone does not delete guides or drafts, because they are independent snapshots.

Observability records event names and hashed user identifiers only. Logs, audit metadata, error
messages, and analytics must not include family names, member names, birth years, or request bodies.

### Decision 10: Integrate cleanly with landmark activities

The `landmark-activity-pages` change already consumes effective child ages from guide state. This
change supplies those same ages after prefill; it does not add a second activity-specific profile
field. The activity selection and generated page plan remain per-guide data.

Both changes touch `ConversationalGuideContext`, the family step, draft contracts, review, and
OpenAPI tests. To reduce merge risk, implement and land `family-profile-prefill` first, then rebase
the activity change and add its new step on top of the finalized bootstrap model.

## Failure And Edge Cases

- **No saved profile:** the dashboard offers registration and generic guide creation still works.
- **Profile deleted in another tab:** the profile launch shows an owner-safe not-found state and
  allows an empty guide; it never uses stale browser storage.
- **Concurrent profile edits:** the stale writer gets a revision conflict and must reload/merge
  deliberately.
- **Existing draft:** no destructive action happens until the parent chooses and confirms it.
- **Expired draft:** it is treated as absent and profile prefill proceeds.
- **Invalid derived age:** the child remains visible with a validation prompt; the wizard cannot
  progress until the parent corrects it.
- **Trip-year change:** only untouched derived ages recalculate.
- **Member not travelling:** removing the member affects only the guide snapshot.
- **Profile API unavailable:** the guide library remains usable, the card shows retry, and the
  profile-aware launch does not fall back to potentially stale local data.
- **Missing production migration:** API readiness/health exposes a safe persistence error; the
  frontend does not treat an absent table as an empty profile.

## Validation Strategy

### Contract and unit validation

- Strict FastAPI and frontend tests for valid create/read/update/delete, all field/count bounds,
  malformed JSON members, duplicate IDs, birth-year limits, and unknown fields.
- Repository tests for atomic replace, revision conflicts, owner isolation, export, deletion, and
  SQLite schema upgrades.
- Age tests for current/future trip years, 17/18 boundaries, birthday warning, manual overrides,
  and recomputation after trip-year changes.

### Database and security validation

- Migration/rollback tests and pgTAP assertions for primary-key ownership, Auth cascade, explicit
  grants, forced RLS, and lack of `anon`/`authenticated` direct access.
- Two-user BOLA tests for every API method, including attempts to reuse another owner's member IDs
  or revision.
- Supabase Security and Performance Advisor checks after applying the migration to a non-production
  branch or local Supabase database.
- Secret scan proving the service role remains backend-only.

### Frontend and browser validation

- Dashboard states: missing, loaded, saved, updating, deleting, conflict, and retryable error.
- Keyboard, focus, labels, error announcement, mobile layout, light/dark theme, and destructive
  confirmation checks.
- End-to-end profile launch with no draft, with a draft continued, and with a draft explicitly
  discarded.
- Assert profile data appears in the family step, effective ages reach review/activity state, and
  no family photo is preloaded.
- Assert one-guide member/age edits leave the dashboard profile unchanged.

### Delivery validation

- Run backend tests, Ruff, formatting, Mypy, frontend unit/contract tests, ESLint, production build,
  OpenAPI snapshot verification, and desktop/mobile browser smoke tests.
- Review the diff for credentials, child data fixtures that resemble real people, local runtime
  data, PDFs, uploads, and unrelated user files.
- Commit and push implementation to `main`, build from pushed `main`, and publish the static build
  to `hostinger-frontend` using the existing environment credentials without printing them.

## References

- [Supabase User Management](https://supabase.com/docs/guides/auth/managing-user-data)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase 2026 Data API grant change](https://supabase.com/changelog/45329-breaking-change-tables-not-exposed-to-data-and-graphql-api-automatically)

