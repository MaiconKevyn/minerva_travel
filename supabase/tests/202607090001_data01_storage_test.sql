begin;

set local search_path = public, extensions;

select plan(55);

select has_table('public', 'guide_drafts', 'guide_drafts exists');
select has_table('public', 'guide_jobs', 'guide_jobs exists');
select has_table('public', 'guides', 'guides exists');
select has_table('public', 'guide_assets', 'guide_assets exists');
select has_table('public', 'payments', 'payments exists');
select has_table('public', 'entitlements', 'entitlements exists');
select has_table('public', 'usage_events', 'usage_events exists');
select has_table('public', 'audit_events', 'audit_events exists');

select is(
    (
        select count(*)::integer
        from pg_class
        join pg_namespace on pg_namespace.oid = pg_class.relnamespace
        where pg_namespace.nspname = 'public'
            and pg_class.relname = any (
                array[
                    'guide_drafts',
                    'guide_jobs',
                    'guides',
                    'guide_assets',
                    'payments',
                    'entitlements',
                    'usage_events',
                    'audit_events'
                ]::text[]
            )
            and pg_class.relrowsecurity
            and pg_class.relforcerowsecurity
    ),
    8,
    'all DATA-01 tables force RLS'
);

select is(
    (
        select count(*)::integer
        from information_schema.columns
        where table_schema = 'public'
            and table_name = any (
                array[
                    'guide_drafts',
                    'guide_jobs',
                    'guides',
                    'guide_assets',
                    'payments',
                    'entitlements',
                    'usage_events',
                    'audit_events'
                ]::text[]
            )
            and column_name = 'schema_version'
    ),
    8,
    'all DATA-01 tables carry schema_version'
);

select is(
    (
        select count(*)::integer
        from information_schema.columns
        where table_schema = 'public'
            and table_name = any (
                array['guide_drafts', 'guide_jobs', 'guides', 'guide_assets']::text[]
            )
            and column_name = 'template_version'
    ),
    4,
    'rendering records carry template_version'
);

select is(
    (
        select count(*)::integer
        from information_schema.columns
        where table_schema = 'public'
            and table_name = any (
                array[
                    'guide_drafts',
                    'guide_jobs',
                    'guides',
                    'guide_assets',
                    'usage_events'
                ]::text[]
            )
            and column_name = 'model_version'
    ),
    5,
    'AI-related records carry model_version'
);

select is(
    (
        select count(*)::integer
        from information_schema.columns
        where table_schema = 'public'
            and table_name = any (array['guide_jobs', 'guides']::text[])
            and column_name = any (array['error_code', 'error_message_safe']::text[])
    ),
    4,
    'jobs and guides expose only safe error fields'
);

select is(
    (
        select count(*)::integer
        from pg_policies
        where schemaname = 'public'
            and policyname like 'minerva_%_owner_read'
    ),
    8,
    'each DATA-01 table has an owner read policy'
);

select is(
    (
        select count(*)::integer
        from pg_policies
        where schemaname = 'public'
            and policyname like 'minerva_%_owner_read'
            and coalesce(qual, '') like '%auth.uid%'
    ),
    8,
    'owner policies are scoped by auth.uid'
);

select is(
    (
        select count(*)::integer
        from pg_policies
        where schemaname = 'public'
            and policyname like 'minerva_%_support_read'
    ),
    0,
    'support has no raw table policy and must use the redacted RPC'
);

select is(
    (
        select count(*)::integer
        from pg_policies
        where schemaname = 'public'
            and policyname like 'minerva_%_service_all'
    ),
    8,
    'each DATA-01 table documents service_role access'
);

select is(
    (
        select count(*)::integer
        from storage.buckets
        where id = any (
            array[
                'family-uploads',
                'generated-covers',
                'generated-guides',
                'landmark-assets'
            ]::text[]
        )
            and not public
            and file_size_limit is not null
            and allowed_mime_types is not null
    ),
    4,
    'all managed buckets are private and constrained'
);

select is(
    (
        select count(*)::integer
        from pg_policies
        where schemaname = 'storage'
            and tablename = 'objects'
            and policyname like 'minerva_storage_%'
    ),
    10,
    'storage.objects has the complete Minerva policy set'
);

