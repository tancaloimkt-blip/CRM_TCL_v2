-- =====================================================================
-- CRM TCL Logistics — Phân quyền (RLS) + Lịch sử thay đổi (Audit)
-- Chạy SAU file 01_schema.sql, trên Supabase SQL Editor.
-- =====================================================================

-- ---------------------------------------------------------------------
-- PHẦN A: AUDIT LOG — trigger tự ghi mọi INSERT/UPDATE/DELETE
-- ---------------------------------------------------------------------
create or replace function fn_audit() returns trigger
language plpgsql security definer as $$
declare
    v_email text;
begin
    select email into v_email from auth.users where id = auth.uid();

    if (tg_op = 'DELETE') then
        insert into audit_log(user_id, user_email, bang, hanh_dong, record_id, du_lieu_cu)
        values (auth.uid(), v_email, tg_table_name, tg_op, old.id::text, to_jsonb(old));
        return old;
    elsif (tg_op = 'UPDATE') then
        insert into audit_log(user_id, user_email, bang, hanh_dong, record_id, du_lieu_cu, du_lieu_moi)
        values (auth.uid(), v_email, tg_table_name, tg_op, new.id::text, to_jsonb(old), to_jsonb(new));
        return new;
    else  -- INSERT
        insert into audit_log(user_id, user_email, bang, hanh_dong, record_id, du_lieu_moi)
        values (auth.uid(), v_email, tg_table_name, tg_op, new.id::text, to_jsonb(new));
        return new;
    end if;
end;
$$;

create trigger trg_audit_customers
    after insert or update or delete on customers
    for each row execute function fn_audit();

create trigger trg_audit_orders
    after insert or update or delete on orders
    for each row execute function fn_audit();

create trigger trg_audit_fees
    after insert or update or delete on fees
    for each row execute function fn_audit();

-- Tự cập nhật updated_at mỗi lần sửa
create or replace function fn_touch_updated_at() returns trigger
language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

create trigger trg_touch_customers before update on customers
    for each row execute function fn_touch_updated_at();
create trigger trg_touch_orders before update on orders
    for each row execute function fn_touch_updated_at();


-- ---------------------------------------------------------------------
-- PHẦN B: RLS — phân quyền ở tầng database
-- ---------------------------------------------------------------------
alter table profiles   enable row level security;
alter table customers  enable row level security;
alter table orders     enable row level security;
alter table fees       enable row level security;
alter table audit_log  enable row level security;

-- ===== PROFILES =====
-- Ai cũng xem được danh sách profile (để hiển thị tên sale). Chỉ GĐ sửa.
create policy profiles_select on profiles
    for select using (true);
create policy profiles_admin on profiles
    for all using (current_role_is('giam_doc'))
    with check (current_role_is('giam_doc'));

-- ===== CUSTOMERS =====
-- XEM: GĐ + kế toán xem tất cả; sale chỉ xem khách mình phụ trách.
create policy customers_select on customers
    for select using (
        is_giam_doc_or_ke_toan() or sale_id = auth.uid()
    );

-- THÊM: GĐ thêm bất kỳ; sale thêm nhưng phải gán cho chính mình.
create policy customers_insert on customers
    for insert with check (
        current_role_is('giam_doc') or sale_id = auth.uid()
    );

-- SỬA: GĐ sửa tất cả. Sale sửa khách mình NHƯNG không được đổi sale_id
--      (đổi chủ sở hữu chỉ GĐ — enforced bởi policy update của GĐ + check dưới).
create policy customers_update_gd on customers
    for update using (current_role_is('giam_doc'))
    with check (current_role_is('giam_doc'));

create policy customers_update_sale on customers
    for update using (sale_id = auth.uid() and current_role_is('sale'))
    with check (sale_id = auth.uid());   -- không cho sale chuyển khách sang người khác

-- XÓA: chỉ GĐ.
create policy customers_delete on customers
    for delete using (current_role_is('giam_doc'));

-- ===== ORDERS =====
-- Đơn hàng "thuộc về" sale qua customer.sale_id.
-- Sale được xem CẢ giá vốn/lợi nhuận của khách mình (theo yêu cầu đã chốt).
create policy orders_select on orders
    for select using (
        is_giam_doc_or_ke_toan()
        or exists (
            select 1 from customers c
            where c.id = orders.customer_id and c.sale_id = auth.uid()
        )
    );

create policy orders_insert on orders
    for insert with check (
        current_role_is('giam_doc')
        or exists (
            select 1 from customers c
            where c.id = orders.customer_id and c.sale_id = auth.uid()
        )
    );

create policy orders_update on orders
    for update using (
        current_role_is('giam_doc')
        or exists (
            select 1 from customers c
            where c.id = orders.customer_id and c.sale_id = auth.uid()
        )
    );

create policy orders_delete on orders
    for delete using (current_role_is('giam_doc'));

-- ===== FEES =====
-- Theo đơn hàng → theo quyền của đơn hàng đó.
create policy fees_all on fees
    for all using (
        is_giam_doc_or_ke_toan()
        or exists (
            select 1 from orders o
            join customers c on c.id = o.customer_id
            where o.id = fees.order_id and c.sale_id = auth.uid()
        )
    );

-- ===== AUDIT_LOG =====
-- Chỉ GĐ + kế toán xem lịch sử. Không ai sửa/xóa (chỉ trigger ghi vào).
create policy audit_select on audit_log
    for select using (is_giam_doc_or_ke_toan());

-- =====================================================================
-- XONG. Sau khi chạy 2 file SQL: tạo user, gán role, rồi import dữ liệu.
-- =====================================================================
