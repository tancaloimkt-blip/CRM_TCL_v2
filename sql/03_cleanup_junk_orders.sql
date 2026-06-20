-- =====================================================================
-- DỌN ĐƠN HÀNG RÁC — xoá các dòng đơn không có dữ liệu nội dung thật.
--
-- Lưu ý: cột giá mua/giá bán/lợi nhuận trong Google Sheet là CÔNG THỨC kéo
-- sẵn xuống cả nghìn dòng (giá trị 0), nên KHÔNG dùng để xét rác.
-- "Đơn rác" = trống TẤT CẢ các trường nội dung thật bên dưới.
-- Ước tính: ~936 đơn rác bị xoá, giữ lại ~65 đơn thật.
-- =====================================================================

-- ---- BƯỚC 1 (tuỳ chọn): ĐẾM TRƯỚC ----
-- Bôi đen riêng câu SELECT này rồi Run để xem số sẽ xoá.
select count(*) as so_don_rac_se_xoa
from orders
where ma_dh                is null
  and ngay_dat             is null
  and customer_id          is null
  and shipper              is null
  and consignee            is null
  and ten_hang             is null
  and incoterm             is null
  and hinh_thuc_vc         is null
  and khoi_luong           is null
  and cang_di              is null
  and cang_den             is null
  and tinh_trang_giao_dich is null
  and trang_thai_hang      is null
  and eta                  is null
  and tinh_trang_thanh_toan is null
  and nha_cung_cap         is null
  and lich_su_giao_dich    is null
  and theo_doi_no          is null;


-- ---- BƯỚC 2: XOÁ (chạy cả khối dưới) ----
-- Tạm tắt audit để không tạo hàng trăm dòng "DELETE" trong lịch sử.
alter table orders disable trigger trg_audit_orders;

delete from orders
where ma_dh                is null
  and ngay_dat             is null
  and customer_id          is null
  and shipper              is null
  and consignee            is null
  and ten_hang             is null
  and incoterm             is null
  and hinh_thuc_vc         is null
  and khoi_luong           is null
  and cang_di              is null
  and cang_den             is null
  and tinh_trang_giao_dich is null
  and trang_thai_hang      is null
  and eta                  is null
  and tinh_trang_thanh_toan is null
  and nha_cung_cap         is null
  and lich_su_giao_dich    is null
  and theo_doi_no          is null;

alter table orders enable trigger trg_audit_orders;

-- ---- BƯỚC 3 (tuỳ chọn): kiểm tra còn lại ----
select count(*) as so_don_con_lai from orders;
