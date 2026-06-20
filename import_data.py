"""Import dữ liệu từ các file Excel (export từ Google Sheet) vào Supabase.

Chạy 1 lần để nạp dữ liệu ban đầu:
    pip install -r requirements.txt
    python import_data.py

Script sẽ:
  1. Tạo tài khoản đăng nhập cho team (giám đốc / kế toán / sale) + gán vai trò.
  2. Đọc từng file Excel, gán toàn bộ khách trong file cho đúng sale phụ trách.
  3. Nạp khách hàng → đơn hàng → phí vào Supabase.

Dùng SECRET key (bỏ qua RLS) — chỉ chạy trên máy bạn, không đưa lên app.
"""

from __future__ import annotations

import sys
import unicodedata
import re
from pathlib import Path

import pandas as pd

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

from supabase import create_client


# =====================================================================
# ★★★ PHẦN CẦN BẠN ĐIỀN ★★★
# =====================================================================

# 1) Tài khoản cho team. Mỗi người 1 dòng.
#    - role chỉ nhận: 'giam_doc' | 'sale' | 'ke_toan'
#    - password: mật khẩu khởi tạo, người dùng đăng nhập lần đầu rồi tự đổi.
#    - email không cần là email thật, nhưng nên dễ nhớ.
USERS = [
    {"email": "giamdoc@tcl.com",  "password": "tcl@2026", "ho_ten": "Giám Đốc",      "role": "giam_doc"},
    {"email": "ketoan@tcl.com",   "password": "tcl@2026", "ho_ten": "Kế Toán",       "role": "ke_toan"},
    # Thêm sale sau khi có file của họ, ví dụ:
    # {"email": "sale1@tcl.com",  "password": "tcl@2026", "ho_ten": "Tên Sale 1",    "role": "sale"},
]

# 2) File Excel nào thuộc về ai (dùng email khớp với USERS ở trên).
FILES = [
    {"path": r"C:\Users\user\Downloads\CRM - TCL Logistics - Khách GĐ.xlsx",
     "sale_email": "giamdoc@tcl.com"},
    # File của các sale khác (bổ sung sau khi export ra .xlsx):
    # {"path": r"C:\Users\user\Downloads\<file phòng 2>.xlsx", "sale_email": "sale1@tcl.com"},
]

# 3) Xóa sạch dữ liệu cũ trước khi import? (True khi chạy lại lần 2 để tránh trùng)
CLEAR_BEFORE_IMPORT = True

# =====================================================================
# (Phần dưới không cần sửa)
# =====================================================================

SHEET_CUSTOMERS = "DS Khách Hàng"
SHEET_ORDERS = "Chi tiết đơn hàng"
SHEET_FEES = "Chi tiết phí"

# Map cột Excel (chuẩn hoá không dấu) -> cột DB
CUSTOMER_MAP = {
    "ma kh": "ma_kh",
    "ngay nhap lieu": "ngay_nhap_lieu",
    "ten khach hang": "ten_kh",
    "ten cong ty": "ten_cong_ty",
    "nguoi lien he": "nguoi_lien_he",
    "email": "email",
    "so dien thoai": "sdt",
    "phan loai": "phan_loai",
    "quoc gia": "quoc_gia",
    "kenh giao dich": "kenh_giao_dich",
    "link nhom chat": "link_nhom_chat",
    "ngay sinh nhat": "ngay_sinh_nhat",
    "facebook": "facebook",
    "tinh trang hon nhan": "tinh_trang_hon_nhan",
    "tinh cach": "tinh_cach",
    "ghi chu chung": "ghi_chu",
}
ORDER_MAP = {
    "ma don hang": "ma_dh",
    "ngay dat hang": "ngay_dat",
    "ten khach hang": "_ten_kh",   # tạm, dùng để nối customer_id
    "shipper": "shipper",
    "consignee": "consignee",
    "ten hang": "ten_hang",
    "incoterm": "incoterm",
    "hinh thuc van chuyen": "hinh_thuc_vc",
    "khoi luong": "khoi_luong",
    "cang di": "cang_di",
    "cang den": "cang_den",
    "tinh trang giao dich": "tinh_trang_giao_dich",
    "lich su giao dich": "lich_su_giao_dich",
    "gia mua": "gia_mua",
    "nha cung cap": "nha_cung_cap",
    "gia ban": "gia_ban",
    "loi nhuan": "loi_nhuan",
    "trang thai hang hoa": "trang_thai_hang",
    "eta": "eta",
    "tinh trang thanh toan": "tinh_trang_thanh_toan",
    "theo doi no": "theo_doi_no",
}
FEE_MAP = {
    "ma don hang": "_ma_dh",       # tạm, dùng để nối order_id
    "noi dung phi": "noi_dung_phi",
    "so tien": "so_tien",
    "loai": "loai",
}

