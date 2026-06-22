"""CRM TCL Logistics v2 — Streamlit + Supabase (login, phân quyền, lịch sử).

Chạy:
    pip install -r requirements.txt
    python -m streamlit run app.py

Đăng nhập bằng tài khoản đã tạo lúc import (vd: giamdoc@tcl.com / tcl@2026).
Phân quyền do Supabase RLS xử lý — app chỉ hiển thị theo quyền.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import db

LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"


def logo_exists() -> bool:
    return LOGO_PATH.exists()

st.set_page_config(page_title="CRM TCL Logistics", page_icon="📦", layout="wide")


def inject_css() -> None:
    """Tải font + CSS tuỳ biến cho toàn app."""
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

          html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }

          /* Nền tổng thể nhẹ nhàng */
          .stApp { background: #F4F7FC; }
          .main .block-container { padding-top: 2rem; max-width: 1300px; }

          /* Tiêu đề trang */
          h1 { font-weight: 800 !important; letter-spacing: -0.5px; color: #1B2A6B; }
          h2, h3, h4 { font-weight: 700 !important; color: #1F2937; }

          /* Sidebar - navy thương hiệu TCL */
          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #16235C 0%, #1B2A6B 100%);
          }
          [data-testid="stSidebar"] * { color: #E8EEF7 !important; }
          [data-testid="stSidebar"] .stRadio label { color: #E8EEF7 !important; }
          [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: #A9B6D9 !important; }
          /* Logo TCL trên nền trắng bo tròn trong sidebar */
          [data-testid="stSidebar"] [data-testid="stImage"] {
            background:#fff; border-radius:14px; padding:10px; margin-bottom:6px;
          }
          /* Menu điều hướng tự dựng */
          [data-testid="stSidebar"] .stButton > button {
            background: transparent !important;
            color: #C9D6EE !important;
            border: none !important;
            box-shadow: none !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 15px !important;
            text-align: left !important;
            justify-content: flex-start !important;
            padding: 9px 14px !important;
            border-radius: 10px !important;
          }
          [data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.10) !important;
            color: #FFFFFF !important;
            transform: none !important;
          }
          [data-testid="stSidebar"] .stButton > button p { font-weight: 600 !important; }
          .nav-active {
            background: linear-gradient(135deg,#C0140A,#E8483B);
            color: #fff !important; font-weight: 700; font-size: 15px;
            font-family: 'Inter', sans-serif;
            padding: 9px 14px; border-radius: 10px; margin: 2px 0;
            box-shadow: 0 3px 10px rgba(192,20,10,0.30);
          }
          /* Giảm khoảng cách giữa các mục menu cho gọn, thẳng hàng */
          [data-testid="stSidebar"] .stButton { margin: 0 !important; }
          [data-testid="stSidebar"] [data-testid="stElementContainer"] { margin-bottom: 2px !important; }

          /* Khung (card) bao quanh nội dung - giống bố cục CRM chuyên nghiệp */
          [data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border: 1px solid #EAF0F9 !important;
            border-radius: 16px;
            box-shadow: 0 1px 4px rgba(15,36,71,0.05);
            padding: 6px 4px;
          }
          [data-testid="stVerticalBlockBorderWrapper"] h5 {
            color: #64748B !important; font-weight: 700 !important;
            font-size: 0.95rem !important; margin-bottom: 6px;
          }
          /* Expander trong sidebar (form đổi mật khẩu): nền trắng -> chữ tối */
          [data-testid="stSidebar"] [data-testid="stExpander"] summary,
          [data-testid="stSidebar"] [data-testid="stExpander"] summary * { color:#E8EEF7 !important; }
          [data-testid="stSidebar"] [data-testid="stExpander"] label,
          [data-testid="stSidebar"] [data-testid="stExpander"] label *,
          [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stAlert"] * {
            color:#1F2937 !important;
          }
          [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button {
            background:#1B2A6B !important; border:none !important;
            border-radius:10px !important; font-weight:700 !important;
          }
          [data-testid="stSidebar"] [data-testid="stFormSubmitButton"] button * { color:#fff !important; }

          /* Card trắng cho nội dung chính */
          [data-testid="stDataFrame"] {
            border-radius: 12px; overflow: hidden;
            box-shadow: 0 1px 3px rgba(15,36,71,0.08);
          }

          /* st.metric -> dạng thẻ */
          [data-testid="stMetric"] {
            background: #FFFFFF; padding: 16px 18px; border-radius: 14px;
            box-shadow: 0 1px 4px rgba(15,36,71,0.06); border: 1px solid #EAF0F9;
          }
          [data-testid="stMetricLabel"] p { font-weight: 600; color: #64748B; }
          [data-testid="stMetricValue"] { font-weight: 800; color: #0F2447; }

          /* KPI card gradient (dùng ở Dashboard) */
          .kpi {
            border-radius: 16px; padding: 20px 22px; color: #fff;
            box-shadow: 0 6px 18px rgba(14,95,216,0.18);
          }
          .kpi .lbl { font-size: 0.85rem; font-weight: 600; opacity: 0.92; margin: 0; }
          .kpi .val { font-size: 1.7rem; font-weight: 800; margin: 6px 0 0 0; line-height: 1.1; }
          .kpi.blue   { background: linear-gradient(135deg,#1B2A6B,#2E4BA0); }
          .kpi.green  { background: linear-gradient(135deg,#0F9D6B,#34D399); }
          .kpi.amber  { background: linear-gradient(135deg,#D97706,#FBBF24); }
          .kpi.red    { background: linear-gradient(135deg,#C0140A,#E8483B); }
          .kpi-delta  { font-size: 0.78rem; font-weight: 600; opacity: 0.95; margin-top: 6px; }

          /* Header trang */
          .page-header { display:flex; align-items:center; gap:14px; margin-bottom: 10px; }
          .ph-icon { font-size: 1.9rem; background:#fff; border:1px solid #EAF0F9;
                     width:54px; height:54px; border-radius:14px; display:flex;
                     align-items:center; justify-content:center;
                     box-shadow:0 1px 4px rgba(15,36,71,0.06); }
          .ph-title { font-size: 1.7rem; font-weight: 800; color:#1B2A6B; line-height:1.1; }
          .ph-sub { color:#64748B; font-size: 0.9rem; margin-top:2px; }

          /* Thẻ Kanban */
          .kan-col { background:#EEF2FA; border-radius:14px; padding:10px; min-height:120px; }
          .kan-col h5 { margin:4px 8px 10px; color:#1B2A6B; }
          .kan-card { background:#fff; border-radius:10px; padding:10px 12px; margin-bottom:8px;
                      box-shadow:0 1px 3px rgba(15,36,71,0.08); border-left:3px solid #2E4BA0; }
          .kan-card .t { font-weight:700; color:#1F2937; font-size:0.9rem; }
          .kan-card .m { color:#64748B; font-size:0.8rem; margin-top:2px; }
          .kan-card .p { color:#0F9D6B; font-weight:700; font-size:0.85rem; margin-top:4px; }

          /* Hồ sơ khách 360 */
          .profile-head { display:flex; align-items:center; gap:18px; background:#fff;
            border:1px solid #EAF0F9; border-radius:16px; padding:20px 22px;
            box-shadow:0 1px 4px rgba(15,36,71,0.06); margin-bottom:12px; }
          .avatar { width:64px; height:64px; border-radius:50%; flex:0 0 64px;
            background:linear-gradient(135deg,#1B2A6B,#2E4BA0); color:#fff;
            display:flex; align-items:center; justify-content:center;
            font-size:1.5rem; font-weight:800; }
          .pname { font-size:1.4rem; font-weight:800; color:#1B2A6B; line-height:1.1; }
          .pcompany { color:#64748B; font-size:0.92rem; margin-top:3px; }
          .ptags { margin-top:8px; display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
          .tag { padding:3px 12px; border-radius:999px; font-size:0.78rem; font-weight:700; }
          .tag-green { background:#DCFCE7; color:#166534; }
          .tag-amber { background:#FEF3C7; color:#92400E; }
          .tag-red   { background:#FEE2E2; color:#991B1B; }
          .tag-gray  { background:#E5E7EB; color:#374151; }
          .tag-blue  { background:#DBEAFE; color:#1E40AF; }
          .chips { display:flex; gap:10px; flex-wrap:wrap; margin:4px 0 6px; }
          .chip { background:#F4F7FC; border:1px solid #EAF0F9; border-radius:10px;
            padding:7px 12px; font-size:0.88rem; color:#1F2937; }
          .chip b { color:#64748B; font-weight:600; }
          /* Kết quả tìm kiếm */
          .sr-card { background:#fff; border:1px solid #EAF0F9; border-radius:12px;
            padding:10px 14px; margin-bottom:8px; box-shadow:0 1px 3px rgba(15,36,71,0.06);
            display:flex; align-items:center; gap:12px; }
          .sr-av { width:40px; height:40px; border-radius:50%; flex:0 0 40px;
            background:linear-gradient(135deg,#1B2A6B,#2E4BA0); color:#fff;
            display:flex; align-items:center; justify-content:center;
            font-size:0.95rem; font-weight:800; }
          .sr-card .t { font-weight:700; color:#1B2A6B; }
          .sr-card .m { color:#64748B; font-size:0.85rem; margin-top:2px; }

          /* Nút bấm */
          .stButton > button {
            border-radius: 10px; font-weight: 600; border: none;
            transition: transform .05s ease;
          }
          .stButton > button:hover { transform: translateY(-1px); }

          /* Expander */
          [data-testid="stExpander"] {
            border-radius: 12px; border: 1px solid #EAF0F9; background: #fff;
          }

          /* Login card */
          .login-wrap { max-width: 420px; margin: 4rem auto 0 auto; }
          .login-card {
            background:#fff; padding: 34px 32px; border-radius: 20px;
            box-shadow: 0 12px 40px rgba(15,36,71,0.12); border:1px solid #EAF0F9;
          }
          .login-logo { font-size: 2.4rem; text-align:center; }
          .login-title { text-align:center; font-weight:800; color:#0F2447; margin:6px 0 2px; font-size:1.6rem; }
          .login-sub { text-align:center; color:#64748B; margin-bottom: 18px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi(col, label: str, value: str, variant: str = "blue", delta: str | None = None) -> None:
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    col.markdown(
        f"""<div class="kpi {variant}"><p class="lbl">{label}</p>"""
        f"""<p class="val">{value}</p>{delta_html}</div>""",
        unsafe_allow_html=True,
    )


def _status_css(val) -> str:
    """Trả về CSS nền/chữ theo ý nghĩa trạng thái (dùng tô màu ô trong bảng)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).lower()
    good = ("đã chốt", "đã thanh toán", "đã giao", "đã nhận", "hoàn tất", "done", "paid")
    bad = ("chưa", "từ chối", "hủy", "huỷ", "trễ", "delay", "nợ", "quá hạn")
    warn = ("đang", "gửi báo giá", "tư vấn", "trung chuyển", "hải quan", "rời cảng", "chờ")
    if any(k in s for k in good):
        return "background-color:#DCFCE7; color:#166534;"
    if any(k in s for k in bad):
        return "background-color:#FEE2E2; color:#991B1B;"
    if any(k in s for k in warn):
        return "background-color:#FEF3C7; color:#92400E;"
    return ""


