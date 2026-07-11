begin;

do $$
begin
    if to_regclass('app_private.storage_bucket_rollback_state') is not null then
        raise exception 'Run the STO-01 rollback before the DATA-01 rollback.';
    end if;
end;
$$;

select app_private.assert_data01_rollback_safe();

drop function if exists public.support_guide_operations(uuid, integer);
drop function if exists app_private.can_upload_family_asset(text, text);
drop function if exists app_private.support_can_read_registered_asset(text, text);
drop function if exists app_private.owns_registered_asset(text, text);
drop function if exists app_private.assert_data01_rollback_safe();

drop table if exists public.audit_events;
drop table if exists public.usage_events;
drop table if exists public.entitlements;
drop table if exists public.payments;
drop table if exists public.guide_assets;
drop table if exists public.guides;
drop table if exists public.guide_jobs;
drop table if exists public.guide_drafts;

drop function if exists app_private.set_updated_at();
drop function if exists app_private.is_support();
-- RESTRICT is deliberate: unexpected objects make rollback fail instead of
-- cascading into state that this migration does not own.
drop schema app_private restrict;

drop type if exists public.entitlement_kind;
drop type if exists public.entitlement_status;
drop type if exists public.payment_status;
drop type if exists public.guide_asset_status;
drop type if exists public.guide_asset_kind;
drop type if exists public.guide_status;
drop type if exists public.guide_job_stage;
drop type if exists public.guide_job_status;
drop type if exists public.guide_draft_status;

commit;
