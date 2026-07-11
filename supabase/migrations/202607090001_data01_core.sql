begin;

-- This schema is migration-owned. A pre-existing schema is treated as a hard
-- collision so neither the migration nor its rollback can overwrite/drop
-- unrelated functions.
create schema app_private;
revoke all on schema app_private from public;
grant usage on schema app_private to authenticated, service_role;

create function app_private.is_support()
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
    select coalesce(
        (auth.jwt() -> 'app_metadata' ->> 'role') = 'support',
        false
    );
$$;

revoke all on function app_private.is_support() from public;
grant execute on function app_private.is_support() to authenticated, service_role;

create function app_private.set_updated_at()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    new.updated_at := pg_catalog.statement_timestamp();
    return new;
end;
$$;

revoke all on function app_private.set_updated_at() from public;

create type public.guide_draft_status as enum (
    'active',
    'submitted',
    'abandoned',
    'deleted'
);

create type public.guide_job_status as enum (
    'queued',
    'running',
    'succeeded',
    'failed',
    'cancelled'
);

create type public.guide_job_stage as enum (
    'queued',
    'validating',
    'preparing_assets',
    'generating_cover',
    'generating_content',
    'rendering_pdf',
    'persisting',
    'finalizing',
    'complete'
);

create type public.guide_status as enum (
    'generating',
    'ready',
    'failed',
    'expired',
    'deleted'
);

create type public.guide_asset_kind as enum (
    'family_upload',
    'generated_cover',
    'generated_guide',
    'landmark_source',
    'landmark_generated',
    'lineart',
    'trip_summary',
    'intermediate'
);

create type public.guide_asset_status as enum (
    'pending',
    'available',
    'deleted'
);

create type public.payment_status as enum (
    'pending',
    'authorized',
    'paid',
    'failed',
    'partially_refunded',
    'refunded',
    'cancelled'
);

create type public.entitlement_status as enum (
    'active',
    'consumed',
    'expired',
    'revoked'
);

create type public.entitlement_kind as enum (
    'guide_generation',
    'restaurant_recommendations',
    'premium_assets'
);

create table public.guide_drafts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    status public.guide_draft_status not null default 'active',
    title text not null default '',
    payload jsonb not null default '{}'::jsonb,
    revision integer not null default 1,
    schema_version integer not null default 1,
    template_version text not null default '2026-07-09',
    model_version text not null default 'not_generated',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    expires_at timestamptz,
    deleted_at timestamptz,
    constraint guide_drafts_title_length check (char_length(title) <= 200),
    constraint guide_drafts_payload_object check (jsonb_typeof(payload) = 'object'),
    constraint guide_drafts_revision_positive check (revision > 0),
    constraint guide_drafts_schema_version_positive check (schema_version > 0),
    constraint guide_drafts_template_version_present check (char_length(template_version) > 0),
    constraint guide_drafts_model_version_present check (char_length(model_version) > 0),
    constraint guide_drafts_expiry_after_creation check (
        expires_at is null or expires_at > created_at
    ),
    unique (id, user_id)
);