def style_status(df: pd.DataFrame, cols: list[str]):
    """Tô màu các cột trạng thái trong DataFrame; trả về Styler cho st.dataframe."""
    present = [c for c in cols if c in df.columns]

    def _apply(col: pd.Series):
        if col.name in present:
            return [_status_css(v) for v in col]
        return [""] * len(col)

    return df.style.apply(_apply, axis=0)


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    sub = f'<div class="ph-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""<div class="page-header"><div class="ph-icon">{icon}</div>
        <div><div class="ph-title">{title}</div>{sub}</div></div>""",
        unsafe_allow_html=True,
    )


ROLE_LABEL = {"giam_doc": "Giám đốc", "sale": "Sale", "ke_toan": "Kế toán"}
PHAN_LOAI_OPTS = ["Khách Hàng Thường Xuyên", "Khách hàng thi thoảng", "Khách Hàng Cũ",
                  "Khách Vãng Lai", "Khách hàng đã mất", "Đang Tư Vấn"]
TT_GIAO_DICH_OPTS = ["Đã chốt", "Đã gửi báo giá", "Đang tư vấn", "Từ chối dịch vụ"]
TT_HANG_OPTS = ["Đã nhận hàng", "Đã giao hàng", "Đang trung chuyển",
                "Đang làm hải quan", "Đã rời cảng"]
TT_THANHTOAN_OPTS = ["Đã thanh toán", "Chưa thanh toán"]


# ---------- Helpers ----------

def can_edit() -> bool:
    return db.role() in ("giam_doc", "sale")


def can_reassign() -> bool:
    return db.role() == "giam_doc"


def can_delete() -> bool:
    return db.role() == "giam_doc"


def _select_page(name: str) -> None:
    """Callback nút điều hướng: đổi trang + xoá ô tìm kiếm."""
    st.session_state["page"] = name
    st.session_state["gsearch"] = ""


def _go_customer(name: str) -> None:
    """Callback: mở hồ sơ 1 khách từ kết quả tìm kiếm."""
    st.session_state["page"] = "Khách hàng"
    st.session_state["cust_pick"] = name
    st.session_state["gsearch"] = ""


def _s(v) -> str:
    """Đổi None/NaN -> '' (NaN là float nên 'NaN or \"\"' không hoạt động)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _initials(name) -> str:
    parts = str(name or "").split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _tag_class(phan_loai) -> str:
    s = str(phan_loai or "").lower()
    if "thường xuyên" in s or "vip" in s:
        return "tag-green"
    if "đã mất" in s:
        return "tag-red"
    if "tư vấn" in s:
        return "tag-amber"
    if "vãng lai" in s or "thi thoảng" in s or "cũ" in s:
        return "tag-gray"
    return "tag-blue"


def can_audit() -> bool:
    return db.role() in ("giam_doc", "ke_toan")