select is(
    (
        select count(*)::integer
        from pg_policies
        where schemaname = 'storage'
            and tablename = 'objects'
            and policyname like 'minerva_storage_%_guard'
            and permissive = 'RESTRICTIVE'
    ),
    4,
    'all storage operations have authenticated RESTRICTIVE guards'
);

select is(
    (
        select count(*)::integer
        from pg_trigger
        where not tgisinternal
            and tgname like 'minerva_%_set_updated_at'
    ),
    6,
    'mutable DATA-01 tables maintain updated_at'
);

select is(
    (
        select count(*)::integer
        from pg_type
        join pg_namespace on pg_namespace.oid = pg_type.typnamespace
        where pg_namespace.nspname = 'public'
            and pg_type.typname = any (
                array[
                    'guide_draft_status',
                    'guide_job_status',
                    'guide_job_stage',
                    'guide_status',
                    'guide_asset_kind',
                    'guide_asset_status',
                    'payment_status',
                    'entitlement_status',
                    'entitlement_kind'
                ]::text[]
            )
    ),
    9,
    'all DATA-01 enum types exist'
);

select is(
    (
        select count(*)::integer
        from pg_constraint
        where contype = 'f'
            and conname like '%_owner_fk'
            and cardinality(conkey) = 2
    ),
    10,
    'all parent links carry the owner in a composite foreign key'
);

select is(
    (
        select count(*)::integer
        from pg_constraint
        where conname = 'guide_assets_canonical_path'
            and contype = 'c'
    ),
    1,
    'asset rows enforce exactly user/job/file object keys'
);

select is(
    (
        select count(*)::integer
        from pg_indexes
        where schemaname = 'public'
            and indexname = 'guide_assets_one_active_family_per_job_uidx'
    ),
    1,
    'one active family upload reservation is enforced per job'
);

select is(
    (
        select count(*)::integer
        from pg_proc
        join pg_namespace on pg_namespace.oid = pg_proc.pronamespace
        where pg_namespace.nspname = 'public'
            and pg_proc.proname = 'support_guide_operations'
            and pg_proc.prosecdef
    ),
    1,
    'redacted support RPC exists as a guarded security-definer function'
);

select is(
    (
        select count(*)::integer
        from information_schema.columns
        where table_schema = 'app_private'
            and table_name = 'storage_bucket_rollback_state'
            and column_name = 'previous_name'
    ),
    1,
    'storage rollback snapshots the previous bucket name'
);

select is(
    to_regprocedure('app_private.assert_data01_rollback_safe()') is not null,
    true,
    'DATA-01 exposes a testable rollback safety preflight'
);

select is(
    to_regprocedure('app_private.assert_sto01_rollback_safe()') is not null,
    true,
    'STO-01 exposes a testable rollback safety preflight'
);

insert into auth.users (id, email)
values
    ('20000000-0000-0000-0000-000000000001', 'data01-owner-a@example.invalid'),
    ('20000000-0000-0000-0000-000000000002', 'data01-owner-b@example.invalid');

insert into public.guide_drafts (id, user_id, title)
values
    (
        '10000000-0000-0000-0000-000000000001',
        '20000000-0000-0000-0000-000000000001',
        'Owner A'
    ),
    (
        '10000000-0000-0000-0000-000000000002',
        '20000000-0000-0000-0000-000000000002',
        'Owner B'
    );

insert into public.guide_jobs (id, user_id, draft_id, idempotency_key)
values
    (
        '30000000-0000-0000-0000-000000000001',
        '20000000-0000-0000-0000-000000000001',
        '10000000-0000-0000-0000-000000000001',
        'data01-job-a'
    ),
    (
        '30000000-0000-0000-0000-000000000002',
        '20000000-0000-0000-0000-000000000002',
        '10000000-0000-0000-0000-000000000002',
        'data01-job-b'
    );

