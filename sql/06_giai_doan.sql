-- =====================================================================
-- Thêm cột "giai_doan" (giai đoạn chăm sóc) cho khách hàng — dùng cho
-- bảng Tiềm Năng (Kanban kéo-thả).
-- Các giai đoạn: Tiềm năng -> Đang tư vấn -> Đã báo giá -> Đã chốt -> Đã thanh toán
-- Chạy trong Supabase SQL Editor.
-- =====================================================================
alter table customers
    add column if not exists giai_doan text not null default 'Tiềm năng';

-- (Khách hiện có sẽ tự nhận giá trị mặc định 'Tiềm năng'.)
