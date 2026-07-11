#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
core="$repo_root/supabase/migrations/202607090001_data01_core.sql"
storage="$repo_root/supabase/migrations/202607090002_sto01_private_buckets.sql"
core_down="$repo_root/supabase/rollbacks/202607090001_data01_core.down.sql"
storage_down="$repo_root/supabase/rollbacks/202607090002_sto01_private_buckets.down.sql"
db_test="$repo_root/supabase/tests/202607090001_data01_storage_test.sql"

for required_file in "$core" "$storage" "$core_down" "$storage_down" "$db_test"; do
    test -f "$required_file"
done

tables=(
    guide_drafts
    guide_jobs
    guides
    guide_assets
    payments
    entitlements
    usage_events
    audit_events
)

for table in "${tables[@]}"; do
    rg --quiet --fixed-strings "create table public.$table" "$core"
    rg --quiet --fixed-strings "alter table public.$table enable row level security;" "$core"
    rg --quiet --fixed-strings "minerva_${table}_owner_read" "$core"
    rg --quiet --fixed-strings "minerva_${table}_service_all" "$core"
    rg --quiet --fixed-strings "drop table if exists public.$table;" "$core_down"
done

if rg --quiet --glob '*.sql' 'minerva_.*_support_read' "$core"; then
    echo "Support must use the redacted RPC, not raw DATA-01 table policies." >&2
    exit 1
fi

buckets=(family-uploads generated-covers generated-guides landmark-assets)
for bucket in "${buckets[@]}"; do
    rg --quiet --fixed-strings "'$bucket'" "$storage"
done

if rg --quiet --ignore-case 'public[[:space:]]*=[[:space:]]*true' "$storage"; then
    echo "A managed storage bucket is public." >&2
    exit 1
fi

rg --quiet --fixed-strings "app_private.is_support()" "$core"
rg --quiet --fixed-strings "app_private.owns_registered_asset" "$core"
rg --quiet --fixed-strings "app_private.owns_registered_asset" "$storage"
rg --quiet --fixed-strings "app_private.support_can_read_registered_asset" "$core"
rg --quiet --fixed-strings "app_private.support_can_read_registered_asset" "$storage"
rg --quiet --fixed-strings "app_private.can_upload_family_asset" "$core"
rg --quiet --fixed-strings "app_private.can_upload_family_asset" "$storage"
rg --quiet --fixed-strings "public.support_guide_operations" "$core"
rg --quiet --fixed-strings "(storage.foldername(name))[1]" "$storage"
rg --quiet --fixed-strings "coalesce(array_length(storage.foldername(name), 1), 0) = 2" "$storage"
rg --quiet --fixed-strings "create schema app_private;" "$core"
rg --quiet --fixed-strings "guide_assets_canonical_path" "$core"
rg --quiet --fixed-strings "guide_assets_one_active_family_per_job_uidx" "$core"
rg --quiet --fixed-strings "foreign key (draft_id, user_id)" "$core"
rg --quiet --fixed-strings "foreign key (guide_job_id, user_id)" "$core"
rg --quiet --fixed-strings "foreign key (guide_id, user_id)" "$core"
rg --quiet --fixed-strings "previous_name text" "$storage"
rg --quiet --fixed-strings "name = state.previous_name" "$storage_down"
rg --quiet --fixed-strings "drop schema app_private restrict;" "$core_down"
rg --quiet --fixed-strings "app_private.assert_data01_rollback_safe()" "$core_down"
rg --quiet --fixed-strings "app_private.assert_sto01_rollback_safe()" "$storage_down"
rg --quiet --fixed-strings "select plan(55);" "$db_test"
rg --quiet --fixed-strings "owner cannot read another user draft" "$db_test"
rg --quiet --fixed-strings "support cannot query raw draft payloads" "$db_test"
rg --quiet --fixed-strings "broad legacy policy" "$db_test"
rg --quiet --fixed-strings "composite foreign key rejects" "$db_test"
rg --quiet --fixed-strings "rollback guard refuses" "$db_test"

storage_policies=(
    minerva_storage_select_guard
    minerva_storage_insert_guard
    minerva_storage_update_guard
    minerva_storage_delete_guard
    minerva_storage_owner_read
    minerva_storage_owner_upload_family
    minerva_storage_owner_update_family
    minerva_storage_owner_delete_family
    minerva_storage_support_read
    minerva_storage_service_all
)
for policy in "${storage_policies[@]}"; do
    rg --quiet --fixed-strings "create policy $policy" "$storage"
    rg --quiet --fixed-strings "drop policy if exists $policy" "$storage_down"
done

for guard in select insert update delete; do
    rg --quiet --fixed-strings \
        "create policy minerva_storage_${guard}_guard" "$storage"
done

if rg --quiet --fixed-strings "app_private.owns_guide_job" "$storage"; then
    echo "Legacy job-only storage authorization remains." >&2
    exit 1
fi

echo "Supabase DATA-01/STO-01 migration structure: OK"
