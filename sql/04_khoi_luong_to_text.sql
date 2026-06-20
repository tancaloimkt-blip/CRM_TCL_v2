-- =====================================================================
-- Đổi cột khoi_luong từ numeric -> text.
-- Lý do: khối lượng trong thực tế ghi kèm đơn vị (vd "11.5 kg", "4.74 cbm",
-- "1x20'") nên phải lưu dạng chữ để không mất dữ liệu.
-- Chạy trong Supabase SQL Editor.
-- =====================================================================
alter table orders
    alter column khoi_luong type text using khoi_luong::text;