def orders_with_names(orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Gắn tên khách vào đơn hàng (join customer_id → ten_kh)."""
    if orders.empty:
        return orders.assign(ten_kh=pd.Series(dtype=str))
    names = customers[["id", "ten_kh"]].rename(columns={"id": "customer_id"})
    return orders.merge(names, on="customer_id", how="left")


def clean_payload(d: dict) -> dict:
    """Bỏ các field rỗng/None để insert/update gọn gàng."""
    out = {}
    for k, v in d.items():
        if v is None or (isinstance(v, str) and v.strip() == ""):
            continue
        if hasattr(v, "isoformat"):   # date
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# ---------- Màn hình đăng nhập ----------

def login_screen() -> None:
    left, mid, right = st.columns([1, 1.4, 1])
    with mid:
        if logo_exists():
            st.image(str(LOGO_PATH), use_container_width=True)
        else:
            st.markdown('<div class="login-logo">📦</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="login-title">CRM TCL Logistics</div>
            <div class="login-sub">Đăng nhập để tiếp tục</div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login"):
            email = st.text_input("Email", placeholder="giamdoc@tcl.com")
            password = st.text_input("Mật khẩu", type="password")
            ok = st.form_submit_button("Đăng nhập", use_container_width=True, type="primary")
        if ok:
            success, msg = db.login(email, password)
            if success:
                st.rerun()
            else:
                st.error(msg)


# ---------- Trang 1: Dashboard ----------

def _mom_delta(o: pd.DataFrame, value_col: str) -> str | None:
    """So sánh tháng có dữ liệu mới nhất với tháng liền trước."""
    if o.empty or "ngay_dat" not in o:
        return None
    od = o.dropna(subset=["ngay_dat"])
    if od.empty:
        return None
    per = od["ngay_dat"].dt.to_period("M")
    latest = per.max()
    cur = od.loc[per == latest, value_col].sum()
    prev = od.loc[per == latest - 1, value_col].sum()
    if prev and prev != 0:
        pct = (cur - prev) / abs(prev) * 100
        arrow = "▲" if pct >= 0 else "▼"
        return f"{arrow} {abs(pct):.0f}% so với tháng trước"
    return None


def _filter_period(o: pd.DataFrame, choice: str) -> pd.DataFrame:
    """Lọc đơn theo khoảng thời gian dựa trên ngày đặt."""
    if choice == "Tất cả" or o.empty or "ngay_dat" not in o:
        return o
    days = {"30 ngày": 30, "90 ngày": 90, "12 tháng": 365}.get(choice)
    if not days:
        return o
    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=days)
    return o[o["ngay_dat"] >= cutoff]


def page_dashboard(client, customers, orders) -> None:
    head_l, head_r = st.columns([3, 1])
    with head_l:
        page_header("📊", "Tổng quan", "Bức tranh kinh doanh tổng thể")
    with head_r:
        period = st.selectbox("Khoảng thời gian",
                              ["Tất cả", "12 tháng", "90 ngày", "30 ngày"],
                              label_visibility="collapsed")

    o_all = orders_with_names(orders, customers)
    o = _filter_period(o_all, period)

    total_profit = o["loi_nhuan"].sum() if "loi_nhuan" in o else 0
    total_revenue = o["gia_ban"].sum() if "gia_ban" in o else 0
    total_customers = len(customers)
    unpaid = int(o["tinh_trang_thanh_toan"].astype(str).str.contains(
        "Chưa", case=False, na=False).sum()) if "tinh_trang_thanh_toan" in o else 0

    # --- Hàng 1: KPI (khung trái) + Donut tỷ lệ thành công (khung phải) ---
    row1_l, row1_r = st.columns([3, 2])
    with row1_l:
        with st.container(border=True):
            st.markdown("##### Chỉ số chính")
            k1, k2 = st.columns(2)
            kpi(k1, "💰 Tổng lợi nhuận", db.fmt_usd(total_profit), "blue", _mom_delta(o, "loi_nhuan"))
            kpi(k2, "📈 Tổng doanh thu", db.fmt_usd(total_revenue), "green", _mom_delta(o, "gia_ban"))
            st.markdown("")
            k3, k4 = st.columns(2)
            kpi(k3, "👥 Khách hàng", f"{total_customers}", "amber")
            kpi(k4, "⚠️ Đơn chưa thanh toán", f"{unpaid}", "red")

    with row1_r:
        with st.container(border=True):
            st.markdown("##### Tỷ lệ đơn thành công")
            done_mask = o["trang_thai_hang"].astype(str).str.contains(
                "Đã giao|Đã nhận", case=False, na=False) if "trang_thai_hang" in o else pd.Series(dtype=bool)
            total_o = len(o)
            done = int(done_mask.sum()) if total_o else 0
            rate = (done / total_o * 100) if total_o else 0
            fig = px.pie(values=[done, max(total_o - done, 0)],
                         names=["Thành công", "Còn lại"], hole=0.72,
                         color_discrete_sequence=["#0F9D6B", "#E5E7EB"])
            fig.update_traces(textinfo="none", sort=False)
            fig.update_layout(height=260, margin=dict(l=0, r=0, t=0, b=0),
                              showlegend=False,
                              annotations=[dict(text=f"<b>{rate:.1f}%</b>", x=0.5, y=0.5,
                                                font_size=26, showarrow=False)])
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"{done}/{total_o} đơn đã giao/nhận")

    # --- Hàng 2: Báo cáo doanh thu (khung trái) + Trạng thái hàng (khung phải) ---
    row2_l, row2_r = st.columns([3, 2])
    with row2_l:
        with st.container(border=True):
            st.markdown("##### Báo cáo doanh thu & lợi nhuận theo tháng")
            if not o.empty and "ngay_dat" in o and o["ngay_dat"].notna().any():
                m = (o.dropna(subset=["ngay_dat"])
                     .assign(thang=lambda d: d["ngay_dat"].dt.to_period("M").astype(str))
                     .groupby("thang", as_index=False)[["gia_ban", "loi_nhuan"]].sum()
                     .sort_values("thang"))
                fig = px.bar(m, x="thang", y=["gia_ban", "loi_nhuan"], barmode="group",
                             labels={"thang": "Tháng", "value": "USD", "variable": ""},
                             color_discrete_map={"gia_ban": "#1B2A6B", "loi_nhuan": "#0F9D6B"})
                fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                                  legend_title_text="")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu theo tháng.")

    with row2_r:
        with st.container(border=True):
            st.markdown("##### Tỷ lệ trạng thái hàng hoá")
            if not o.empty and "trang_thai_hang" in o:
                sc = o["trang_thai_hang"].fillna("Chưa rõ").replace("", "Chưa rõ").value_counts().reset_index()
                sc.columns = ["Trạng thái", "Số đơn"]
                fig = px.pie(sc, values="Số đơn", names="Trạng thái", hole=0.5,
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                                  legend=dict(orientation="h", y=-0.1))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu.")

    # --- Hàng 3: Top khách hàng (khung) ---
    with st.container(border=True):
        st.markdown("##### 🏆 Top 5 khách hàng theo lợi nhuận")
        if not o.empty and o["loi_nhuan"].notna().any():
            top5 = (o.dropna(subset=["ten_kh"]).groupby("ten_kh", as_index=False)["loi_nhuan"]
                    .sum().sort_values("loi_nhuan", ascending=False).head(5))
            fig = px.bar(top5, x="loi_nhuan", y="ten_kh", orientation="h",
                         color="loi_nhuan", color_continuous_scale="Blues",
                         labels={"loi_nhuan": "Lợi nhuận (USD)", "ten_kh": "Khách hàng"})
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                              yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu lợi nhuận.")


# ---------- Trang 2: Khách hàng ----------

def page_customers(client, customers, orders, profiles) -> None:
    page_header("👥", "Khách hàng", "Quản lý hồ sơ & lịch sử giao dịch")

    if can_edit():
        with st.expander("➕ Thêm khách hàng mới"):
            _form_add_customer(client, profiles)

    if customers.empty:
        st.info("Chưa có khách hàng nào (theo quyền của bạn).")
        return

    q = st.text_input("🔍 Tìm theo tên hoặc mã KH", "")
    df = customers
    if q:
        ql = q.lower()
        df = df[df["ten_kh"].astype(str).str.lower().str.contains(ql, na=False)
                | df["ma_kh"].astype(str).str.lower().str.contains(ql, na=False)]

    st.markdown(f"**{len(df)} khách hàng**")
    cols = [c for c in ["ma_kh", "ten_kh", "ten_cong_ty", "phan_loai", "quoc_gia", "email", "sdt"] if c in df.columns]
    st.dataframe(df[cols].rename(columns={
        "ma_kh": "Mã KH", "ten_kh": "Tên KH", "ten_cong_ty": "Công ty",
        "phan_loai": "Phân loại", "quoc_gia": "Quốc gia", "email": "Email", "sdt": "SĐT"}),
        use_container_width=True, hide_index=True)

    st.divider()
    pick = st.selectbox("Xem chi tiết khách hàng",
                        df["ten_kh"].tolist(), key="cust_pick")
    row = df[df["ten_kh"] == pick].iloc[0]

    # --- Header hồ sơ 360 ---
    ten = _s(row.get("ten_kh")) or "—"
    company = _s(row.get("ten_cong_ty"))
    country = _s(row.get("quoc_gia"))
    sub = " · ".join(x for x in [company, (f"🌏 {country}" if country else "")] if x)
    pl = _s(row.get("phan_loai"))
    tag = f'<span class="tag {_tag_class(pl)}">{pl}</span>' if pl else ""
    macode = f'<span class="tag tag-gray">Mã: {_s(row.get("ma_kh"))}</span>' if _s(row.get("ma_kh")) else ""
    st.markdown(
        f'<div class="profile-head"><div class="avatar">{_initials(ten)}</div>'
        f'<div><div class="pname">{ten}</div>'
        f'<div class="pcompany">{sub or "—"}</div>'
        f'<div class="ptags">{tag}{macode}</div></div></div>',
        unsafe_allow_html=True)

    # --- Thông tin liên hệ dạng chip ---
    bday = row.get("ngay_sinh_nhat").date().strftime("%d/%m/%Y") if pd.notna(row.get("ngay_sinh_nhat")) else ""
    chips = [
        ("✉️ Email", _s(row.get("email"))), ("📞 SĐT", _s(row.get("sdt"))),
        ("👤 Liên hệ", _s(row.get("nguoi_lien_he"))), ("💬 Kênh", _s(row.get("kenh_giao_dich"))),
        ("🎂 Sinh nhật", bday), ("💍 Hôn nhân", _s(row.get("tinh_trang_hon_nhan"))),
        ("🧠 Tính cách", _s(row.get("tinh_cach"))),
    ]
    chip_html = "".join(f'<span class="chip"><b>{lbl}:</b> {val}</span>'
                        for lbl, val in chips if val)
    if chip_html:
        st.markdown(f'<div class="chips">{chip_html}</div>', unsafe_allow_html=True)
    if _s(row.get("ghi_chu")):
        st.markdown(f"📝 **Ghi chú chung:** {_s(row.get('ghi_chu'))}")

    if can_edit():
        with st.expander("✏️ Sửa thông tin khách này"):
            _form_edit_customer(client, row, profiles)

    if can_delete():
        with st.expander("🗑️ Xoá khách hàng này"):
            _form_delete_customer(client, row, orders)

    # Ghi chú & nhắc việc
    _section_notes(client, row)

    # Lịch sử đơn hàng
    st.markdown("#### 📦 Lịch sử đơn hàng")
    cust_orders = orders[orders["customer_id"] == row["id"]] if not orders.empty else pd.DataFrame()
    if cust_orders.empty:
        st.info("Khách này chưa có đơn hàng.")
        return
    a, b, c = st.columns(3)
    a.metric("Số đơn", f"{len(cust_orders)}")
    b.metric("Doanh thu", db.fmt_usd(cust_orders["gia_ban"].sum()))
    c.metric("Lợi nhuận", db.fmt_usd(cust_orders["loi_nhuan"].sum()))
    hc = [x for x in ["ma_dh", "ngay_dat", "ten_hang", "gia_ban", "loi_nhuan", "trang_thai_hang", "tinh_trang_thanh_toan"] if x in cust_orders.columns]
    hist = cust_orders[hc].rename(columns={
        "ma_dh": "Mã ĐH", "ngay_dat": "Ngày đặt", "ten_hang": "Hàng",
        "gia_ban": "Giá bán", "loi_nhuan": "Lợi nhuận",
        "trang_thai_hang": "Trạng thái", "tinh_trang_thanh_toan": "Thanh toán"})
    st.dataframe(style_status(hist, ["Trạng thái", "Thanh toán"]),
                 use_container_width=True, hide_index=True)


def _section_notes(client, row) -> None:
    """Ghi chú & nhắc follow-up cho 1 khách hàng."""
    st.markdown("#### 📝 Ghi chú & nhắc việc")
    notes = db.fetch_notes(client, int(row["id"]))

    if can_edit():
        with st.form(f"add_note_{row['id']}", clear_on_submit=True):
            noi_dung = st.text_area("Thêm ghi chú", placeholder="VD: Đã gọi, khách hẹn tuần sau chốt...")
            cc1, cc2 = st.columns([1, 1])
            has_followup = cc1.checkbox("Đặt lịch nhắc lại")
            fu_date = cc2.date_input("Ngày nhắc", value=None, disabled=not has_followup)
            if st.form_submit_button("Lưu ghi chú") and noi_dung.strip():
                db.add_note(client, int(row["id"]), noi_dung.strip(),
                            fu_date if has_followup else None)
                st.success("Đã lưu ghi chú.")
                st.rerun()

    if notes.empty:
        st.caption("Chưa có ghi chú nào.")
        return
    for _, n in notes.iterrows():
        when = n["created_at"].strftime("%d/%m/%Y") if pd.notna(n["created_at"]) else ""
        fu = ""
        if pd.notna(n.get("follow_up_date")):
            d = n["follow_up_date"].date()
            overdue = d < pd.Timestamp.today().date()
            flag = "🔴 Quá hạn" if (overdue and not n["done"]) else "🔔 Nhắc"
            fu = f" · {flag}: {d.strftime('%d/%m/%Y')}"
        done_mark = "✅ " if n["done"] else ""
        cols = st.columns([6, 1])
        cols[0].markdown(f"{done_mark}**{n['noi_dung']}**  \n<span style='color:#94A3B8;font-size:0.8rem'>{when}{fu}</span>",
                         unsafe_allow_html=True)
        if can_edit() and pd.notna(n.get("follow_up_date")):
            label = "Mở lại" if n["done"] else "Xong"
            if cols[1].button(label, key=f"note_done_{n['id']}"):
                db.set_note_done(client, int(n["id"]), not n["done"])
                st.rerun()


def _form_add_customer(client, profiles) -> None:
    with st.form("add_cust", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ten_kh = c1.text_input("Tên khách hàng *")
        ma_kh = c2.text_input("Mã KH")
        cong_ty = c1.text_input("Công ty")
        email = c2.text_input("Email")
        sdt = c1.text_input("Số điện thoại")
        quoc_gia = c2.text_input("Quốc gia")
        phan_loai = c1.selectbox("Phân loại", [""] + PHAN_LOAI_OPTS)
        kenh = c2.text_input("Kênh giao dịch")
        tinh_cach = st.text_input("Tính cách")
        ghi_chu = st.text_area("Ghi chú")

        sale_id = st.session_state["user_id"]
        if can_reassign() and not profiles.empty:
            opts = profiles.set_index("id")["ho_ten"].to_dict()
            sale_id = st.selectbox("Sale phụ trách", list(opts.keys()),
                                   format_func=lambda i: opts.get(i, i),
                                   index=list(opts.keys()).index(st.session_state["user_id"])
                                   if st.session_state["user_id"] in opts else 0)
        ok = st.form_submit_button("Lưu khách hàng")
    if ok:
        if not ten_kh.strip():
            st.error("Phải nhập Tên khách hàng.")
            return
        payload = clean_payload({
            "ten_kh": ten_kh, "ma_kh": ma_kh, "ten_cong_ty": cong_ty, "email": email,
            "sdt": sdt, "quoc_gia": quoc_gia, "phan_loai": phan_loai, "kenh_giao_dich": kenh,
            "tinh_cach": tinh_cach, "ghi_chu": ghi_chu, "sale_id": sale_id,
        })
        try:
            client.table("customers").insert(payload).execute()
            st.success(f"Đã thêm khách: {ten_kh}")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi lưu: {e}")


def _form_edit_customer(client, row, profiles) -> None:
    with st.form(f"edit_cust_{row['id']}"):
        c1, c2 = st.columns(2)
        ten_kh = c1.text_input("Tên khách hàng", _s(row.get("ten_kh")))
        cong_ty = c2.text_input("Công ty", _s(row.get("ten_cong_ty")))
        email = c1.text_input("Email", _s(row.get("email")))
        sdt = c2.text_input("Số điện thoại", _s(row.get("sdt")))
        quoc_gia = c1.text_input("Quốc gia", _s(row.get("quoc_gia")))
        pl_idx = PHAN_LOAI_OPTS.index(row["phan_loai"]) + 1 if row.get("phan_loai") in PHAN_LOAI_OPTS else 0
        phan_loai = c2.selectbox("Phân loại", [""] + PHAN_LOAI_OPTS, index=pl_idx)
        tinh_cach = st.text_input("Tính cách", _s(row.get("tinh_cach")))
        ghi_chu = st.text_area("Ghi chú", _s(row.get("ghi_chu")))

        new_sale = None
        if can_reassign() and not profiles.empty:
            opts = profiles.set_index("id")["ho_ten"].to_dict()
            keys = list(opts.keys())
            cur = row.get("sale_id")
            new_sale = st.selectbox("🔄 Đổi sale phụ trách", keys,
                                    format_func=lambda i: opts.get(i, i),
                                    index=keys.index(cur) if cur in keys else 0)
        ok = st.form_submit_button("Cập nhật")
    if ok:
        payload = {
            "ten_kh": ten_kh, "ten_cong_ty": cong_ty, "email": email, "sdt": sdt,
            "quoc_gia": quoc_gia, "phan_loai": phan_loai or None,
            "tinh_cach": tinh_cach, "ghi_chu": ghi_chu,
        }
        if new_sale is not None:
            payload["sale_id"] = new_sale
        try:
            client.table("customers").update(payload).eq("id", int(row["id"])).execute()
            st.success("Đã cập nhật.")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")


def _form_delete_customer(client, row, orders) -> None:
    n_orders = int((orders["customer_id"] == row["id"]).sum()) if not orders.empty else 0
    st.warning(
        f"⚠️ Sắp xoá khách **{row.get('ten_kh')}**. "
        + (f"Khách này có **{n_orders} đơn hàng** — các đơn sẽ KHÔNG bị xoá nhưng sẽ mất liên kết với khách (cần gán lại sau)."
           if n_orders else "Khách này chưa có đơn hàng.")
    )
    confirm = st.checkbox(f"Tôi xác nhận muốn xoá '{row.get('ten_kh')}'", key=f"del_confirm_{row['id']}")
    if st.button("🗑️ Xoá vĩnh viễn", type="primary", disabled=not confirm, key=f"del_btn_{row['id']}"):
        try:
            client.table("customers").delete().eq("id", int(row["id"])).execute()
            st.session_state.pop("cust_pick", None)  # tránh selectbox trỏ tới khách đã xoá
            st.success(f"Đã xoá khách: {row.get('ten_kh')}")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi xoá: {e}")


# ---------- Trang 3: Đơn hàng ----------

def page_orders(client, customers, orders) -> None:
    page_header("📦", "Đơn hàng", "Toàn bộ giao dịch & bộ lọc")
    o = orders_with_names(orders, customers)

    if can_edit():
        with st.expander("➕ Thêm đơn hàng mới"):
            _form_add_order(client, customers)

    if o.empty:
        st.info("Chưa có đơn hàng nào.")
        return

    f1, f2, f3 = st.columns(3)

    def opts(col):
        vals = o[col].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist() if col in o else []
        return ["(Tất cả)"] + sorted(vals)

    gd = f1.selectbox("Tình trạng giao dịch", opts("tinh_trang_giao_dich"))
    tt = f2.selectbox("Tình trạng thanh toán", opts("tinh_trang_thanh_toan"))
    th = f3.selectbox("Trạng thái hàng hoá", opts("trang_thai_hang"))

    df = o
    if gd != "(Tất cả)":
        df = df[df["tinh_trang_giao_dich"].astype(str) == gd]
    if tt != "(Tất cả)":
        df = df[df["tinh_trang_thanh_toan"].astype(str) == tt]
    if th != "(Tất cả)":
        df = df[df["trang_thai_hang"].astype(str) == th]

    # Tuỳ chọn chỉ hiện đơn đã có ngày đặt (ẩn các dòng trống ngày)
    only_dated = st.checkbox("📅 Chỉ hiện đơn đã có ngày đặt (sắp theo mới nhất)", value=True)
    if only_dated and "ngay_dat" in df.columns:
        df = df[df["ngay_dat"].notna()]

    # Sắp xếp: ngày mới nhất lên đầu, đơn trống ngày xuống cuối
    if "ngay_dat" in df.columns:
        df = df.sort_values("ngay_dat", ascending=False, na_position="last")

    st.markdown(f"**{len(df)} / {len(o)} đơn**")
    a, b, c = st.columns(3)
    a.metric("Doanh thu", db.fmt_usd(df["gia_ban"].sum()))
    b.metric("Lợi nhuận", db.fmt_usd(df["loi_nhuan"].sum()))
    margin = (df["loi_nhuan"].sum() / df["gia_ban"].sum() * 100) if df["gia_ban"].sum() else 0
    c.metric("Tỷ suất LN", f"{margin:.1f}%")

    show_cols = [x for x in ["ma_dh", "ngay_dat", "ten_kh", "ten_hang", "incoterm",
                             "khoi_luong", "cang_di", "cang_den", "gia_ban", "loi_nhuan",
                             "trang_thai_hang", "tinh_trang_thanh_toan", "eta"] if x in df.columns]
    show = df[show_cols].rename(columns={
        "ma_dh": "Mã ĐH", "ngay_dat": "Ngày đặt", "ten_kh": "Khách hàng", "ten_hang": "Hàng",
        "incoterm": "Incoterm", "khoi_luong": "KL", "cang_di": "Cảng đi", "cang_den": "Cảng đến",
        "gia_ban": "Giá bán", "loi_nhuan": "Lợi nhuận", "trang_thai_hang": "TT hàng",
        "tinh_trang_thanh_toan": "Thanh toán", "eta": "ETA"})
    if can_edit():
        st.caption("✏️ Bạn có thể sửa trực tiếp các ô **Hàng, Giá mua, Giá bán, TT hàng, "
                   "Thanh toán, ETA** ngay trong bảng, sau đó bấm **Lưu thay đổi**.")
        _editable_orders(client, df)
    else:
        st.dataframe(style_status(show, ["TT hàng", "Thanh toán"]),
            use_container_width=True, hide_index=True,
            column_config={
                "Giá bán": st.column_config.NumberColumn(format="$%.2f"),
                "Lợi nhuận": st.column_config.NumberColumn(format="$%.2f"),
                "Ngày đặt": st.column_config.DateColumn(format="DD/MM/YYYY"),
                "ETA": st.column_config.DateColumn(format="DD/MM/YYYY")})
    download_excel("📥 Tải danh sách đơn (Excel)", {"Don hang": show},
                   "bao_cao_don_hang.xlsx")

    # Xem phí — chọn đơn theo nhãn dễ đọc (khách + hàng + ngày), không phải mã
    st.divider()
    st.markdown("#### 💸 Chi tiết phí của đơn")
    fee_opts = {int(r["id"]): _order_label(r) for _, r in df.iterrows()}
    pick_fee = st.selectbox("Chọn đơn để xem phí", ["(Chọn)"] + list(fee_opts.keys()),
                            format_func=lambda i: "(Chọn)" if i == "(Chọn)" else fee_opts[i],
                            key="fee_pick")
    if pick_fee != "(Chọn)":
        oid = int(pick_fee)
        fees = db.fetch_fees(client, oid)
        if fees.empty:
            st.info("Đơn này chưa có phí.")
        else:
            st.dataframe(fees[["noi_dung_phi", "so_tien", "loai"]].rename(columns={
                "noi_dung_phi": "Nội dung", "so_tien": "Số tiền", "loai": "Loại"}),
                use_container_width=True, hide_index=True,
                column_config={"Số tiền": st.column_config.NumberColumn(format="$%.2f")})
            st.caption(f"**Tổng phí:** {db.fmt_usd(fees['so_tien'].sum())}")


def _order_label(r) -> str:
    """Nhãn dễ đọc cho 1 đơn: Khách – Hàng (ngày)."""
    ten = r.get("ten_kh") or "—"
    hang = r.get("ten_hang") or "(chưa có hàng)"
    d = ""
    if pd.notna(r.get("ngay_dat")):
        d = f" · {r['ngay_dat'].strftime('%d/%m/%Y')}"
    ma = f" [{r['ma_dh']}]" if r.get("ma_dh") else ""
    return f"{ten} – {hang}{d}{ma}"


def _editable_orders(client, df) -> None:
    """Bảng chỉnh sửa trực tiếp (kiểu Excel) + nút Lưu."""
    th_opts = sorted(set(TT_HANG_OPTS) | set(df["trang_thai_hang"].dropna().astype(str)))
    tt_opts = sorted(set(TT_THANHTOAN_OPTS) | set(df["tinh_trang_thanh_toan"].dropna().astype(str)))

    ed = pd.DataFrame({
        "Mã ĐH": df["ma_dh"].values,
        "Ngày đặt": df["ngay_dat"].values,
        "Khách hàng": df["ten_kh"].values,
        "Hàng": df["ten_hang"].values,
        "Giá mua": df["gia_mua"].values,
        "Giá bán": df["gia_ban"].values,
        "TT hàng": df["trang_thai_hang"].values,
        "Thanh toán": df["tinh_trang_thanh_toan"].values,
        "ETA": df["eta"].values,
    }, index=df["id"].values)

    edited = st.data_editor(
        ed, key="ord_editor", use_container_width=True, hide_index=True,
        disabled=["Mã ĐH", "Ngày đặt", "Khách hàng"],
        column_config={
            "Ngày đặt": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Giá mua": st.column_config.NumberColumn(format="$%.2f"),
            "Giá bán": st.column_config.NumberColumn(format="$%.2f"),
            "TT hàng": st.column_config.SelectboxColumn(options=th_opts, required=False),
            "Thanh toán": st.column_config.SelectboxColumn(options=tt_opts, required=False),
            "ETA": st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
    )

    def _txt(v):
        return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()

    def _num(v):
        return None if v is None or (isinstance(v, float) and pd.isna(v)) else float(v)

    def _diso(v):
        if v is None or (not hasattr(v, "isoformat") and pd.isna(v)):
            return None
        if hasattr(v, "date") and not isinstance(v, str):
            try:
                return v.date().isoformat()
            except Exception:
                pass
        return v.isoformat() if hasattr(v, "isoformat") else None

    if st.button("💾 Lưu thay đổi", type="primary", key="save_orders"):
        changes = 0
        for oid in ed.index:
            old, new = ed.loc[oid], edited.loc[oid]
            payload = {}
            if _txt(new["Hàng"]) != _txt(old["Hàng"]):
                payload["ten_hang"] = _txt(new["Hàng"]) or None
            if _txt(new["TT hàng"]) != _txt(old["TT hàng"]):
                payload["trang_thai_hang"] = _txt(new["TT hàng"]) or None
            if _txt(new["Thanh toán"]) != _txt(old["Thanh toán"]):
                payload["tinh_trang_thanh_toan"] = _txt(new["Thanh toán"]) or None
            gm_ch = _num(new["Giá mua"]) != _num(old["Giá mua"])
            gb_ch = _num(new["Giá bán"]) != _num(old["Giá bán"])
            if gm_ch:
                payload["gia_mua"] = _num(new["Giá mua"])
            if gb_ch:
                payload["gia_ban"] = _num(new["Giá bán"])
            if _diso(new["ETA"]) != _diso(old["ETA"]):
                payload["eta"] = _diso(new["ETA"])
            if gm_ch or gb_ch:
                payload["loi_nhuan"] = (_num(new["Giá bán"]) or 0) - (_num(new["Giá mua"]) or 0)
            if payload:
                try:
                    client.table("orders").update(payload).eq("id", int(oid)).execute()
                    changes += 1
                except Exception as e:
                    st.error(f"Lỗi khi lưu đơn id={oid}: {e}")
        if changes:
            st.success(f"Đã cập nhật {changes} đơn hàng.")
            st.rerun()
        else:
            st.info("Không có thay đổi nào để lưu.")


def _form_add_order(client, customers) -> None:
    if customers.empty:
        st.info("Cần có khách hàng trước khi thêm đơn.")
        return
    cust_map = customers.set_index("id")["ten_kh"].to_dict()
    with st.form("add_order", clear_on_submit=True):
        c1, c2 = st.columns(2)
        customer_id = c1.selectbox("Khách hàng *", list(cust_map.keys()),
                                   format_func=lambda i: cust_map.get(i, i))
        ma_dh = c2.text_input("Mã đơn hàng")
        ngay_dat = c1.date_input("Ngày đặt", value=None)
        ten_hang = c2.text_input("Tên hàng")
        incoterm = c1.text_input("Incoterm")
        khoi_luong = c2.text_input("Khối lượng", placeholder="vd: 11.5 kg, 4.74 cbm, 1x20'")
        cang_di = c1.text_input("Cảng đi")
        cang_den = c2.text_input("Cảng đến")
        gia_mua = c1.number_input("Giá mua (USD)", min_value=0.0, step=1.0, value=0.0)
        gia_ban = c2.number_input("Giá bán (USD)", min_value=0.0, step=1.0, value=0.0)
        tt_gd = c1.selectbox("Tình trạng giao dịch", [""] + TT_GIAO_DICH_OPTS)
        tt_hang = c2.selectbox("Trạng thái hàng hoá", [""] + TT_HANG_OPTS)
        eta = c1.date_input("ETA", value=None)
        tt_tt = c2.selectbox("Tình trạng thanh toán", [""] + TT_THANHTOAN_OPTS)
        ok = st.form_submit_button("Lưu đơn hàng")
    if ok:
        loi_nhuan = (gia_ban - gia_mua) if (gia_ban or gia_mua) else None
        payload = clean_payload({
            "customer_id": int(customer_id), "ma_dh": ma_dh, "ngay_dat": ngay_dat,
            "ten_hang": ten_hang, "incoterm": incoterm,
            "khoi_luong": khoi_luong or None, "cang_di": cang_di, "cang_den": cang_den,
            "gia_mua": gia_mua or None, "gia_ban": gia_ban or None, "loi_nhuan": loi_nhuan,
            "tinh_trang_giao_dich": tt_gd, "trang_thai_hang": tt_hang, "eta": eta,
            "tinh_trang_thanh_toan": tt_tt,
        })
        try:
            client.table("orders").insert(payload).execute()
            st.success("Đã thêm đơn hàng.")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")


def _form_edit_order(client, orow) -> None:
    with st.form(f"edit_order_{orow['id']}"):
        c1, c2 = st.columns(2)
        ten_hang = c1.text_input("Tên hàng", orow.get("ten_hang") or "")
        gia_mua = c2.number_input("Giá mua (USD)", value=float(orow.get("gia_mua") or 0), step=1.0)
        gia_ban = c1.number_input("Giá bán (USD)", value=float(orow.get("gia_ban") or 0), step=1.0)
        th_idx = TT_HANG_OPTS.index(orow["trang_thai_hang"]) + 1 if orow.get("trang_thai_hang") in TT_HANG_OPTS else 0
        tt_hang = c2.selectbox("Trạng thái hàng hoá", [""] + TT_HANG_OPTS, index=th_idx)
        tt_idx = TT_THANHTOAN_OPTS.index(orow["tinh_trang_thanh_toan"]) + 1 if orow.get("tinh_trang_thanh_toan") in TT_THANHTOAN_OPTS else 0
        tt_tt = c1.selectbox("Tình trạng thanh toán", [""] + TT_THANHTOAN_OPTS, index=tt_idx)
        eta_val = orow.get("eta").date() if pd.notna(orow.get("eta")) else None
        eta = c2.date_input("ETA", value=eta_val)
        ok = st.form_submit_button("Cập nhật đơn")
    if ok:
        payload = {
            "ten_hang": ten_hang, "gia_mua": gia_mua or None, "gia_ban": gia_ban or None,
            "loi_nhuan": (gia_ban - gia_mua) if (gia_ban or gia_mua) else None,
            "trang_thai_hang": tt_hang or None, "tinh_trang_thanh_toan": tt_tt or None,
            "eta": eta.isoformat() if eta else None,
        }
        try:
            client.table("orders").update(payload).eq("id", int(orow["id"])).execute()
            st.success("Đã cập nhật đơn.")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")


# ---------- Trang 4: Vận chuyển ----------

def page_tracking(client, customers, orders) -> None:
    page_header("🚢", "Theo dõi vận chuyển", "Lô hàng theo ETA")
    o = orders_with_names(orders, customers)
    if o.empty or o["eta"].isna().all():
        st.info("Chưa có dữ liệu ETA.")
        return
    today = pd.Timestamp.today().normalize()
    o = o.dropna(subset=["eta"]).copy()
    o["con_lai"] = (o["eta"] - today).dt.days

    up7 = o[(o["con_lai"] >= 0) & (o["con_lai"] <= 7)]
    overdue = o[o["con_lai"] < 0]
    a, b, c = st.columns(3)
    a.metric("Lô đang theo dõi", f"{len(o)}")
    b.metric("📅 Về trong 7 ngày", f"{len(up7)}")
    c.metric("⚠️ Quá ETA", f"{len(overdue)}")
    st.divider()

    t1, t2, t3 = st.tabs(["🔥 Sắp về (≤7 ngày)", "🚨 Quá ETA", "📋 Tất cả"])

    def render(d):
        if d.empty:
            st.info("Không có lô hàng.")
            return
        d = d.sort_values("con_lai").copy()
        cols = [x for x in ["ma_dh", "ten_kh", "ten_hang", "eta", "con_lai", "trang_thai_hang"] if x in d.columns]
        show = d[cols].rename(columns={"ma_dh": "Mã ĐH", "ten_kh": "Khách", "ten_hang": "Hàng",
                                       "eta": "ETA", "con_lai": "Còn (ngày)", "trang_thai_hang": "Trạng thái"})

        def style(r):
            v = r.get("Còn (ngày)")
            if pd.isna(v):
                return [""] * len(r)
            if v < 0:
                return ["background-color:#FEE2E2"] * len(r)
            if v <= 7:
                return ["background-color:#FEF3C7"] * len(r)
            return [""] * len(r)

        st.dataframe(show.style.apply(style, axis=1), use_container_width=True, hide_index=True,
                     column_config={"ETA": st.column_config.DateColumn(format="DD/MM/YYYY")})

    with t1:
        render(up7)
    with t2:
        render(overdue)
    with t3:
        render(o)


# ---------- Trang 5: Công nợ ----------

def page_debt(client, customers, orders) -> None:
    page_header("💰", "Theo dõi công nợ", "Đơn chưa thanh toán")
    o = orders_with_names(orders, customers)
    if o.empty:
        st.info("Chưa có đơn hàng.")
        return
    mask = o["tinh_trang_thanh_toan"].astype(str).str.contains("Chưa", case=False, na=False)
    if "theo_doi_no" in o:
        mask = mask | o["theo_doi_no"].astype(str).str.contains("chưa", case=False, na=False)
    debt = o[mask].copy()

    a, b, c = st.columns(3)
    a.metric("Đơn còn nợ", f"{len(debt)}")
    b.metric("Tổng chưa thu", db.fmt_usd(debt["gia_ban"].sum()))
    by = debt.groupby("ten_kh")["gia_ban"].sum().sort_values(ascending=False) if not debt.empty else pd.Series(dtype=float)
    c.metric("Khách nợ nhiều nhất", by.index[0] if not by.empty else "-")

    if debt.empty:
        st.success("🎉 Tất cả đã thanh toán.")
        return
    st.divider()
    if not by.empty:
        fig = px.bar(by.reset_index(), x="ten_kh", y="gia_ban",
                     labels={"ten_kh": "Khách hàng", "gia_ban": "Công nợ (USD)"},
                     color="gia_ban", color_continuous_scale="Reds")
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    cols = [x for x in ["ma_dh", "ngay_dat", "ten_kh", "ten_hang", "gia_ban", "tinh_trang_thanh_toan", "theo_doi_no", "eta"] if x in debt.columns]
    show = debt[cols].rename(columns={
        "ma_dh": "Mã ĐH", "ngay_dat": "Ngày đặt", "ten_kh": "Khách", "ten_hang": "Hàng",
        "gia_ban": "Giá bán", "tinh_trang_thanh_toan": "Thanh toán", "theo_doi_no": "Theo dõi nợ", "eta": "ETA"})
    st.dataframe(style_status(show, ["Thanh toán", "Theo dõi nợ"]),
        use_container_width=True, hide_index=True,
        column_config={"Giá bán": st.column_config.NumberColumn(format="$%.2f"),
                       "Ngày đặt": st.column_config.DateColumn(format="DD/MM/YYYY"),
                       "ETA": st.column_config.DateColumn(format="DD/MM/YYYY")})
    download_excel("📥 Tải báo cáo công nợ (Excel)", {"Cong no": show},
                   "bao_cao_cong_no.xlsx")


# ---------- Trang 6: Lịch sử thay đổi ----------

def page_audit(client) -> None:
    page_header("🕓", "Lịch sử thay đổi", "Mọi thao tác thêm/sửa/xoá đều được ghi lại")
    audit = db.fetch_audit(client)
    if audit.empty:
        st.info("Chưa có bản ghi nào.")
        return
    bang_filter = st.multiselect("Lọc theo bảng", sorted(audit["bang"].dropna().unique().tolist()))
    df = audit[audit["bang"].isin(bang_filter)] if bang_filter else audit
    show = df[["thoi_gian", "user_email", "bang", "hanh_dong", "record_id"]].rename(columns={
        "thoi_gian": "Thời gian", "user_email": "Người dùng", "bang": "Bảng",
        "hanh_dong": "Hành động", "record_id": "ID bản ghi"})
    st.dataframe(show, use_container_width=True, hide_index=True,
                 column_config={"Thời gian": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm")})


# ---------- Trang: Pipeline (Kanban + phễu) ----------

def page_pipeline(client, customers, orders) -> None:
    page_header("🗂️", "Pipeline bán hàng", "Đơn hàng theo tình trạng giao dịch")
    o = orders_with_names(orders, customers)
    if o.empty or "tinh_trang_giao_dich" not in o:
        st.info("Chưa có dữ liệu giao dịch.")
        return

    stages = ["Đang tư vấn", "Đã gửi báo giá", "Đã chốt"]
    counts = {s: int((o["tinh_trang_giao_dich"].astype(str) == s).sum()) for s in stages}

    # Phễu chuyển đổi
    st.markdown("#### 🔻 Phễu chuyển đổi")
    fig = px.funnel(
        x=[counts[s] for s in stages], y=stages,
        color_discrete_sequence=["#1B2A6B"],
    )
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    won = counts["Đã chốt"]
    quoted = counts["Đã gửi báo giá"] + won
    rate = (won / quoted * 100) if quoted else 0
    st.caption(f"Tỷ lệ chốt trên số đã báo giá: **{rate:.0f}%**")

    # Kanban
    st.markdown("#### 📋 Bảng Kanban")
    all_stages = stages + ["Từ chối dịch vụ"]
    cols = st.columns(len(all_stages))
    for col, stage in zip(cols, all_stages):
        sub = o[o["tinh_trang_giao_dich"].astype(str) == stage]
        cards = ""
        for _, r in sub.head(40).iterrows():
            ten = r.get("ten_kh") or "—"
            hang = r.get("ten_hang") or ""
            gia = db.fmt_usd(r.get("gia_ban")) if pd.notna(r.get("gia_ban")) else ""
            cards += (f'<div class="kan-card"><div class="t">{ten}</div>'
                      f'<div class="m">{hang}</div><div class="p">{gia}</div></div>')
        col.markdown(
            f'<div class="kan-col"><h5>{stage} ({len(sub)})</h5>{cards}</div>',
            unsafe_allow_html=True,
        )


# ---------- Trang: Nhắc việc (follow-up) ----------

def page_tasks(client, customers) -> None:
    page_header("🔔", "Nhắc việc", "Các lịch follow-up khách hàng")
    notes = db.fetch_notes(client)
    if notes.empty:
        st.info("Chưa có ghi chú nào.")
        return
    todo = notes[(notes["follow_up_date"].notna()) & (~notes["done"])].copy()
    if todo.empty:
        st.success("🎉 Không còn việc nào cần nhắc.")
        return

    name_map = customers.set_index("id")["ten_kh"].to_dict() if not customers.empty else {}
    todo["khach"] = todo["customer_id"].map(name_map).fillna("(không rõ)")
    todo = todo.sort_values("follow_up_date")
    today = pd.Timestamp.today().normalize()

    overdue = todo[todo["follow_up_date"] < today]
    upcoming = todo[todo["follow_up_date"] >= today]

    a, b = st.columns(2)
    a.metric("🔴 Quá hạn", f"{len(overdue)}")
    b.metric("🔔 Sắp tới", f"{len(upcoming)}")
    st.divider()

    def render(group: pd.DataFrame, title: str):
        if group.empty:
            return
        st.markdown(f"##### {title}")
        for _, n in group.iterrows():
            d = n["follow_up_date"].date().strftime("%d/%m/%Y")
            cols = st.columns([6, 1])
            cols[0].markdown(
                f"**{n['khach']}** — {n['noi_dung']}  \n"
                f"<span style='color:#94A3B8;font-size:0.8rem'>📅 {d}</span>",
                unsafe_allow_html=True)
            if can_edit() and cols[1].button("Xong", key=f"task_done_{n['id']}"):
                db.set_note_done(client, int(n["id"]), True)
                st.rerun()

    render(overdue, "🔴 Quá hạn")
    render(upcoming, "🔔 Sắp tới")


# ---------- Xuất báo cáo ----------

def to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    try:
        engine = "xlsxwriter"
        import xlsxwriter  # noqa: F401
    except ImportError:
        engine = "openpyxl"  # đã cài sẵn, dùng làm phương án dự phòng
    with pd.ExcelWriter(buf, engine=engine) as w:
        for name, d in sheets.items():
            d.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()


def download_excel(label: str, sheets: dict[str, pd.DataFrame], filename: str) -> None:
    st.download_button(
        label, data=to_excel_bytes(sheets), file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )


# ---------- Trang: Kết quả tìm kiếm toàn cục ----------

def page_search(client, customers, orders, q: str) -> None:
    page_header("🔎", f'Kết quả cho "{q}"', "Khách hàng & đơn hàng khớp")
    ql = q.lower()

    # Khách khớp
    cust_hits = pd.DataFrame()
    if not customers.empty:
        def _c(col):
            return customers[col].astype(str).str.lower().str.contains(ql, na=False) if col in customers else False
        m = _c("ten_kh") | _c("ma_kh") | _c("ten_cong_ty") | _c("email") | _c("sdt") | _c("nguoi_lien_he")
        cust_hits = customers[m]

    st.markdown(f"#### 👥 Khách hàng ({len(cust_hits)})")
    if cust_hits.empty:
        st.caption("Không có khách khớp.")
    else:
        for _, r in cust_hits.head(20).iterrows():
            ten = _s(r.get("ten_kh")) or "—"
            pl = _s(r.get("phan_loai"))
            tag = f'<span class="tag {_tag_class(pl)}">{pl}</span>' if pl else ""
            meta = " · ".join(x for x in [_s(r.get("ten_cong_ty")), _s(r.get("email")),
                                          _s(r.get("sdt"))] if x)
            c1, c2 = st.columns([6, 1])
            c1.markdown(
                f'<div class="sr-card"><div class="sr-av">{_initials(ten)}</div>'
                f'<div><div class="t">{ten} {tag}</div>'
                f'<div class="m">{meta or "—"}</div></div></div>',
                unsafe_allow_html=True)
            c2.button("Mở hồ sơ", key=f"open_{r['id']}",
                      on_click=_go_customer, args=(r["ten_kh"],))

    # Đơn khớp
    o = orders_with_names(orders, customers)
    ord_hits = pd.DataFrame()
    if not o.empty:
        def _o(col):
            return o[col].astype(str).str.lower().str.contains(ql, na=False) if col in o else False
        m = _o("ma_dh") | _o("ten_hang") | _o("shipper") | _o("consignee") | _o("ten_kh")
        ord_hits = o[m]

    st.markdown(f"#### 📦 Đơn hàng ({len(ord_hits)})")
    if ord_hits.empty:
        st.caption("Không có đơn khớp.")
    else:
        cols = [x for x in ["ma_dh", "ngay_dat", "ten_kh", "ten_hang", "gia_ban",
                            "trang_thai_hang", "tinh_trang_thanh_toan"] if x in ord_hits.columns]
        show = ord_hits[cols].rename(columns={
            "ma_dh": "Mã ĐH", "ngay_dat": "Ngày đặt", "ten_kh": "Khách", "ten_hang": "Hàng",
            "gia_ban": "Giá bán", "trang_thai_hang": "TT hàng", "tinh_trang_thanh_toan": "Thanh toán"})
        st.dataframe(style_status(show, ["TT hàng", "Thanh toán"]),
                     use_container_width=True, hide_index=True,
                     column_config={"Giá bán": st.column_config.NumberColumn(format="$%.2f"),
                                    "Ngày đặt": st.column_config.DateColumn(format="DD/MM/YYYY")})


# ---------- Main ----------

def main() -> None:
    inject_css()
    if not db.is_logged_in():
        login_screen()
        return

    client = db.get_client()

    # Sidebar
    if logo_exists():
        st.sidebar.image(str(LOGO_PATH), use_container_width=True)
    else:
        st.sidebar.title("📦 CRM TCL")
    st.sidebar.markdown(f"**{st.session_state['ho_ten']}**")
    st.sidebar.caption(f"{ROLE_LABEL.get(db.role(), db.role())} · {st.session_state['email']}")

    with st.sidebar.expander("🔑 Đổi mật khẩu"):
        with st.form("change_pw", clear_on_submit=True):
            p1 = st.text_input("Mật khẩu mới", type="password")
            p2 = st.text_input("Nhập lại mật khẩu mới", type="password")
            if st.form_submit_button("Cập nhật mật khẩu"):
                if len(p1) < 6:
                    st.error("Mật khẩu phải từ 6 ký tự trở lên.")
                elif p1 != p2:
                    st.error("Hai lần nhập không khớp.")
                else:
                    ok, msg = db.change_password(p1)
                    if ok:
                        st.success("Đã đổi mật khẩu. Lần sau đăng nhập bằng mật khẩu mới.")
                    else:
                        st.error(f"Lỗi: {msg}")

    if st.sidebar.button("🚪  Đăng xuất", use_container_width=True, key="logout_btn"):
        db.logout()
        st.rerun()
    st.sidebar.divider()

    # Thanh tìm kiếm toàn cục
    st.sidebar.text_input("🔎 Tìm nhanh", key="gsearch",
                          placeholder="Tên khách, mã, tên hàng...")
    gq = st.session_state.get("gsearch", "").strip()

    # Danh sách trang + icon (emoji)
    nav = [("Tổng quan", "📊"), ("Khách hàng", "👥"), ("Đơn hàng", "📦"),
           ("Pipeline", "🗂️"), ("Vận chuyển", "🚢"), ("Công nợ", "💰"),
           ("Nhắc việc", "🔔")]
    if can_audit():
        nav.append(("Lịch sử", "🕓"))
    names = [n for n, _ in nav]

    if "page" not in st.session_state or st.session_state["page"] not in names:
        st.session_state["page"] = names[0]

    # Menu tự dựng: mục đang chọn = thẻ đỏ, mục khác = nút bấm trên nền navy
    for name, emoji in nav:
        if st.session_state["page"] == name and not gq:
            st.sidebar.markdown(
                f'<div class="nav-active">{emoji}&nbsp;&nbsp;{name}</div>',
                unsafe_allow_html=True)
        else:
            st.sidebar.button(f"{emoji}  {name}", key=f"nav_{name}",
                              use_container_width=True,
                              on_click=_select_page, args=(name,))
    page = st.session_state["page"]

    # Tải dữ liệu (RLS tự lọc theo quyền)
    try:
        customers = db.fetch_customers(client)
        orders = db.fetch_orders(client)
        profiles = db.fetch_profiles(client) if can_reassign() else pd.DataFrame()
    except Exception as e:
        if "JWT" in str(e) or "PGRST303" in str(e):
            db.logout()
            st.warning("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
            st.stop()
        st.error(f"Lỗi tải dữ liệu: {e}")
        st.stop()

    # Đang tìm kiếm -> hiện trang kết quả (ghi đè trang đang chọn)
    if gq:
        page_search(client, customers, orders, gq)
        return

    if page == "Tổng quan":
        page_dashboard(client, customers, orders)
    elif page == "Khách hàng":
        page_customers(client, customers, orders, profiles)
    elif page == "Đơn hàng":
        page_orders(client, customers, orders)
    elif page == "Pipeline":
        page_pipeline(client, customers, orders)
    elif page == "Vận chuyển":
        page_tracking(client, customers, orders)
    elif page == "Công nợ":
        page_debt(client, customers, orders)
    elif page == "Nhắc việc":
        page_tasks(client, customers)
    elif page == "Lịch sử":
        page_audit(client)


if __name__ == "__main__":
    main()
