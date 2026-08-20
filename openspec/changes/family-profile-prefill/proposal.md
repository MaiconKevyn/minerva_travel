## Why

The authenticated dashboard currently knows only the account name and email. Family names,
responsible adults, and children are kept only inside a short-lived guide draft or an immutable
generated-guide snapshot. As a result, a returning parent must type the same family information
again for every new trip.

A family profile should be a reusable, private source of defaults. Starting a guide from that
profile must save time without silently replacing an existing draft, changing old guides, or
turning sensitive family data and photos into broadly reusable account metadata.

## What Changes

- Add a private `Minha família` card and editor to the authenticated dashboard.
- Store a reusable family name, responsible-adult names, and child names with birth year.
- Do not store an exact birth date, family photo, photo-processing consent, destinations, trip
  year, tourist points, or guide extras in the reusable profile.
- Add a profile-aware `Criar guia com esta família` action that starts the wizard with family
  fields prefilled.
- Calculate each child's approximate age for the selected trip year and let the parent correct it
  for that guide without changing the saved profile.
- Treat the prefilled values as a snapshot: profile edits do not rewrite active drafts or completed
  guides, and guide edits do not update the profile automatically.
- Resolve an existing-draft conflict explicitly by letting the parent continue the draft or discard
  it and start a fresh guide with the saved family.
- Add owner-scoped API, persistence, Supabase migration/RLS, account export, account deletion, and
  local-development support for family profiles.
- Keep the normal `/create` entry point backward compatible when no family profile exists or the
  user did not launch from the profile action.

## Capabilities

### New Capabilities

- `family-profile-management`: Authenticated parents can create, view, edit, and delete one private
  reusable family profile.
- `family-profile-guide-prefill`: A profile-aware guide launch copies reusable family defaults into
  a new guide session while preserving draft and per-guide boundaries.

### Modified Capabilities

- `guide-creation-flow`: The dashboard can launch a profile-prefilled guide and the family step can
  explain and edit the copied values.
- `guide-draft-persistence`: Guide bootstrap distinguishes restoring the current draft from starting
  a fresh profile-prefilled draft.
- `account-privacy`: Family profile data is included in owner export/deletion and excluded from
  logs, public metadata, and photo persistence.

## Impact

- Dashboard layout, loading/error states, family editor, and create-guide calls to action.
- Guide context bootstrap, draft conflict UI, family-step provenance, age calculation, and review.
- FastAPI family-profile contracts and the frontend OpenAPI snapshot/client.
- SQLite development/test persistence and Supabase Postgres migration, grants, RLS, rollback, and
  pgTAP coverage.
- Account export/deletion and privacy documentation for stored child data.
- The planned activity feature can consume the same computed child ages; it does not need a second
  family-profile contract.

## Non-Goals

- Automatically extracting or saving a family profile from existing guides or expired drafts.
- Automatically updating the saved profile when the parent edits one guide.
- Persisting a reusable family photo or reusing old photo-processing consent.
- Supporting multiple named households per account in the first release.
- Sharing one family profile between separate Supabase accounts.
- Changing previously generated guides when a family profile changes.