create table public.guide_jobs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    draft_id uuid,
    idempotency_key text not null,
    status public.guide_job_status not null default 'queued',
    stage public.guide_job_stage not null default 'queued',
    progress smallint not null default 0,
    request_snapshot jsonb not null default '{}'::jsonb,
    attempt_count smallint not null default 0,
    max_attempts smallint not null default 3,
    error_code text,
    error_message_safe text,
    error_retryable boolean not null default false,
    schema_version integer not null default 1,
    template_version text not null default '2026-07-09',
    model_version text not null default 'not_selected',
    queued_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    cancelled_at timestamptz,
    next_retry_at timestamptz,
    expires_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint guide_jobs_idempotency_key_length check (
        char_length(idempotency_key) between 1 and 200
    ),
    constraint guide_jobs_progress_range check (progress between 0 and 100),
    constraint guide_jobs_request_snapshot_object check (
        jsonb_typeof(request_snapshot) = 'object'
    ),
    constraint guide_jobs_attempt_count_valid check (attempt_count >= 0),
    constraint guide_jobs_max_attempts_valid check (max_attempts between 1 and 10),
    constraint guide_jobs_error_code_length check (
        error_code is null or char_length(error_code) <= 80
    ),
    constraint guide_jobs_safe_error_length check (
        error_message_safe is null or char_length(error_message_safe) <= 500
    ),
    constraint guide_jobs_schema_version_positive check (schema_version > 0),
    constraint guide_jobs_template_version_present check (char_length(template_version) > 0),
    constraint guide_jobs_model_version_present check (char_length(model_version) > 0),
    constraint guide_jobs_expiry_after_creation check (
        expires_at is null or expires_at > created_at
    ),
    constraint guide_jobs_final_timestamp check (
        (status in ('succeeded', 'failed', 'cancelled') and completed_at is not null)
        or (status not in ('succeeded', 'failed', 'cancelled') and completed_at is null)
    ),
    constraint guide_jobs_cancelled_timestamp check (
        status <> 'cancelled' or cancelled_at is not null
    ),
    constraint guide_jobs_draft_owner_fk
        foreign key (draft_id, user_id)
        references public.guide_drafts(id, user_id)
        deferrable initially deferred,
    unique (id, user_id),
    unique (user_id, idempotency_key)
);

create table public.guides (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    guide_job_id uuid unique,
    status public.guide_status not null default 'generating',
    title text not null,
    itinerary_summary jsonb not null default '{}'::jsonb,
    cover_fallback_used boolean not null default false,
    error_code text,
    error_message_safe text,
    schema_version integer not null default 1,
    template_version text not null default '2026-07-09',
    model_version text not null default 'not_selected',
    ready_at timestamptz,
    expires_at timestamptz,
    deleted_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint guides_title_length check (char_length(title) between 1 and 200),
    constraint guides_itinerary_summary_object check (
        jsonb_typeof(itinerary_summary) = 'object'
    ),
    constraint guides_error_code_length check (
        error_code is null or char_length(error_code) <= 80
    ),
    constraint guides_safe_error_length check (
        error_message_safe is null or char_length(error_message_safe) <= 500
    ),
    constraint guides_schema_version_positive check (schema_version > 0),
    constraint guides_template_version_present check (char_length(template_version) > 0),
    constraint guides_model_version_present check (char_length(model_version) > 0),
    constraint guides_ready_timestamp check (status <> 'ready' or ready_at is not null),
    constraint guides_expiry_after_creation check (
        expires_at is null or expires_at > created_at
    ),
    constraint guides_job_owner_fk
        foreign key (guide_job_id, user_id)
        references public.guide_jobs(id, user_id)
        deferrable initially deferred,
    unique (id, user_id)
);

