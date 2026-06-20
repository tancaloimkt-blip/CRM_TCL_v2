-- =====================================================================
-- RESET — xóa sạch để chạy lại từ đầu (DÙNG KHI DB chưa có dữ liệu thật).
-- Chạy file này TRƯỚC, rồi chạy 01_schema.sql, rồi 02_security.sql.
-- =====================================================================
drop table if exists audit_log, fees, orders, customers, profiles cascade;
drop function if exists current_role_is(user_role) cascade;
drop function if exists is_giam_doc_or_ke_toan() cascade;
drop function if exists fn_audit() cascade;
drop function if exists fn_touch_updated_at() cascade;
drop type if exists user_role cascade;
