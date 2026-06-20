-- =====================================================================
-- CRM TCL Logistics — Database Schema (chạy 1 lần trên Supabase)
-- Paste toàn bộ file này vào: Supabase → SQL Editor → New query → Run
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. PROFILES: mở rộng thông tin user (Supabase Auth quản lý login).
--    Mỗi user khi đăng ký sẽ có 1 dòng ở đây kèm vai trò (role).
-- ---------------------------------------------------------------------
create type user_role as enum ('giam_doc', 'sale', 'ke_toan');

create table profiles (
    id          uuid primary key references auth.users (id) on delete cascade,
    ho_ten      text        not null,
    role        user_role   not null default 'sale',
    active      boolean     not null default true,
    created_at  timestamptz not null default now()
);

-- Hàm tiện ích: lấy role của user đang đăng nhập (dùng trong RLS).
create or replace function current_role_is(target user_role)
returns boolean language sql security definer stable as $$
    select exists (
        select 1 from profiles
        where id = auth.uid() and role = target and active = true
    );
$$;

create or replace function is_giam_doc_or_ke_toan()
returns boolean language sql security definer stable as $$
    select exists (
        select 1 from profiles
        where id = auth.uid() and role in ('giam_doc','ke_toan') and active = true
    );
$$;

-- ---------------------------------------------------------------------
-- 2. CUSTOMERS: danh sách khách hàng (gộp từ 3 Google Sheet).
--    sale_id = ai phụ trách → nền tảng của phân quyền.
-- ---------------------------------------------------------------------
create table customers (
    id                  bigint generated always as identity primary key,
    ma_kh               text,
    sale_id             uuid references profiles (id),   -- chủ sở hữu
    ngay_nhap_lieu      date,
    ten_kh              text not null,
    ten_cong_ty         text,
    nguoi_lien_he       text,
    email               text,
    sdt                 text,
    phan_loai           text,        -- KH thường xuyên / vãng lai / đã mất ...
    quoc_gia            text,
    kenh_giao_dich      text,        -- Zalo, Whatsapp, Email ...
    link_nhom_chat      text,
    ngay_sinh_nhat      date,
    facebook            text,
    tinh_trang_hon_nhan text,
    tinh_cach           text,
    ghi_chu             text,
    created_at          timestamptz not null default now(),
    updated_at          timestamptz not null default now()
);
create index on customers (sale_id);
create index on customers (ma_kh);

-- ---------------------------------------------------------------------
-- 3. ORDERS: chi tiết đơn hàng. Gắn với customer_id.
-- ---------------------------------------------------------------------
create table orders (
    id                      bigint generated always as identity primary key,
    ma_dh                   text,
    customer_id             bigint references customers (id) on delete set null,
    ngay_dat                date,
    shipper                 text,
    consignee               text,
    ten_hang                text,
    incoterm                text,
    hinh_thuc_vc            text,
    khoi_luong              numeric,
    cang_di                 text,
    cang_den                text,
    tinh_trang_giao_dich    text,    -- Đã chốt / Đã gửi báo giá / Đang tư vấn / Từ chối
    lich_su_giao_dich       text,
    gia_mua                 numeric,         -- 🔒 nhạy cảm
    nha_cung_cap            text,            -- 🔒 nhạy cảm
    gia_ban                 numeric,
    loi_nhuan               numeric,         -- 🔒 nhạy cảm
    trang_thai_hang         text,    -- Đã giao / Đang trung chuyển / Hải quan ...
    eta                     date,
    tinh_trang_thanh_toan   text,    -- Đã thanh toán / Chưa thanh toán
    theo_doi_no             text,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now()
);
create index on orders (customer_id);
create index on orders (ma_dh);

-- ---------------------------------------------------------------------
-- 4. FEES: chi tiết phí của từng đơn.
-- ---------------------------------------------------------------------
create table fees (
    id          bigint generated always as identity primary key,
    order_id    bigint references orders (id) on delete cascade,
    noi_dung_phi text,
    so_tien     numeric,
    loai        text,
    created_at  timestamptz not null default now()
);
create index on fees (order_id);

-- ---------------------------------------------------------------------
-- 5. AUDIT_LOG: lịch sử mọi thay đổi (ai, bảng nào, làm gì, dữ liệu cũ/mới).
-- ---------------------------------------------------------------------
create table audit_log (
    id          bigint generated always as identity primary key,
    user_id     uuid,
    user_email  text,
    bang        text,
    hanh_dong   text,          -- INSERT / UPDATE / DELETE
    record_id   text,
    du_lieu_cu  jsonb,
    du_lieu_moi jsonb,
    thoi_gian   timestamptz not null default now()
);
create index on audit_log (bang, thoi_gian desc);

-- =====================================================================
-- Lưu ý: RLS (phân quyền) và Trigger (audit) ở file 02_security.sql
-- =====================================================================