create table public.guide_assets (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    guide_job_id uuid not null,
    guide_id uuid,
    kind public.guide_asset_kind not null,
    status public.guide_asset_status not null default 'pending',
    bucket_id text not null,
    object_path text not null,
    content_type text,
    size_bytes bigint,
    checksum_sha256 text,
    metadata_safe jsonb not null default '{}'::jsonb,
    schema_version integer not null default 1,
    template_version text not null default '2026-07-09',
    model_version text not null default 'not_applicable',
    expires_at timestamptz,
    deleted_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint guide_assets_bucket_known check (
        bucket_id in (
            'family-uploads',
            'generated-covers',
            'generated-guides',
            'landmark-assets'
        )
    ),
    constraint guide_assets_kind_matches_bucket check (
        (kind = 'family_upload' and bucket_id = 'family-uploads')
        or (kind in ('generated_cover', 'trip_summary') and bucket_id = 'generated-covers')
        or (kind = 'generated_guide' and bucket_id = 'generated-guides')
        or (
            kind in ('landmark_source', 'landmark_generated', 'lineart', 'intermediate')
            and bucket_id = 'landmark-assets'
        )
    ),
    constraint guide_assets_owner_path check (
        split_part(object_path, '/', 1) = user_id::text
    ),
    constraint guide_assets_job_path check (
        split_part(object_path, '/', 2) = guide_job_id::text
    ),
    constraint guide_assets_safe_path check (
        object_path !~ '(^/|//|(^|/)[.][.](/|$))'
    ),
    constraint guide_assets_canonical_path check (
        object_path ~ '^[^/]+/[^/]+/[^/]+$'
        and char_length(split_part(object_path, '/', 3)) between 1 and 255
    ),
    constraint guide_assets_size_valid check (size_bytes is null or size_bytes >= 0),
    constraint guide_assets_checksum_valid check (
        checksum_sha256 is null or checksum_sha256 ~ '^[0-9a-f]{64}$'
    ),
    constraint guide_assets_metadata_object check (jsonb_typeof(metadata_safe) = 'object'),
    constraint guide_assets_schema_version_positive check (schema_version > 0),
    constraint guide_assets_template_version_present check (char_length(template_version) > 0),
    constraint guide_assets_model_version_present check (char_length(model_version) > 0),
    constraint guide_assets_expiry_after_creation check (
        expires_at is null or expires_at > created_at
    ),
    constraint guide_assets_job_owner_fk
        foreign key (guide_job_id, user_id)
        references public.guide_jobs(id, user_id)
        deferrable initially deferred,
    constraint guide_assets_guide_owner_fk
        foreign key (guide_id, user_id)
        references public.guides(id, user_id)
        deferrable initially deferred,
    unique (bucket_id, object_path)
);

create table public.payments (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    guide_job_id uuid,
    provider text not null,
    provider_payment_id text,
    provider_customer_id text,
    idempotency_key text not null,
    status public.payment_status not null default 'pending',
    amount_minor bigint not null,
    currency text not null,
    product_code text not null,
    metadata_safe jsonb not null default '{}'::jsonb,
    schema_version integer not null default 1,
    authorized_at timestamptz,
    paid_at timestamptz,
    refunded_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint payments_provider_length check (char_length(provider) between 1 and 40),
    constraint payments_provider_payment_id_length check (
        provider_payment_id is null or char_length(provider_payment_id) <= 200
    ),
    constraint payments_provider_customer_id_length check (
        provider_customer_id is null or char_length(provider_customer_id) <= 200
    ),
    constraint payments_idempotency_key_length check (
        char_length(idempotency_key) between 1 and 200
    ),
    constraint payments_amount_nonnegative check (amount_minor >= 0),
    constraint payments_currency_iso check (currency ~ '^[A-Z]{3}$'),
    constraint payments_product_code_length check (
        char_length(product_code) between 1 and 100
    ),
    constraint payments_metadata_object check (jsonb_typeof(metadata_safe) = 'object'),
    constraint payments_schema_version_positive check (schema_version > 0),
    constraint payments_job_owner_fk
        foreign key (guide_job_id, user_id)
        references public.guide_jobs(id, user_id)
        deferrable initially deferred,
    unique (id, user_id),
    unique (provider, idempotency_key)
);

create unique index payments_provider_payment_uidx
    on public.payments (provider, provider_payment_id)
    where provider_payment_id is not null;

create table public.entitlements (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    source_payment_id uuid,
    consumed_by_job_id uuid,
    kind public.entitlement_kind not null,
    status public.entitlement_status not null default 'active',
    product_code text not null,
    quantity_granted integer not null default 1,
    quantity_consumed integer not null default 0,
    schema_version integer not null default 1,
    starts_at timestamptz not null default now(),
    expires_at timestamptz,
    consumed_at timestamptz,
    revoked_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint entitlements_product_code_length check (
        char_length(product_code) between 1 and 100
    ),
    constraint entitlements_quantities_valid check (
        quantity_granted > 0
        and quantity_consumed >= 0
        and quantity_consumed <= quantity_granted
    ),
    constraint entitlements_schema_version_positive check (schema_version > 0),
    constraint entitlements_expiry_after_start check (
        expires_at is null or expires_at > starts_at
    ),
    constraint entitlements_consumed_timestamp check (
        status <> 'consumed' or consumed_at is not null
    ),
    constraint entitlements_revoked_timestamp check (
        status <> 'revoked' or revoked_at is not null
    ),
    constraint entitlements_payment_owner_fk
        foreign key (source_payment_id, user_id)
        references public.payments(id, user_id)
        deferrable initially deferred,
    constraint entitlements_job_owner_fk
        foreign key (consumed_by_job_id, user_id)
        references public.guide_jobs(id, user_id)
        deferrable initially deferred,
    unique (id, user_id)
);

