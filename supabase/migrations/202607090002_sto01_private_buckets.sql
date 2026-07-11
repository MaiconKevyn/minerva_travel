begin;

do $$
begin
    if not coalesce(
        (
            select pg_class.relrowsecurity
            from pg_class
            join pg_namespace on pg_namespace.oid = pg_class.relnamespace
            where pg_namespace.nspname = 'storage'
                and pg_class.relname = 'objects'
        ),
        false
    ) then
        raise exception 'STO-01 preflight refused: storage.objects must exist with RLS enabled.';
    end if;

    if exists (
        select 1
        from pg_policies
        where schemaname = 'storage'
            and tablename = 'objects'
            and policyname = any (
                array[
                    'minerva_storage_select_guard',
                    'minerva_storage_insert_guard',
                    'minerva_storage_update_guard',
                    'minerva_storage_delete_guard',
                    'minerva_storage_owner_read',
                    'minerva_storage_owner_upload_family',
                    'minerva_storage_owner_update_family',
                    'minerva_storage_owner_delete_family',
                    'minerva_storage_support_read',
                    'minerva_storage_service_all'
                ]::text[]
            )
    ) then
        raise exception 'STO-01 preflight refused: a Minerva storage policy name already exists.';
    end if;
end;
$$;

create table app_private.storage_bucket_rollback_state (
    id text primary key,
    existed boolean not null,
    previous_name text,
    previous_public boolean,
    previous_file_size_limit bigint,
    previous_allowed_mime_types text[]
);

revoke all on table app_private.storage_bucket_rollback_state from public;

insert into app_private.storage_bucket_rollback_state (
    id,
    existed,
    previous_name,
    previous_public,
    previous_file_size_limit,
    previous_allowed_mime_types
)
select
    desired.id,
    buckets.id is not null,
    buckets.name,
    buckets.public,
    buckets.file_size_limit,
    buckets.allowed_mime_types
from (
    values
        ('family-uploads'),
        ('generated-covers'),
        ('generated-guides'),
        ('landmark-assets')
) as desired(id)
left join storage.buckets as buckets on buckets.id = desired.id;

insert into storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
values
    (
        'family-uploads',
        'family-uploads',
        false,
        10485760,
        array['image/jpeg', 'image/png', 'image/webp']::text[]
    ),
    (
        'generated-covers',
        'generated-covers',
        false,
        15728640,
        array['image/jpeg', 'image/png', 'image/webp']::text[]
    ),
    (
        'generated-guides',
        'generated-guides',
        false,
        52428800,
        array['application/pdf']::text[]
    ),
    (
        'landmark-assets',
        'landmark-assets',
        false,
        15728640,
        array['image/jpeg', 'image/png', 'image/webp']::text[]
    )
on conflict (id) do update
set
    name = excluded.name,
    public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

create function app_private.assert_sto01_rollback_safe()
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if to_regclass('app_private.storage_bucket_rollback_state') is null then
        raise exception 'STO-01 rollback state is missing; refusing an unsafe rollback.';
    end if;

    if exists (
        select 1
        from storage.objects as objects
        join app_private.storage_bucket_rollback_state as state
            on state.id = objects.bucket_id
        where not state.existed
    ) then
        raise exception
            'STO-01 rollback refused: a bucket created by the migration still contains objects.'
            using hint = 'Delete objects through the Storage API or migrate them before retrying.';
    end if;
end;
$$;

revoke all on function app_private.assert_sto01_rollback_safe() from public;

-- These RESTRICTIVE guards are a tenant boundary for every authenticated
-- policy, including permissive policies that may predate this migration. They
-- are intentionally neutral for buckets outside Minerva's managed set.
create policy minerva_storage_select_guard
on storage.objects as restrictive for select to authenticated
using (
    not (
        bucket_id = any (
            array[
                'family-uploads',
                'generated-covers',
                'generated-guides',
                'landmark-assets'
            ]::text[]
        )
    )
    or (
        coalesce(array_length(storage.foldername(name), 1), 0) = 2
        and (
            (
                (storage.foldername(name))[1] = (select auth.uid()::text)
                and (select app_private.owns_registered_asset(bucket_id, name))
            )
            or (select app_private.support_can_read_registered_asset(bucket_id, name))
        )
    )
);