DATE_COLS = {"ngay_nhap_lieu", "ngay_sinh_nhat", "ngay_dat", "eta"}
# khoi_luong KHÔNG ép số vì hay ghi kèm đơn vị (kg/cbm/container) -> giữ chữ.
NUM_COLS = {"gia_mua", "gia_ban", "loi_nhuan", "so_tien"}


def _norm(s: str) -> str:
    s = str(s).replace("đ", "d").replace("Đ", "D")  # đ là chữ riêng, NFKD không tách
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower().strip())


def _rename(df: pd.DataFrame, colmap: dict) -> pd.DataFrame:
    norm_cols = {_norm(c): c for c in df.columns}
    rename = {norm_cols[k]: v for k, v in colmap.items() if k in norm_cols}
    return df.rename(columns=rename)[[v for v in colmap.values() if v in rename.values()]]


def _clean_value(col: str, val):
    """Chuyển 1 ô thành giá trị JSON hợp lệ cho Supabase."""
    if pd.isna(val):
        return None
    if col in DATE_COLS:
        ts = pd.to_datetime(val, errors="coerce", dayfirst=True)
        return None if pd.isna(ts) else ts.date().isoformat()
    if col in NUM_COLS:
        num = pd.to_numeric(val, errors="coerce")
        return None if pd.isna(num) else float(num)
    return str(val).strip()


def _rows(df: pd.DataFrame) -> list[dict]:
    out = []
    for _, r in df.iterrows():
        out.append({c: _clean_value(c, r[c]) for c in df.columns})
    return out


def load_secrets() -> dict:
    path = Path(__file__).parent / ".streamlit" / "secrets.toml"
    if not path.exists():
        sys.exit("❌ Chưa có .streamlit/secrets.toml — copy từ secrets.toml.example và điền.")
    with open(path, "rb") as f:
        return tomllib.load(f)


def get_or_create_user(admin, email: str, password: str) -> str:
    """Tạo user trong Supabase Auth nếu chưa có. Trả về UUID."""
    # Tìm user đã tồn tại
    try:
        existing = admin.auth.admin.list_users()
        users = existing if isinstance(existing, list) else getattr(existing, "users", [])
        for u in users:
            if getattr(u, "email", None) == email:
                return u.id
    except Exception as e:
        print(f"   (cảnh báo khi list users: {e})")

    res = admin.auth.admin.create_user({
        "email": email, "password": password, "email_confirm": True,
    })
    return res.user.id