insert into public.guide_assets (
    id,
    user_id,
    guide_job_id,
    kind,
    status,
    bucket_id,
    object_path
)
values
    (
        '40000000-0000-0000-0000-000000000001',
        '20000000-0000-0000-0000-000000000001',
        '30000000-0000-0000-0000-000000000001',
        'family_upload',
        'pending',
        'family-uploads',
        '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/family-a.webp'
    ),
    (
        '40000000-0000-0000-0000-000000000002',
        '20000000-0000-0000-0000-000000000001',
        '30000000-0000-0000-0000-000000000001',
        'generated_cover',
        'available',
        'generated-covers',
        '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/cover-a.webp'
    ),
    (
        '40000000-0000-0000-0000-000000000003',
        '20000000-0000-0000-0000-000000000002',
        '30000000-0000-0000-0000-000000000002',
        'generated_cover',
        'available',
        'generated-covers',
        '20000000-0000-0000-0000-000000000002/30000000-0000-0000-0000-000000000002/cover-b.webp'
    );

insert into storage.objects (bucket_id, name)
values
    (
        'generated-covers',
        '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/cover-a.webp'
    ),
    (
        'generated-covers',
        '20000000-0000-0000-0000-000000000002/30000000-0000-0000-0000-000000000002/cover-b.webp'
    ),
    (
        'generated-covers',
        '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/unregistered.webp'
    );

-- Simulate a dangerous policy left by an older release. The Minerva
-- RESTRICTIVE guard must still win for all managed buckets.
create policy minerva_test_legacy_broad
on storage.objects for select to authenticated
using (true);

set local role authenticated;
set local request.jwt.claims =
    '{"role":"authenticated","sub":"20000000-0000-0000-0000-000000000001","app_metadata":{}}';

select is(
    (select count(*)::integer from public.guide_drafts),
    1,
    'owner sees exactly one own draft'
);

select is(
    (
        select count(*)::integer
        from public.guide_drafts
        where user_id = '20000000-0000-0000-0000-000000000002'
    ),
    0,
    'owner cannot read another user draft'
);

select is(
    (
        select app_private.can_upload_family_asset(
            '30000000-0000-0000-0000-000000000001',
            '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/family-a.webp'
        )
    ),
    true,
    'active owner job can upload its single server-reserved family asset'
);

select lives_ok(
    $$
        insert into storage.objects (bucket_id, name)
        values (
            'family-uploads',
            '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/family-a.webp'
        )
    $$,
    'owner can upload the exact reserved family object'
);

select is(
    (
        select count(*)::integer
        from storage.objects
        where bucket_id in ('family-uploads', 'generated-covers')
    ),
    2,
    'owner sees only registered own objects'
);

select is(
    (
        select count(*)::integer
        from storage.objects
        where name like '20000000-0000-0000-0000-000000000002/%'
    ),
    0,
    'storage owner cannot read another tenant despite a broad legacy policy'
);

select is(
    (
        select count(*)::integer
        from storage.objects
        where name like '%/unregistered.webp'
    ),
    0,
    'storage owner cannot read an unregistered own-prefix object'
);

select throws_ok(
    $$
        insert into storage.objects (bucket_id, name)
        values (
            'family-uploads',
            '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/not-reserved.webp'
        )
    $$,
    '42501',
    'new row violates row-level security policy for table "objects"',
    'owner cannot upload an unregistered object'
);

reset role;

select throws_ok(
    $$
        insert into public.guide_assets (
            user_id,
            guide_job_id,
            kind,
            status,
            bucket_id,
            object_path
        )
        values (
            '20000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000001',
            'generated_cover',
            'available',
            'generated-covers',
            '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/nested/cover.webp'
        )
    $$,
    '23514',
    'new row for relation "guide_assets" violates check constraint "guide_assets_canonical_path"',
    'asset metadata rejects a path deeper than user/job/file'
);

select throws_ok(
    $$
        insert into public.guide_assets (
            user_id,
            guide_job_id,
            kind,
            status,
            bucket_id,
            object_path
        )
        values (
            '20000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000001',
            'family_upload',
            'pending',
            'family-uploads',
            '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/family-second.webp'
        )
    $$,
    '23505',
    'duplicate key value violates unique constraint "guide_assets_one_active_family_per_job_uidx"',
    'database rejects a second active family upload reservation for one job'
);