create table public.usage_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    guide_job_id uuid,
    guide_id uuid,
    entitlement_id uuid,
    event_type text not null,
    provider text,
    model_version text not null default 'not_applicable',
    quantity numeric(18, 6) not null default 1,
    unit text not null default 'event',
    cost_minor bigint,
    currency text,
    idempotency_key text,
    metadata_safe jsonb not null default '{}'::jsonb,
    schema_version integer not null default 1,
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    constraint usage_events_event_type_length check (
        char_length(event_type) between 1 and 100
    ),
    constraint usage_events_provider_length check (
        provider is null or char_length(provider) <= 80
    ),
    constraint usage_events_model_version_present check (char_length(model_version) > 0),
    constraint usage_events_quantity_nonnegative check (quantity >= 0),
    constraint usage_events_unit_length check (char_length(unit) between 1 and 40),
    constraint usage_events_cost_nonnegative check (cost_minor is null or cost_minor >= 0),
    constraint usage_events_currency_iso check (
        currency is null or currency ~ '^[A-Z]{3}$'
    ),
    constraint usage_events_idempotency_key_length check (
        idempotency_key is null or char_length(idempotency_key) <= 200
    ),
    constraint usage_events_metadata_object check (jsonb_typeof(metadata_safe) = 'object'),
    constraint usage_events_schema_version_positive check (schema_version > 0),
    constraint usage_events_job_owner_fk
        foreign key (guide_job_id, user_id)
        references public.guide_jobs(id, user_id)
        deferrable initially deferred,
    constraint usage_events_guide_owner_fk
        foreign key (guide_id, user_id)
        references public.guides(id, user_id)
        deferrable initially deferred,
    constraint usage_events_entitlement_owner_fk
        foreign key (entitlement_id, user_id)
        references public.entitlements(id, user_id)
        deferrable initially deferred
);

create unique index usage_events_owner_idempotency_uidx
    on public.usage_events (user_id, idempotency_key)
    where idempotency_key is not null;

-- The current product accepts one active family photo per generation job.
-- Enforcing the quota in the database closes the reservation/upload race.
create unique index guide_assets_one_active_family_per_job_uidx
    on public.guide_assets (guide_job_id)
    where kind = 'family_upload' and status <> 'deleted';

create table public.audit_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    actor_user_id uuid references auth.users(id) on delete set null,
    actor_role text not null default 'system',
    action text not null,
    resource_type text not null,
    resource_id text,
    request_id text,
    ip_hash text,
    user_agent_hash text,
    metadata_safe jsonb not null default '{}'::jsonb,
    schema_version integer not null default 1,
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    constraint audit_events_actor_role_length check (
        char_length(actor_role) between 1 and 40
    ),
    constraint audit_events_action_length check (char_length(action) between 1 and 120),
    constraint audit_events_resource_type_length check (
        char_length(resource_type) between 1 and 80
    ),
    constraint audit_events_resource_id_length check (
        resource_id is null or char_length(resource_id) <= 300
    ),
    constraint audit_events_request_id_length check (
        request_id is null or char_length(request_id) <= 200
    ),
    constraint audit_events_ip_hash_length check (
        ip_hash is null or char_length(ip_hash) <= 128
    ),
    constraint audit_events_user_agent_hash_length check (
        user_agent_hash is null or char_length(user_agent_hash) <= 128
    ),
    constraint audit_events_metadata_object check (jsonb_typeof(metadata_safe) = 'object'),
    constraint audit_events_schema_version_positive check (schema_version > 0)
);

