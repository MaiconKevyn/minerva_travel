# Supabase database artifacts

This directory contains the versioned DATA-01 and STO-01 database contract.
Migrations are intentionally independent from the local SQLite adapter.

## Apply in a temporary local Supabase database

Prerequisites: Docker, the Supabase CLI, `psql`, and `rg`. If this checkout does
not yet have `supabase/config.toml`, initialize the local CLI configuration once;
the CLI preserves the versioned migrations:

```bash
test -f supabase/config.toml || supabase init
supabase start
bash scripts/check_supabase_migrations.sh
supabase db reset
supabase db lint --level error
supabase test db
```

`supabase db reset` recreates the local database and applies files from
`supabase/migrations` in timestamp order. `supabase test db` runs the pgTAP
catalog checks in `supabase/tests` and verifies tables, versions, forced RLS,
owner/support/service policies, private buckets, storage policies, triggers and
enums.

The canonical object key is:

```text
<user_id>/<guide_job_id>/<non-enumerable-file-name>
```

Authenticated clients may upload, update or delete only `family-uploads`.
Generated covers, PDFs and landmark assets are written and deleted by the
trusted server so database/object cleanup remains coordinated. Owners can read
only paths under their own UUID. Support users are read-only and must receive
`app_metadata.role = support` (or `admin`) through a trusted admin flow; never
use user-editable metadata for authorization. Storage support access is further
limited to generated covers and guides, excluding raw family uploads.

Supabase `service_role` bypasses RLS by design. Its explicit policies and grants
in these migrations document intended server access, but the service credential
must remain server-only and is not protected by those policy expressions.

## Exercise rollback in the temporary database

Run rollback files in reverse migration order:

```bash
database_url='postgresql://postgres:postgres@127.0.0.1:54322/postgres'
psql "$database_url" -v ON_ERROR_STOP=1 \
  -f supabase/rollbacks/202607090002_sto01_private_buckets.down.sql
psql "$database_url" -v ON_ERROR_STOP=1 \
  -f supabase/rollbacks/202607090001_data01_core.down.sql
psql "$database_url" -Atc "select to_regclass('public.guides') is null"
supabase stop --no-backup
```

Expected output for the final query is `t`. The core rollback refuses to drop
non-empty application tables. The storage rollback restores prior bucket
configuration, removes only buckets created by the migration, and refuses to
remove a newly created bucket that still has objects. Objects must be removed
through the Storage API, never by deleting rows directly from `storage.objects`.

## Deployment order

1. Apply both migrations to an empty staging branch.
2. Run database lint and pgTAP tests.
3. Exercise application reads/writes with two distinct users and a support JWT.
4. Verify signed downloads from every private bucket.
5. Apply migrations before deploying API/worker code that depends on them.
6. Keep rollback exports and bucket inventory with the release evidence.