set constraints guide_jobs_draft_owner_fk immediate;
select throws_ok(
    $$
        insert into public.guide_jobs (
            user_id,
            draft_id,
            idempotency_key
        )
        values (
            '20000000-0000-0000-0000-000000000001',
            '10000000-0000-0000-0000-000000000002',
            'cross-tenant-draft'
        )
    $$,
    '23503',
    'insert or update on table "guide_jobs" violates foreign key constraint "guide_jobs_draft_owner_fk"',
    'composite foreign key rejects a parent owned by another tenant'
);

set local role authenticated;
set local request.jwt.claims =
    '{"role":"authenticated","sub":"50000000-0000-0000-0000-000000000001","app_metadata":{"role":"support"}}';

select is(
    (select count(*)::integer from public.guide_drafts),
    0,
    'support cannot query raw draft payloads'
);

select is(
    (select count(*)::integer from public.guide_jobs),
    0,
    'support cannot query raw job request snapshots'
);

select is(
    (select count(*)::integer from public.support_guide_operations(null, 10)),
    2,
    'support can query only the redacted operational projection'
);

select is(
    (
        select count(*)::integer
        from storage.objects
        where bucket_id = 'generated-covers'
    ),
    2,
    'support can read registered generated outputs'
);

select is(
    (
        select count(*)::integer
        from storage.objects
        where bucket_id = 'family-uploads'
    ),
    0,
    'support cannot read raw family uploads'
);

set local request.jwt.claims =
    '{"role":"authenticated","sub":"50000000-0000-0000-0000-000000000002","app_metadata":{"role":"admin"}}';

select is(
    (select app_private.is_support()),
    false,
    'admin metadata is not implicitly promoted to support'
);

select throws_ok(
    $$ select * from public.support_guide_operations(null, 10) $$,
    '42501',
    'Support role required.',
    'admin cannot invoke the support projection'
);

select is(
    (select count(*)::integer from storage.objects),
    0,
    'admin cannot bypass managed-bucket guards via a broad legacy policy'
);

reset role;
set local role service_role;

select is(
    (select count(*)::integer from public.guide_drafts),
    2,
    'service_role can read both drafts'
);

select is(
    (
        select count(*)::integer
        from storage.objects
        where bucket_id in ('family-uploads', 'generated-covers')
    ),
    4,
    'service_role retains trusted access to managed objects'
);

reset role;

select throws_ok(
    $$ select app_private.assert_data01_rollback_safe() $$,
    'P0001',
    'DATA-01 rollback refused: application tables contain data.',
    'DATA-01 rollback guard refuses destructive rollback with records'
);

-- Force the generated-covers snapshot into the "created" branch so this test
-- remains behavioral even if a developer had a same-named local bucket.
update app_private.storage_bucket_rollback_state
set existed = false
where id = 'generated-covers';

select throws_ok(
    $$ select app_private.assert_sto01_rollback_safe() $$,
    'P0001',
    'STO-01 rollback refused: a bucket created by the migration still contains objects.',
    'STO-01 rollback guard refuses to remove a non-empty created bucket'
);

update public.guide_jobs
set status = 'succeeded', completed_at = now()
where id = '30000000-0000-0000-0000-000000000001';

set local role authenticated;
set local request.jwt.claims =
    '{"role":"authenticated","sub":"20000000-0000-0000-0000-000000000001","app_metadata":{}}';

select is(
    (
        select app_private.can_upload_family_asset(
            '30000000-0000-0000-0000-000000000001',
            '20000000-0000-0000-0000-000000000001/30000000-0000-0000-0000-000000000001/family-a.webp'
        )
    ),
    false,
    'completed jobs close the family-upload window'
);

reset role;
drop policy minerva_test_legacy_broad on storage.objects;
delete from storage.objects
where bucket_id in ('family-uploads', 'generated-covers');
delete from public.guide_assets;
delete from public.guide_jobs;
delete from public.guide_drafts;

select lives_ok(
    $$ select app_private.assert_data01_rollback_safe() $$,
    'DATA-01 rollback preflight accepts empty application tables'
);

select lives_ok(
    $$ select app_private.assert_sto01_rollback_safe() $$,
    'STO-01 rollback preflight accepts empty created buckets'
);

select * from finish();

rollback;