create function app_private.owns_registered_asset(
    path_bucket_id text,
    path_object_path text
)
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
    select exists (
        select 1
        from public.guide_assets
        where guide_assets.user_id = auth.uid()
            and guide_assets.bucket_id = path_bucket_id
            and guide_assets.object_path = path_object_path
            and (
                (
                    guide_assets.bucket_id = 'family-uploads'
                    and guide_assets.status in ('pending', 'available')
                )
                or (
                    guide_assets.bucket_id <> 'family-uploads'
                    and guide_assets.status = 'available'
                )
            )
    );
$$;

revoke all on function app_private.owns_registered_asset(text, text) from public;
grant execute on function app_private.owns_registered_asset(text, text)
    to authenticated, service_role;

create function app_private.support_can_read_registered_asset(
    path_bucket_id text,
    path_object_path text
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select
        app_private.is_support()
        and path_bucket_id in ('generated-covers', 'generated-guides')
        and exists (
            select 1
            from public.guide_assets
            where guide_assets.bucket_id = path_bucket_id
                and guide_assets.object_path = path_object_path
                and guide_assets.status = 'available'
        );
$$;

revoke all on function app_private.support_can_read_registered_asset(text, text) from public;
grant execute on function app_private.support_can_read_registered_asset(text, text)
    to authenticated;

create function app_private.can_upload_family_asset(
    path_job_id text,
    path_object_path text
)
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
    select
        exists (
            select 1
            from public.guide_jobs
            where guide_jobs.id::text = path_job_id
                and guide_jobs.user_id = auth.uid()
                and guide_jobs.status in ('queued', 'running')
                and (guide_jobs.expires_at is null or guide_jobs.expires_at > now())
        )
        and exists (
            select 1
            from public.guide_assets
            where guide_assets.guide_job_id::text = path_job_id
                and guide_assets.user_id = auth.uid()
                and guide_assets.kind = 'family_upload'
                and guide_assets.bucket_id = 'family-uploads'
                and guide_assets.object_path = path_object_path
                and guide_assets.status in ('pending', 'available')
        )
        and (
            select count(*)
            from public.guide_assets
            where guide_assets.guide_job_id::text = path_job_id
                and guide_assets.user_id = auth.uid()
                and guide_assets.kind = 'family_upload'
                and guide_assets.status <> 'deleted'
        ) <= 1;
$$;

revoke all on function app_private.can_upload_family_asset(text, text) from public;
grant execute on function app_private.can_upload_family_asset(text, text)
    to authenticated, service_role;

create function app_private.assert_data01_rollback_safe()
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
    if exists (select 1 from public.audit_events limit 1)
        or exists (select 1 from public.usage_events limit 1)
        or exists (select 1 from public.entitlements limit 1)
        or exists (select 1 from public.payments limit 1)
        or exists (select 1 from public.guide_assets limit 1)
        or exists (select 1 from public.guides limit 1)
        or exists (select 1 from public.guide_jobs limit 1)
        or exists (select 1 from public.guide_drafts limit 1)
    then
        raise exception 'DATA-01 rollback refused: application tables contain data.'
            using hint = 'Export or delete records explicitly before retrying the rollback.';
    end if;
end;
$$;

revoke all on function app_private.assert_data01_rollback_safe() from public;

create function public.support_guide_operations(
    requested_user_id uuid default null,
    requested_limit integer default 100
)
returns table (
    job_id uuid,
    user_id uuid,
    job_status text,
    job_stage text,
    progress smallint,
    guide_id uuid,
    guide_status text,
    guide_title text,
    error_code text,
    error_message_safe text,
    payment_status text,
    amount_minor bigint,
    currency text,
    entitlement_status text,
    created_at timestamptz,
    updated_at timestamptz
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
    if not app_private.is_support() then
        raise exception 'Support role required.' using errcode = '42501';
    end if;

    return query
    select
        jobs.id,
        jobs.user_id,
        jobs.status::text,
        jobs.stage::text,
        jobs.progress,
        guides.id,
        guides.status::text,
        guides.title,
        jobs.error_code,
        jobs.error_message_safe,
        latest_payment.status,
        latest_payment.amount_minor,
        latest_payment.currency,
        latest_entitlement.status,
        jobs.created_at,
        jobs.updated_at
    from public.guide_jobs as jobs
    left join public.guides as guides
        on guides.guide_job_id = jobs.id
        and guides.user_id = jobs.user_id
    left join lateral (
        select
            payments.status::text as status,
            payments.amount_minor,
            payments.currency
        from public.payments
        where payments.guide_job_id = jobs.id
            and payments.user_id = jobs.user_id
        order by payments.created_at desc
        limit 1
    ) as latest_payment on true
    left join lateral (
        select entitlements.status::text as status
        from public.entitlements
        where entitlements.consumed_by_job_id = jobs.id
            and entitlements.user_id = jobs.user_id
        order by entitlements.created_at desc
        limit 1
    ) as latest_entitlement on true
    where requested_user_id is null or jobs.user_id = requested_user_id
    order by jobs.created_at desc
    limit least(greatest(coalesce(requested_limit, 100), 1), 200);
end;
$$;

comment on function public.support_guide_operations(uuid, integer) is
    'Redacted support projection. Omits draft/request payloads, asset paths, provider IDs, and metadata.';
revoke all on function public.support_guide_operations(uuid, integer) from public, anon;
grant execute on function public.support_guide_operations(uuid, integer) to authenticated;

comment on column public.guide_jobs.error_message_safe is
    'Sanitized user-facing error only; never store stack traces, prompts, secrets, or provider payloads.';
comment on column public.guides.error_message_safe is
    'Sanitized user-facing error only; never store stack traces, prompts, secrets, or provider payloads.';
comment on column public.payments.metadata_safe is
    'Allowlisted non-sensitive metadata only; never store card data, secrets, or complete webhook payloads.';
comment on column public.audit_events.metadata_safe is
    'Allowlisted metadata only; never store raw photos, names of children, tokens, or request bodies.';

create index guide_drafts_owner_updated_idx
    on public.guide_drafts (user_id, updated_at desc)
    where deleted_at is null;
create index guide_jobs_owner_created_idx
    on public.guide_jobs (user_id, created_at desc);
create index guide_jobs_status_retry_idx
    on public.guide_jobs (status, next_retry_at)
    where status in ('queued', 'running');
create index guide_jobs_draft_idx on public.guide_jobs (draft_id);
create index guides_owner_created_idx
    on public.guides (user_id, created_at desc)
    where deleted_at is null;
create index guides_owner_status_idx on public.guides (user_id, status);
create index guide_assets_owner_guide_idx on public.guide_assets (user_id, guide_id);
create index guide_assets_job_idx on public.guide_assets (guide_job_id);
create index guide_assets_guide_idx on public.guide_assets (guide_id);
create index guide_assets_expiry_idx
    on public.guide_assets (expires_at)
    where deleted_at is null and expires_at is not null;
create index payments_owner_created_idx on public.payments (user_id, created_at desc);
create index payments_job_idx on public.payments (guide_job_id);
create index entitlements_owner_status_idx on public.entitlements (user_id, status, expires_at);
create index entitlements_payment_idx on public.entitlements (source_payment_id);
create index entitlements_consumed_job_idx on public.entitlements (consumed_by_job_id);
create index usage_events_owner_occurred_idx
    on public.usage_events (user_id, occurred_at desc);
create index usage_events_job_idx on public.usage_events (guide_job_id);
create index usage_events_guide_idx on public.usage_events (guide_id);
create index usage_events_entitlement_idx on public.usage_events (entitlement_id);
create index audit_events_owner_occurred_idx
    on public.audit_events (user_id, occurred_at desc);
create index audit_events_resource_idx
    on public.audit_events (resource_type, resource_id, occurred_at desc);
create index audit_events_actor_idx on public.audit_events (actor_user_id);

create trigger minerva_guide_drafts_set_updated_at
before update on public.guide_drafts
for each row execute function app_private.set_updated_at();

create trigger minerva_guide_jobs_set_updated_at
before update on public.guide_jobs
for each row execute function app_private.set_updated_at();

create trigger minerva_guides_set_updated_at
before update on public.guides
for each row execute function app_private.set_updated_at();

create trigger minerva_guide_assets_set_updated_at
before update on public.guide_assets
for each row execute function app_private.set_updated_at();

create trigger minerva_payments_set_updated_at
before update on public.payments
for each row execute function app_private.set_updated_at();

create trigger minerva_entitlements_set_updated_at
before update on public.entitlements
for each row execute function app_private.set_updated_at();

alter table public.guide_drafts enable row level security;
alter table public.guide_drafts force row level security;
alter table public.guide_jobs enable row level security;
alter table public.guide_jobs force row level security;
alter table public.guides enable row level security;
alter table public.guides force row level security;
alter table public.guide_assets enable row level security;
alter table public.guide_assets force row level security;
alter table public.payments enable row level security;
alter table public.payments force row level security;
alter table public.entitlements enable row level security;
alter table public.entitlements force row level security;
alter table public.usage_events enable row level security;
alter table public.usage_events force row level security;
alter table public.audit_events enable row level security;
alter table public.audit_events force row level security;

revoke all privileges on table
    public.guide_drafts,
    public.guide_jobs,
    public.guides,
    public.guide_assets,
    public.payments,
    public.entitlements,
    public.usage_events,
    public.audit_events
from anon, authenticated;

grant select, insert, update, delete on table public.guide_drafts to authenticated;
grant select on table
    public.guide_jobs,
    public.guides,
    public.guide_assets,
    public.payments,
    public.entitlements,
    public.usage_events,
    public.audit_events
to authenticated;

grant all privileges on table
    public.guide_drafts,
    public.guide_jobs,
    public.guides,
    public.guide_assets,
    public.payments,
    public.entitlements,
    public.usage_events,
    public.audit_events
to service_role;

create policy minerva_guide_drafts_owner_read
on public.guide_drafts for select to authenticated
using (user_id = (select auth.uid()));
create policy minerva_guide_drafts_owner_insert
on public.guide_drafts for insert to authenticated
with check (user_id = (select auth.uid()));
create policy minerva_guide_drafts_owner_update
on public.guide_drafts for update to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));
create policy minerva_guide_drafts_owner_delete
on public.guide_drafts for delete to authenticated
using (user_id = (select auth.uid()));
create policy minerva_guide_drafts_service_all
on public.guide_drafts for all to service_role
using (true) with check (true);

