begin;

alter table public.payments
    add column builder_session_id text,
    add column provider_preference_id text,
    add column checkout_url text;

alter table public.payments
    add constraint payments_builder_session_id_length check (
        builder_session_id is null or char_length(builder_session_id) between 1 and 120
    ),
    add constraint payments_provider_preference_id_length check (
        provider_preference_id is null or char_length(provider_preference_id) <= 200
    ),
    add constraint payments_checkout_url_https check (
        checkout_url is null or checkout_url ~ '^https://'
    );

create unique index payments_provider_preference_uidx
    on public.payments (provider, provider_preference_id)
    where provider_preference_id is not null;

create index payments_builder_session_idx
    on public.payments (user_id, builder_session_id, created_at desc)
    where builder_session_id is not null;

create unique index payments_active_builder_uidx
    on public.payments (user_id, builder_session_id)
    where builder_session_id is not null
      and status in ('pending', 'authorized', 'paid');

alter table public.entitlements
    add column builder_session_id text;

alter table public.entitlements
    add constraint entitlements_builder_session_id_length check (
        builder_session_id is null or char_length(builder_session_id) between 1 and 120
    ),
    add constraint entitlements_guide_source_present check (
        kind <> 'guide_generation'
        or (source_payment_id is not null and builder_session_id is not null)
    ) not valid;

create unique index entitlements_guide_builder_uidx
    on public.entitlements (user_id, builder_session_id)
    where kind = 'guide_generation' and builder_session_id is not null;

create unique index entitlements_source_payment_uidx
    on public.entitlements (source_payment_id)
    where source_payment_id is not null;

create index entitlements_builder_status_idx
    on public.entitlements (user_id, builder_session_id, status)
    where builder_session_id is not null;

commit;

