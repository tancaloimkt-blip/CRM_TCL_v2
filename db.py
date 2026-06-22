"""Kết nối Supabase + tiện ích cho app Streamlit.

- get_client(): trả về client đã gắn token người dùng → RLS tự áp dụng.
- login()/logout(): xác thực qua Supabase Auth.
- fetch_*(): đọc dữ liệu thành DataFrame (đã bị RLS lọc theo quyền).
"""

from __future__ import annotations

import base64
import json
import time

import pandas as pd
import streamlit as st
from supabase import create_client, Client


def _clean_url(url: str) -> str:
    url = url.strip().rstrip("/")
    for suffix in ("/rest/v1", "/auth/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url


SUPABASE_URL = _clean_url(st.secrets["SUPABASE_URL"])
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]


def _token_expired(token: str) -> bool:
    """Đọc trường exp trong JWT, coi là hết hạn nếu còn < 60 giây."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # pad base64
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("exp", 0) <= time.time() + 60
    except Exception:
        return True


def _refresh_session() -> bool:
    """Làm mới phiên bằng refresh_token. Trả về True nếu thành công."""
    refresh = st.session_state.get("refresh_token")
    if not refresh:
        return False
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = client.auth.refresh_session(refresh)
        if res.session:
            st.session_state["access_token"] = res.session.access_token
            st.session_state["refresh_token"] = res.session.refresh_token
            return True
    except Exception:
        pass
    return False


def get_client() -> Client:
    """Client mới mỗi lần gọi; gắn access_token (tự làm mới nếu hết hạn) để RLS chạy."""
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    token = st.session_state.get("access_token")
    if token and _token_expired(token):
        if _refresh_session():
            token = st.session_state.get("access_token")
        else:
            logout()  # refresh token cũng hết hạn → buộc đăng nhập lại
            token = None
    if token:
        client.postgrest.auth(token)
    return client


def login(email: str, password: str) -> tuple[bool, str]:
    """Đăng nhập. Trả về (thành công, thông báo)."""
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        return False, f"Sai email hoặc mật khẩu. ({e})"

    session, user = res.session, res.user
    if not session or not user:
        return False, "Không tạo được phiên đăng nhập."

    # Lấy hồ sơ (vai trò) của user
    prof = client.table("profiles").select("*").eq("id", user.id).single().execute()
    if not prof.data:
        return False, "Tài khoản chưa được gán vai trò (profiles)."

    st.session_state.update({
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "user_id": user.id,
        "email": user.email,
        "role": prof.data["role"],
        "ho_ten": prof.data["ho_ten"],
    })
    return True, "OK"


def change_password(new_password: str) -> tuple[bool, str]:
    """Đổi mật khẩu của user đang đăng nhập."""
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.auth.set_session(st.session_state["access_token"],
                                st.session_state["refresh_token"])
        client.auth.update_user({"password": new_password})
        return True, "OK"
    except Exception as e:
        return False, str(e)


def logout() -> None:
    for k in ("access_token", "refresh_token", "user_id", "email", "role", "ho_ten"):
        st.session_state.pop(k, None)


def is_logged_in() -> bool:
    return bool(st.session_state.get("access_token"))


def role() -> str:
    return st.session_state.get("role", "")


# ---------- Đọc dữ liệu (RLS tự lọc theo quyền user) ----------

def _df(data) -> pd.DataFrame:
    return pd.DataFrame(data or [])


def fetch_customers(client: Client) -> pd.DataFrame:
    df = _df(client.table("customers").select("*").order("ten_kh").execute().data)
    for c in ("ngay_nhap_lieu", "ngay_sinh_nhat"):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def fetch_orders(client: Client) -> pd.DataFrame:
    df = _df(
        client.table("orders").select("*")
        .order("ngay_dat", desc=True, nullsfirst=False).execute().data
    )
    for c in ("gia_mua", "gia_ban", "loi_nhuan"):  # khoi_luong giữ dạng chữ
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("ngay_dat", "eta"):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def fetch_fees(client: Client, order_id: int) -> pd.DataFrame:
    df = _df(client.table("fees").select("*").eq("order_id", order_id).execute().data)
    if "so_tien" in df.columns:
        df["so_tien"] = pd.to_numeric(df["so_tien"], errors="coerce")
    return df


def fetch_profiles(client: Client) -> pd.DataFrame:
    """Danh sách user (để hiển thị tên sale / chọn người phụ trách)."""
    return _df(client.table("profiles").select("id, ho_ten, role").execute().data)


def fetch_notes(client: Client, customer_id: int | None = None) -> pd.DataFrame:
    """Ghi chú: của 1 khách (nếu truyền customer_id) hoặc tất cả (RLS lọc theo quyền)."""
    q = client.table("notes").select("*").order("created_at", desc=True)
    if customer_id is not None:
        q = q.eq("customer_id", customer_id)
    df = _df(q.execute().data)
    for c in ("follow_up_date", "created_at"):
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def update_customer_stage(client: Client, customer_id: int, giai_doan: str) -> None:
    """Đổi giai đoạn chăm sóc của 1 khách (dùng khi kéo-thả Kanban)."""
    client.table("customers").update({"giai_doan": giai_doan}).eq("id", int(customer_id)).execute()


def add_note(client: Client, customer_id: int, noi_dung: str,
             follow_up_date=None) -> None:
    payload = {
        "customer_id": int(customer_id),
        "user_id": st.session_state["user_id"],
        "noi_dung": noi_dung,
        "follow_up_date": follow_up_date.isoformat() if follow_up_date else None,
    }
    client.table("notes").insert(payload).execute()


def set_note_done(client: Client, note_id: int, done: bool) -> None:
    client.table("notes").update({"done": done}).eq("id", int(note_id)).execute()


def fetch_audit(client: Client, limit: int = 500) -> pd.DataFrame:
    df = _df(
        client.table("audit_log").select("*")
        .order("thoi_gian", desc=True).limit(limit).execute().data
    )
    if "thoi_gian" in df.columns:
        df["thoi_gian"] = pd.to_datetime(df["thoi_gian"], errors="coerce")
    return df


def fmt_usd(value) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"${value:,.2f}"