create policy minerva_guide_jobs_owner_read
on public.guide_jobs for select to authenticated
using (user_id = (select auth.uid()));
create policy minerva_guide_jobs_service_all
on public.guide_jobs for all to service_role
using (true) with check (true);

create policy minerva_guides_owner_read
on public.guides for select to authenticated
using (user_id = (select auth.uid()));
create policy minerva_guides_service_all
on public.guides for all to service_role
using (true) with check (true);

create policy minerva_guide_assets_owner_read
on public.guide_assets for select to authenticated
using (user_id = (select auth.uid()));
create policy minerva_guide_assets_service_all
on public.guide_assets for all to service_role
using (true) with check (true);

create policy minerva_payments_owner_read
on public.payments for select to authenticated
using (user_id = (select auth.uid()));
create policy minerva_payments_service_all
on public.payments for all to service_role
using (true) with check (true);

create policy minerva_entitlements_owner_read
on public.entitlements for select to authenticated
using (user_id = (select auth.uid()));
create policy minerva_entitlements_service_all
on public.entitlements for all to service_role
using (true) with check (true);

create policy minerva_usage_events_owner_read
on public.usage_events for select to authenticated
using (user_id = (select auth.uid()));
create policy minerva_usage_events_service_all
on public.usage_events for all to service_role
using (true) with check (true);

create policy minerva_audit_events_owner_read
on public.audit_events for select to authenticated
using (user_id = (select auth.uid()));
create policy minerva_audit_events_service_all
on public.audit_events for all to service_role
using (true) with check (true);

commit;