def main() -> None:
    sec = load_secrets()
    # Cắt đuôi thừa nếu lỡ copy URL kèm /rest/v1 hoặc dấu "/" cuối.
    url = sec["SUPABASE_URL"].strip().rstrip("/")
    for suffix in ("/rest/v1", "/auth/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    service_key = sec["SUPABASE_SERVICE_KEY"]
    admin = create_client(url, service_key)

    # --- 1. Tạo user + profiles ---
    print("👤 Tạo tài khoản & vai trò...")
    email_to_uuid: dict[str, str] = {}
    for u in USERS:
        uid = get_or_create_user(admin, u["email"], u["password"])
        email_to_uuid[u["email"]] = uid
        admin.table("profiles").upsert({
            "id": uid, "ho_ten": u["ho_ten"], "role": u["role"], "active": True,
        }).execute()
        print(f"   ✓ {u['email']} ({u['role']})")

    # --- 2. Xóa dữ liệu cũ nếu cần ---
    if CLEAR_BEFORE_IMPORT:
        print("🧹 Xóa dữ liệu cũ...")
        for tbl in ("fees", "orders", "customers"):
            admin.table(tbl).delete().neq("id", 0).execute()

    # --- 3. Import từng file ---
    for f in FILES:
        path, sale_email = f["path"], f["sale_email"]
        sale_id = email_to_uuid.get(sale_email)
        if sale_id is None:
            print(f"⚠️  Bỏ qua {path}: sale_email '{sale_email}' không có trong USERS.")
            continue
        print(f"\n📂 {Path(path).name}  →  {sale_email}")

        xls = pd.ExcelFile(path)
        sheet_lookup = {_norm(s): s for s in xls.sheet_names}

        def read(sheet_name):
            real = sheet_lookup.get(_norm(sheet_name))
            return pd.read_excel(xls, sheet_name=real) if real else pd.DataFrame()

        # 3a. Customers
        cust_df = _rename(read(SHEET_CUSTOMERS), CUSTOMER_MAP)
        cust_df = cust_df.dropna(subset=["ten_kh"])
        cust_rows = _rows(cust_df)
        for row in cust_rows:
            row["sale_id"] = sale_id
        name_to_custid: dict[str, int] = {}
        if cust_rows:
            res = admin.table("customers").insert(cust_rows).execute()
            for rec in res.data:
                if rec.get("ten_kh"):
                    name_to_custid[_norm(rec["ten_kh"])] = rec["id"]
            print(f"   ✓ {len(res.data)} khách hàng")

        # 3b. Orders (nối customer_id theo tên khách)
        ord_df = _rename(read(SHEET_ORDERS), ORDER_MAP)
        ord_df = ord_df.dropna(how="all")
        ord_rows = _rows(ord_df)
        # Các trường "nội dung thật" để xác định đơn rỗng (bỏ qua giá vì là
        # công thức kéo sẵn trong Google Sheet, luôn có giá trị 0).
        content_fields = ("ma_dh", "ngay_dat", "shipper", "consignee", "ten_hang",
                          "incoterm", "hinh_thuc_vc", "khoi_luong", "cang_di", "cang_den",
                          "tinh_trang_giao_dich", "trang_thai_hang", "eta",
                          "tinh_trang_thanh_toan", "nha_cung_cap", "lich_su_giao_dich",
                          "theo_doi_no")
        madh_to_orderid: dict[str, int] = {}
        clean_orders = []
        for row in ord_rows:
            ten = row.pop("_ten_kh", None)
            row["customer_id"] = name_to_custid.get(_norm(ten)) if ten else None
            # Giữ đơn nếu có khách HOẶC có ít nhất 1 trường nội dung thật.
            has_content = row["customer_id"] is not None or any(
                row.get(f) is not None for f in content_fields
            )
            if has_content:
                clean_orders.append(row)
        if clean_orders:
            # insert theo lô 500 để tránh quá tải
            inserted = 0
            for i in range(0, len(clean_orders), 500):
                res = admin.table("orders").insert(clean_orders[i:i+500]).execute()
                for rec in res.data:
                    if rec.get("ma_dh"):
                        madh_to_orderid[_norm(rec["ma_dh"])] = rec["id"]
                inserted += len(res.data)
            print(f"   ✓ {inserted} đơn hàng")

        # 3c. Fees (nối order_id theo mã đơn)
        fee_df = _rename(read(SHEET_FEES), FEE_MAP)
        fee_df = fee_df.dropna(how="all")
        fee_rows = _rows(fee_df)
        clean_fees = []
        for row in fee_rows:
            madh = row.pop("_ma_dh", None)
            oid = madh_to_orderid.get(_norm(madh)) if madh else None
            if oid is not None:
                row["order_id"] = oid
                clean_fees.append(row)
        if clean_fees:
            admin.table("fees").insert(clean_fees).execute()
            print(f"   ✓ {len(clean_fees)} dòng phí")

    print("\n✅ Hoàn tất import!")
    print("   Đăng nhập app bằng các tài khoản trong USERS (mật khẩu mặc định: xem cột password).")


if __name__ == "__main__":
    main()
