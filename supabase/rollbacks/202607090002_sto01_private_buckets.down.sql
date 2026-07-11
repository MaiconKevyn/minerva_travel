begin;

select app_private.assert_sto01_rollback_safe();

drop policy if exists minerva_storage_service_all on storage.objects;
drop policy if exists minerva_storage_support_read on storage.objects;
drop policy if exists minerva_storage_owner_delete_family on storage.objects;
drop policy if exists minerva_storage_owner_update_family on storage.objects;
drop policy if exists minerva_storage_owner_upload_family on storage.objects;
drop policy if exists minerva_storage_owner_read on storage.objects;
drop policy if exists minerva_storage_delete_guard on storage.objects;
drop policy if exists minerva_storage_update_guard on storage.objects;
drop policy if exists minerva_storage_insert_guard on storage.objects;
drop policy if exists minerva_storage_select_guard on storage.objects;

update storage.buckets as buckets
set
    name = state.previous_name,
    public = state.previous_public,
    file_size_limit = state.previous_file_size_limit,
    allowed_mime_types = state.previous_allowed_mime_types
from app_private.storage_bucket_rollback_state as state
where buckets.id = state.id and state.existed;

delete from storage.buckets as buckets
using app_private.storage_bucket_rollback_state as state
where buckets.id = state.id and not state.existed;

drop function app_private.assert_sto01_rollback_safe();
drop table app_private.storage_bucket_rollback_state;

commit;
