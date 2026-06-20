-- =====================================================================
-- Bảng GHI CHÚ & NHẮC VIỆC (notes) cho từng khách hàng.
-- Chạy trong Supabase SQL Editor (sau các file trước).
-- =====================================================================
create table if not exists notes (
    id             bigint generated always as identity primary key,
    customer_id    bigint references customers (id) on delete cascade,
    user_id        uuid,                 -- người tạo ghi chú
    noi_dung       text not null,
    follow_up_date date,                 -- ngày cần liên hệ lại (có thể trống)
    done           boolean not null default false,
    created_at     timestamptz not null default now()
);
create index if not exists idx_notes_customer on notes (customer_id);
create index if not exists idx_notes_followup on notes (follow_up_date) where done = false;

-- Audit cho notes
create trigger trg_audit_notes
    after insert or update or delete on notes
    for each row execute function fn_audit();

-- ---- RLS ----
alter table notes enable row level security;

-- Xem: GĐ/kế toán xem tất cả; sale xem ghi chú của khách mình phụ trách.
create policy notes_select on notes
    for select using (
        is_giam_doc_or_ke_toan()
        or exists (select 1 from customers c
                   where c.id = notes.customer_id and c.sale_id = auth.uid())
    );

-- Thêm: phải gắn user_id = chính mình, và có quyền trên khách đó.
create policy notes_insert on notes
    for insert with check (
        user_id = auth.uid()
        and (current_role_is('giam_doc')
             or exists (select 1 from customers c
                        where c.id = notes.customer_id and c.sale_id = auth.uid()))
    );

-- Sửa (vd: đánh dấu đã xong): GĐ, hoặc sale phụ trách khách đó.
create policy notes_update on notes
    for update using (
        current_role_is('giam_doc')
        or exists (select 1 from customers c
                   where c.id = notes.customer_id and c.sale_id = auth.uid())
    );

-- Xóa: GĐ hoặc người tạo.
create policy notes_delete on notes
    for delete using (
        current_role_is('giam_doc') or user_id = auth.uid()
    );
