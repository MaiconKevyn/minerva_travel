begin;

drop index if exists public.entitlements_builder_status_idx;
drop index if exists public.entitlements_source_payment_uidx;
drop index if exists public.entitlements_guide_builder_uidx;
alter table public.entitlements
    drop constraint if exists entitlements_guide_source_present,
    drop constraint if exists entitlements_builder_session_id_length,
    drop column if exists builder_session_id;

drop index if exists public.payments_active_builder_uidx;
drop index if exists public.payments_builder_session_idx;
drop index if exists public.payments_provider_preference_uidx;
alter table public.payments
    drop constraint if exists payments_checkout_url_https,
    drop constraint if exists payments_provider_preference_id_length,
    drop constraint if exists payments_builder_session_id_length,
    drop column if exists checkout_url,
    drop column if exists provider_preference_id,
    drop column if exists builder_session_id;

commit;