create policy minerva_storage_insert_guard
on storage.objects as restrictive for insert to authenticated
with check (
    not (
        bucket_id = any (
            array[
                'family-uploads',
                'generated-covers',
                'generated-guides',
                'landmark-assets'
            ]::text[]
        )
    )
    or (
        bucket_id = 'family-uploads'
        and coalesce(array_length(storage.foldername(name), 1), 0) = 2
        and (storage.foldername(name))[1] = (select auth.uid()::text)
        and (
            select app_private.can_upload_family_asset(
                (storage.foldername(name))[2],
                name
            )
        )
    )
);

create policy minerva_storage_update_guard
on storage.objects as restrictive for update to authenticated
using (
    not (
        bucket_id = any (
            array[
                'family-uploads',
                'generated-covers',
                'generated-guides',
                'landmark-assets'
            ]::text[]
        )
    )
    or (
        bucket_id = 'family-uploads'
        and coalesce(array_length(storage.foldername(name), 1), 0) = 2
        and (storage.foldername(name))[1] = (select auth.uid()::text)
        and (
            select app_private.can_upload_family_asset(
                (storage.foldername(name))[2],
                name
            )
        )
    )
)
with check (
    not (
        bucket_id = any (
            array[
                'family-uploads',
                'generated-covers',
                'generated-guides',
                'landmark-assets'
            ]::text[]
        )
    )
    or (
        bucket_id = 'family-uploads'
        and coalesce(array_length(storage.foldername(name), 1), 0) = 2
        and (storage.foldername(name))[1] = (select auth.uid()::text)
        and (
            select app_private.can_upload_family_asset(
                (storage.foldername(name))[2],
                name
            )
        )
    )
);

create policy minerva_storage_delete_guard
on storage.objects as restrictive for delete to authenticated
using (
    not (
        bucket_id = any (
            array[
                'family-uploads',
                'generated-covers',
                'generated-guides',
                'landmark-assets'
            ]::text[]
        )
    )
    or (
        bucket_id = 'family-uploads'
        and coalesce(array_length(storage.foldername(name), 1), 0) = 2
        and (storage.foldername(name))[1] = (select auth.uid()::text)
        and (select app_private.owns_registered_asset(bucket_id, name))
    )
);

create policy minerva_storage_owner_read
on storage.objects for select to authenticated
using (
    bucket_id = any (
        array[
            'family-uploads',
            'generated-covers',
            'generated-guides',
            'landmark-assets'
        ]::text[]
    )
    and coalesce(array_length(storage.foldername(name), 1), 0) = 2
    and (storage.foldername(name))[1] = (select auth.uid()::text)
    and (select app_private.owns_registered_asset(bucket_id, name))
);

create policy minerva_storage_owner_upload_family
on storage.objects for insert to authenticated
with check (
    bucket_id = 'family-uploads'
    and coalesce(array_length(storage.foldername(name), 1), 0) = 2
    and (storage.foldername(name))[1] = (select auth.uid()::text)
    and (
        select app_private.can_upload_family_asset(
            (storage.foldername(name))[2],
            name
        )
    )
);

create policy minerva_storage_owner_update_family
on storage.objects for update to authenticated
using (
    bucket_id = 'family-uploads'
    and coalesce(array_length(storage.foldername(name), 1), 0) = 2
    and (storage.foldername(name))[1] = (select auth.uid()::text)
    and (
        select app_private.can_upload_family_asset(
            (storage.foldername(name))[2],
            name
        )
    )
)
with check (
    bucket_id = 'family-uploads'
    and coalesce(array_length(storage.foldername(name), 1), 0) = 2
    and (storage.foldername(name))[1] = (select auth.uid()::text)
    and (
        select app_private.can_upload_family_asset(
            (storage.foldername(name))[2],
            name
        )
    )
);

create policy minerva_storage_owner_delete_family
on storage.objects for delete to authenticated
using (
    bucket_id = 'family-uploads'
    and coalesce(array_length(storage.foldername(name), 1), 0) = 2
    and (storage.foldername(name))[1] = (select auth.uid()::text)
    and (select app_private.owns_registered_asset(bucket_id, name))
);

create policy minerva_storage_support_read
on storage.objects for select to authenticated
using ((select app_private.support_can_read_registered_asset(bucket_id, name)));

create policy minerva_storage_service_all
on storage.objects for all to service_role
using (
    bucket_id = any (
        array[
            'family-uploads',
            'generated-covers',
            'generated-guides',
            'landmark-assets'
        ]::text[]
    )
)
with check (
    bucket_id = any (
        array[
            'family-uploads',
            'generated-covers',
            'generated-guides',
            'landmark-assets'
        ]::text[]
    )
);

commit;
