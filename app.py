#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026 AI 風格診斷系統（Streamlit）
成長漏斗版 v2.0

✅ v2.0 變更：
1) 事件漏斗：開啟、開始、題目進度、完成、結果、名單與分享包
2) 三種入口：friend / cold / social，可搭配 src / campaign / quiz
3) 完整結果不再被必填興趣阻擋
4) 夥伴分享包：LINE / Instagram / Facebook / 跟進文字
"""

import json
import os
import re
import time
import random
import hashlib
import sys
import platform
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from html import escape as html_escape
from typing import Optional, Tuple, Dict, Any, List

import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from growth_features import (
    AcquisitionContext,
    EVENT_COLUMNS,
    build_campaign_share_pack,
    build_event_row,
    build_partner_share_pack,
    build_share_url,
    entry_copy,
)
from humanity_profile import (
    ANIMAL_PROFILES,
    BIRTHDAY_CORES,
    HUMANITY_QUESTIONS,
    build_life_path_report,
    calculate_life_path,
    compute_humanity_report,
)

# plotly（雷達圖）可選
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

# importlib.metadata（環境偵測）
try:
    from importlib import metadata as importlib_metadata
except Exception:
    importlib_metadata = None


# =========================
# 1) Page Config
# =========================
st.set_page_config(page_title="2026 AI 風格診斷", page_icon="🤖", layout="centered")

APP_VERSION = "growth-funnel-v3.1.0"
BIRTHDAY_QUIZ_VERSION = "2026LIFE2-HUM20-v1.0"
WEALTH_QUIZ_VERSION = "2026Q1-10Q-v1.2"
HEALTH_QUIZ_VERSION = "2026H1-10Q-v1.1"
DEFAULT_APP_URL = "https://richaiproject-xzwznzb6fdd35n8otuxgha.streamlit.app/"


# =========================
# Helpers
# =========================
def get_qp(key: str, default=None):
    """Streamlit query params 兼容（st.query_params / st.experimental_get_query_params）"""
    try:
        v = st.query_params.get(key, default)
        if isinstance(v, list):
            return v[0] if v else default
        return v
    except Exception:
        try:
            v = st.experimental_get_query_params().get(key, [default])
            return v[0] if isinstance(v, list) else v
        except Exception:
            return default


def sget(dct: dict, *path, default=None):
    cur = dct
    for k in path:
        try:
            cur = cur.get(k, None)
        except Exception:
            return default
        if cur is None:
            return default
    return cur


def secret_value(*path, default=None):
    """Read Streamlit secrets without failing when no local secrets file exists."""
    try:
        return sget(st.secrets, *path, default=default)
    except Exception:
        return default


def norm_ref(x: str) -> str:
    return str(x or "").strip().lower()


ACQUISITION = AcquisitionContext.from_values(
    ref_input=get_qp("ref", "master"),
    source=get_qp("src", "direct"),
    campaign=get_qp("campaign", "organic"),
    entry=get_qp("entry", "friend"),
    forced_quiz=get_qp("quiz", ""),
)
DEBUG = str(get_qp("debug", "0")).lower() in ("1", "true", "yes", "y")
DEMO_MODE = str(os.getenv("RICH_DEMO_MODE", "0")).strip().lower() in (
    "1",
    "true",
    "yes",
    "y",
)
FUNNEL_TAG = str(get_qp("cl", "cl3")).strip()
MODE = str(get_qp("mode", "A")).strip()
APP_PUBLIC_URL = str(
    secret_value("APP_PUBLIC_URL", default=DEFAULT_APP_URL) or DEFAULT_APP_URL
).strip()
EVENT_TRACKING_ENABLED = (not DEMO_MODE) and str(
    secret_value("ENABLE_EVENT_TRACKING", default="false")
).strip().lower() in ("1", "true", "yes", "y")
ADMIN_PANEL_ENABLED = str(
    secret_value("ENABLE_LEGACY_ADMIN_PANEL", default="false")
).strip().lower() in ("1", "true", "yes", "y")


def _pkg_ver(pkg_name: str) -> str:
    if not importlib_metadata:
        return ""
    try:
        return importlib_metadata.version(pkg_name)
    except Exception:
        return ""


def _env_meta() -> Dict[str, Any]:
    return {
        "app_version": APP_VERSION,
        "birthday_quiz_version": BIRTHDAY_QUIZ_VERSION,
        "wealth_quiz_version": WEALTH_QUIZ_VERSION,
        "health_quiz_version": HEALTH_QUIZ_VERSION,
        "python": sys.version.split()[0],
        "python_exec": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "streamlit": _pkg_ver("streamlit"),
        "pandas": _pkg_ver("pandas"),
        "requests": _pkg_ver("requests"),
        "plotly": _pkg_ver("plotly"),
        "st-gsheets-connection": _pkg_ver("st-gsheets-connection"),
        "streamlit-gsheets": _pkg_ver("streamlit-gsheets"),
        "gspread": _pkg_ver("gspread"),
    }


if DEBUG:
    st.sidebar.caption(f"APP_VERSION: {APP_VERSION}")
    st.sidebar.caption(f"FUNNEL_TAG: {FUNNEL_TAG} | MODE: {MODE}")
    st.sidebar.caption(
        f"ENTRY: {ACQUISITION.entry} | SRC: {ACQUISITION.source} | CAMPAIGN: {ACQUISITION.campaign}"
    )
    st.sidebar.caption(f"DEMO MODE: {'ON' if DEMO_MODE else 'OFF'}")
    st.sidebar.caption(f"EVENT TRACKING: {'ON' if EVENT_TRACKING_ENABLED else 'OFF'}")
    st.sidebar.subheader("🧪 環境偵測（讀 metadata）")
    st.sidebar.json(_env_meta())


def _retry(fn, *, attempts=4, base_sleep=0.5, max_sleep=3.0, name="op"):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last = e
            if i == attempts - 1:
                raise
            sleep = min(max_sleep, base_sleep * (2 ** i)) + random.random() * 0.25
            if DEBUG:
                st.sidebar.write(
                    f"🔁 retry({name}) {i+1}/{attempts-1} -> {type(e).__name__}: {e} (sleep {sleep:.2f}s)"
                )
            time.sleep(sleep)
    raise last


# =========================
# 2) GSheets 連線封裝（讀/寫 + Retry）
# =========================
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1GxpOmk108RM8wd9lvrQSpngTm5_KWpKkF31bbXjZKv8/edit"
SPREADSHEET_URL = (
    secret_value("connections", "gsheets", "spreadsheet", default=DEFAULT_SHEET_URL)
    or DEFAULT_SHEET_URL
)


def get_conn():
    # Keep the Google Sheets connector lazy so local Demo/QA mode needs no
    # credentials and does not load its native DuckDB dependency.
    from streamlit_gsheets import GSheetsConnection

    return st.connection("gsheets", type=GSheetsConnection)


def gs_read(conn, worksheet: str, ttl: int = 60):
    def _do():
        try:
            return conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet, ttl=ttl)
        except TypeError:
            return conn.read(worksheet=worksheet, ttl=ttl)

    return _retry(_do, name=f"gs_read:{worksheet}")


def gs_update(conn, worksheet: str, data):
    def _do():
        try:
            return conn.update(spreadsheet=SPREADSHEET_URL, worksheet=worksheet, data=data)
        except TypeError:
            return conn.update(worksheet=worksheet, data=data)

    return _retry(_do, name=f"gs_update:{worksheet}")


def _sheet_id_from_url(url: str) -> str:
    m = re.search(r"/spreadsheets/d/([^/]+)", str(url))
    return m.group(1) if m else ""


def gs_append_row_best_effort(conn, worksheet: str, row_dict: dict, cols: List[str]) -> bool:
    """
    多人同時寫入最怕「讀-改-寫」覆蓋：
    - 優先嘗試 gspread worksheet.append_row（原子性較好）
    - 不支援再 fallback：讀表 concat update
    """
    values = [row_dict.get(c, "") for c in cols]

    # 1) append_row
    try:
        client = getattr(conn, "client", None) or getattr(conn, "_client", None)
        if client is None:
            raise AttributeError("no gspread client on connection")

        try:
            ss = client.open_by_url(SPREADSHEET_URL)
        except Exception:
            sid = _sheet_id_from_url(SPREADSHEET_URL)
            if not sid:
                raise
            ss = client.open_by_key(sid)

        ws = ss.worksheet(worksheet)

        def _do_append():
            return ws.append_row(values, value_input_option="USER_ENTERED")

        _retry(_do_append, name=f"append_row:{worksheet}")
        return True
    except Exception as e:
        if DEBUG:
            st.sidebar.write(f"append_row fallback -> {type(e).__name__}: {e}")

    # 2) fallback
    try:
        df = gs_read(conn, worksheet, ttl=0 if DEBUG else 30)
        df.columns = df.columns.str.strip().str.lower()
    except Exception:
        df = pd.DataFrame(columns=cols)

    for c in cols:
        if c not in df.columns:
            df[c] = ""

    new_df = pd.DataFrame([row_dict]).reindex(columns=cols)
    updated = pd.concat([df, new_df], ignore_index=True).reindex(columns=cols)
    gs_update(conn, worksheet, updated)
    return True


# =========================
# 3) Drive 圖片直連（thumbnail）
# =========================
_DRIVE_ID_PATTERNS = [
    r"/file/d/([^/]+)",
    r"[?&]id=([^&]+)",
    r"lh3\.googleusercontent\.com/d/([^=/?]+)",
    r"drive\.google\.com/uc\?export=(?:view|download)&id=([^&]+)",
]


def extract_drive_file_id(url: str) -> str:
    if not url:
        return ""
    s = str(url).strip()
    if (not s.startswith("http")) and len(s) >= 20 and "/" not in s:
        return s
    for pat in _DRIVE_ID_PATTERNS:
        m = re.search(pat, s)
        if m:
            return m.group(1)
    return ""


def drive_img(url: str, width: int = 1200) -> str:
    if not url or pd.isna(url):
        return ""
    s = str(url).strip()
    fid = extract_drive_file_id(s)
    if fid:
        return f"https://drive.google.com/thumbnail?id={fid}&sz=w{int(width)}"
    return s


# =========================
# 4) Partners（多人友善：cache_data）
# =========================
REQUIRED_PARTNER_COLS = {
    "ref",
    "name",
    "title",
    "img_url",
    "line_id",
    "line_search_id",
    "line_token",
    "password",
}


@st.cache_data(ttl=300, show_spinner=False)
def load_all_partners_cached(spreadsheet_url: str, debug_flag: bool):
    conn = get_conn()
    df_m = gs_read(conn, "partners_master", ttl=0)
    df_t = gs_read(conn, "partners_team", ttl=0)

    df_m.columns = df_m.columns.str.strip().str.lower()
    df_t.columns = df_t.columns.str.strip().str.lower()

    df_all = pd.concat([df_m, df_t], ignore_index=True)

    missing = REQUIRED_PARTNER_COLS - set(df_all.columns)
    if missing:
        raise RuntimeError(f"partners 表缺少必要欄位：{', '.join(sorted(missing))}")

    df_all["ref"] = df_all["ref"].astype(str).map(norm_ref)
    for col in ["line_search_id", "line_id", "line_token", "password"]:
        df_all[col] = df_all[col].astype(str).str.strip()

    return df_all


def pick_partner(df_all: pd.DataFrame, ref: str) -> dict:
    ref = norm_ref(ref)
    all_refs = set(df_all["ref"].astype(str).map(norm_ref).values)

    if ref in all_refs:
        return df_all[df_all["ref"] == ref].iloc[0].to_dict()
    if "master" in all_refs:
        return df_all[df_all["ref"] == "master"].iloc[0].to_dict()
    return df_all.iloc[0].to_dict()


if DEMO_MODE:
    df_all = pd.DataFrame(
        [
            {
                "ref": "master",
                "name": "侯閔議",
                "title": "RICH AI 風格診斷顧問",
                "img_url": "",
                "line_id": "",
                "line_search_id": "@rich-demo",
                "line_token": "",
                "password": "",
            }
        ]
    )
else:
    try:
        df_all = load_all_partners_cached(SPREADSHEET_URL, DEBUG)
    except Exception as e:
        st.error("❌ Google Sheets（partners）讀取失敗")
        st.exception(e)
        st.stop()

ref_input = norm_ref(get_qp("ref", "master"))
partner = pick_partner(df_all, ref_input)
ENTRY_UI = entry_copy(ACQUISITION, str(partner.get("name", "")).strip())

p_img = drive_img(partner.get("img_url", ""), width=800)
BADGE_FILE_ID = "1Dz9q_hoxG4BN9YOHymw7JjqJaq5kEFGf"
BADGE_URL = "" if DEMO_MODE else drive_img(BADGE_FILE_ID, width=200)


# =========================
# 5) CSS（玻璃卡 + 多巴胺卡 + 黏著 CTA）
# =========================
CSS_VERSION = "2026-07-23-growth-v2.1.0"

st.markdown(
    f"""
<style>
/* CSS_VERSION:{CSS_VERSION} */
:root{{
  --bg0:#0B0B10; --bg2:#1B1B28; --gold:#FFD700; --green:#06C755;
  --muted:#B8B8C6; --accent:#D3544E; --accent2:#FF4B4B;
  --font:'Microsoft JhengHei', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  --form-bg:#141423; --form-bg-2:#0E0E15; --form-border:rgba(255,255,255,0.16);
}}
html{{ font-size:18px !important; }}
body, .stApp{{ font-size:1rem !important; }}
*{{ font-family:var(--font) !important; }}
[data-testid="stIconMaterial"]{{
  font-family:"Material Symbols Rounded","Material Icons" !important;
}}

.stApp{{
  background:
    radial-gradient(1200px 600px at 70% 15%, rgba(255,215,0,0.10), transparent 60%),
    radial-gradient(900px 500px at 20% 30%, rgba(255,75,75,0.10), transparent 60%),
    linear-gradient(135deg, var(--bg0), var(--bg2));
  padding-bottom:110px;
}}

h1,h2,h3,p,div,span,label{{ color:#fff !important; }}
p, li{{ line-height:1.55 !important; }}
.muted{{ color:var(--muted) !important; }}

[data-testid="stSidebar"]{{
  background:
    radial-gradient(900px 500px at 30% 20%, rgba(255,215,0,0.08), transparent 60%),
    linear-gradient(180deg, #0E0E15, #0B0B10);
  border-right:1px solid rgba(255,255,255,0.06);
}}

/* Inputs */
.stApp input, .stApp textarea {{
  background-color:var(--form-bg) !important;
  color:#fff !important; -webkit-text-fill-color:#fff !important;
  caret-color:#fff !important;
  border:1px solid var(--form-border) !important;
  border-radius:14px !important;
  outline:none !important;
}}

.stApp div[data-baseweb="select"] > div {{
  background-color:var(--form-bg) !important;
  border:1px solid var(--form-border) !important;
  border-radius:14px !important;
}}
.stApp div[data-baseweb="select"] * {{ color:#fff !important; -webkit-text-fill-color:#fff !important; }}

/* Progress */
.stProgress > div > div > div > div{{ background:linear-gradient(90deg, var(--accent), var(--accent2)); }}

/* Buttons */
div.stButton > button{{
  background:linear-gradient(135deg, var(--accent), var(--accent2)) !important;
  color:#fff !important;
  border-radius:14px; width:100%; border:none;
  padding:1.05rem 1.05rem;
  box-shadow:0 14px 35px rgba(255,75,75,0.22);
  transition:0.16s;
  font-size:1.05rem !important;
  font-weight:1000 !important;
}}

[data-testid="stLinkButton"] a{{
  display:flex !important; align-items:center !important; justify-content:center !important;
  gap:10px !important; width:100% !important; text-decoration:none !important;
  background:linear-gradient(135deg, var(--accent), var(--accent2)) !important;
  color:#fff !important; border-radius:14px !important; padding:1.05rem 1.05rem !important;
  border:none !important; font-size:1.05rem !important; font-weight:1000 !important;
  box-shadow:0 14px 35px rgba(255,75,75,0.22) !important; transition:0.16s !important;
}}

pre, code{{
  background:rgba(255,255,255,0.06) !important;
  color:#EEE !important;
  border:1px solid rgba(255,255,255,0.10) !important;
  border-radius:14px !important;
  font-size:0.98rem !important;
}}

.gold-gradient{{
  background:linear-gradient(90deg, #FFF2B8 0%, #FFD700 35%, #FFB84D 70%, #FFE9A6 100%);
  -webkit-background-clip:text; background-clip:text;
  color:transparent !important;
  text-shadow:0 10px 28px rgba(255,215,0,0.16);
}}

/* Badge */
.card-badge{{
  position:absolute; top:10px; right:10px; width:28px !important; height:auto;
  opacity:0.98; filter:drop-shadow(0 10px 22px rgba(255,215,0,0.18));
  pointer-events:none; z-index:9999 !important;
}}

/* Sidebar consultant card */
.sb-card{{
  position:relative; overflow:hidden;
  padding:16px 14px;
  border-radius:22px;
  border:1px solid rgba(255,255,255,0.10);
  background:rgba(255,255,255,0.05);
  box-shadow:0 14px 35px rgba(0,0,0,0.28);
  margin-top:10px;
}}
.sb-img{{
  width:100%; max-width:180px !important; border-radius:18px; object-fit:cover;
  border:1px solid rgba(255,215,0,0.22);
  display:block; margin:0 auto 12px auto;
  position:relative; z-index:1;
}}
.sb-kicker{{ font-size:0.95rem; color:rgba(255,255,255,0.74) !important; letter-spacing:0.5px; }}
.sb-name{{ font-size:1.9rem; font-weight:1000; line-height:1.12; margin-top:4px; }}
.sb-title{{ font-size:1.05rem; color:rgba(255,255,255,0.82) !important; margin-top:6px; }}
.sb-ref{{ margin-top:10px; font-size:0.9rem; color:rgba(255,255,255,0.62) !important; }}

/* Main partner card */
.partner-card{{
  position:relative; overflow:hidden;
  display:flex !important; flex-direction:row !important; align-items:center !important;
  gap:12px !important;
  padding:12px 14px; border-radius:18px;
  border:1px solid rgba(255,255,255,0.10);
  background:rgba(255,255,255,0.05);
  box-shadow:0 10px 25px rgba(0,0,0,0.22);
  margin:6px 0 12px 0;
}}
.partner-img{{
  width:56px !important; height:56px !important; border-radius:16px !important;
  object-fit:cover !important; border:1px solid rgba(255,215,0,0.25);
  flex:0 0 auto; position:relative; z-index:1;
}}
.partner-meta{{ line-height:1.15; position:relative; z-index:2; }}
.partner-kicker{{ font-size:0.85rem; color:rgba(255,255,255,0.72) !important; letter-spacing:0.3px; }}
.partner-name{{ font-size:1.25rem; font-weight:1000; margin-top:2px; }}
.partner-title{{ font-size:0.98rem; color:rgba(255,255,255,0.78) !important; margin-top:2px; }}
.partner-ref{{ margin-top:4px; font-size:0.82rem; color:rgba(255,255,255,0.65) !important; }}

/* Glass cards */
.glass-card{{
  position:relative; overflow:hidden;
  border-radius:22px; border:1px solid rgba(255,255,255,0.14);
  background:rgba(255,255,255,0.06);
  box-shadow:0 18px 45px rgba(0,0,0,0.28);
  backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);
  padding:16px 16px; margin:10px 0 12px 0;
}}
.glass-title{{ font-size:1.06rem; font-weight:1000; margin-bottom:8px; }}
.glass-body{{ color:rgba(255,255,255,0.86) !important; font-size:1rem; line-height:1.6; white-space:pre-wrap; }}
.glass-hint{{ margin-top:10px; color:rgba(255,255,255,0.62) !important; font-size:0.92rem; }}

/* Hero */
.hero-title{{ font-size:2.1rem; font-weight:1000; margin:6px 0 2px 0; }}
.hero-subtitle{{ font-size:1.05rem; color:rgba(255,255,255,0.78) !important; margin:0 0 8px 0; }}
.quiz-step{{ font-size:1.15rem; font-weight:1000; margin-top:4px; }}
.quiz-question{{ font-size:1.55rem; font-weight:1000; margin:6px 0 10px 0; }}

/* Dopamine cards */
.dopamine-card {{
  transition:all 0.25s ease;
  padding:18px 14px;
  border-radius:24px;
  background:rgba(255,255,255,0.04);
  border:2px solid rgba(255,255,255,0.08);
  text-align:center;
  cursor:pointer;
  position:relative;
  overflow:hidden;
  min-height:210px;
  display:flex; flex-direction:column;
  justify-content:center; align-items:center;
}}
.dopamine-card:hover {{
  transform:translateY(-4px);
  background:rgba(255,255,255,0.07);
}}
.card-wealth.active {{
  border-color:var(--gold);
  background:linear-gradient(145deg, rgba(255,215,0,0.15), rgba(0,0,0,0));
  box-shadow:0 0 30px rgba(255,215,0,0.20);
}}
.card-birthday.active {{
  border-color:#C89BFF;
  background:linear-gradient(145deg, rgba(200,155,255,0.20), rgba(255,105,180,0.06));
  box-shadow:0 0 34px rgba(200,155,255,0.22);
}}
.card-health.active {{
  border-color:var(--green);
  background:linear-gradient(145deg, rgba(6,199,85,0.15), rgba(0,0,0,0));
  box-shadow:0 0 30px rgba(6,199,85,0.20);
}}
.dopa-icon {{ font-size:3rem; margin-bottom:8px; }}
.dopa-title {{ font-size:1.35rem; font-weight:1000; margin-bottom:4px; }}
.dopa-desc {{ font-size:0.92rem; color:rgba(255,255,255,0.72); line-height:1.45; }}
.dopa-badge {{
  font-size:0.75rem; padding:4px 10px; border-radius:12px;
  background:rgba(255,255,255,0.10); color:#aaa; margin-bottom:8px; font-weight:900;
}}
.card-wealth.active .dopa-title {{ color:var(--gold) !important; }}
.card-birthday.active .dopa-title {{ color:#E2C8FF !important; }}
.card-health.active .dopa-title {{ color:var(--green) !important; }}

.featured-quiz {{
  min-height:0;
  text-align:left;
  align-items:flex-start;
  padding:20px 20px;
}}
.featured-quiz .dopa-icon {{ font-size:2.4rem; margin-bottom:4px; }}
.featured-quiz .dopa-title {{ font-size:1.55rem; }}
.featured-quiz .dopa-desc {{ font-size:1rem; }}
.privacy-note {{
  color:rgba(255,255,255,0.66) !important;
  font-size:0.88rem;
  margin-top:8px;
}}
.score-grid {{
  display:grid;
  grid-template-columns:repeat(5, minmax(0, 1fr));
  gap:8px;
  margin:8px 0 18px;
}}
.score-item {{
  padding:10px 8px;
  border-radius:14px;
  border:1px solid rgba(255,255,255,0.12);
  background:rgba(255,255,255,0.05);
  text-align:center;
}}
.score-label {{
  color:rgba(255,255,255,0.72) !important;
  font-size:0.78rem;
  line-height:1.25;
}}
.score-value {{
  margin-top:4px;
  color:#E2C8FF !important;
  font-size:1.05rem;
  font-weight:1000;
}}

/* Sticky CTA */
.sticky-cta-container {{
  position:fixed; bottom:24px; left:0; width:100%;
  z-index:99999; display:flex; justify-content:center; pointer-events:none;
}}
.sticky-cta-btn {{
  pointer-events:auto; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(135deg, #06C755, #20D278);
  color:#fff !important; font-weight:1000; font-size:1.08rem;
  padding:14px 28px; border-radius:50px;
  box-shadow:0 10px 25px rgba(6,199,85,0.40);
  text-decoration:none !important;
  border:2px solid rgba(255,255,255,0.2);
  transition:transform 0.2s;
  backdrop-filter:blur(5px);
  width:92%; max-width:420px;
}}
.sticky-cta-btn:active {{ transform:scale(0.97); }}

/* Intro CTA: inline on desktop, fixed at the bottom on mobile. */
.st-key-mobile_start_cta {{
  display:none;
}}

div[data-baseweb="popover"]{{ z-index:99999 !important; }}
div[data-baseweb="popover"] [role="listbox"],
div[data-baseweb="popover"] ul{{
  background-color:var(--form-bg-2) !important;
  border:1px solid rgba(255,255,255,0.14) !important;
  border-radius:14px !important; overflow:hidden !important;
}}
div[data-baseweb="popover"] [role="option"],
div[data-baseweb="popover"] li{{ color:#fff !important; background:transparent !important; }}

@media (max-width:640px){{
  [data-testid="stMainBlockContainer"]{{
    padding:4rem 1rem 8rem !important;
  }}
  .hero-title{{
    font-size:1.72rem !important;
    line-height:1.24 !important;
  }}
  .hero-subtitle{{
    font-size:0.96rem !important;
    line-height:1.5 !important;
  }}
  .partner-card{{
    padding:10px 12px !important;
    margin:4px 0 8px 0 !important;
  }}
  .glass-card{{
    padding:13px 14px !important;
    margin:6px 0 8px 0 !important;
  }}
  .glass-hint{{ display:none !important; }}
  .featured-quiz {{
    padding:14px 15px !important;
  }}
  .featured-quiz .dopa-icon {{
    font-size:1.85rem !important;
    margin-bottom:2px !important;
  }}
  .featured-quiz .dopa-title {{
    font-size:1.28rem !important;
  }}
  .featured-quiz .dopa-desc {{
    font-size:0.9rem !important;
    line-height:1.4 !important;
  }}
  .featured-quiz .privacy-note {{
    display:none !important;
  }}
  .score-grid {{
    grid-template-columns:repeat(2, minmax(0, 1fr));
  }}
  hr{{ margin:0.9rem 0 !important; }}
  h3{{ font-size:1.3rem !important; }}
  .st-key-inline_start_cta {{
    display:none !important;
  }}
  .st-key-mobile_start_cta {{
    display:block !important;
    position:fixed !important;
    left:12px !important;
    right:12px !important;
    width:auto !important;
    max-width:none !important;
    bottom:calc(12px + env(safe-area-inset-bottom)) !important;
    z-index:99998 !important;
    padding:9px !important;
    border:1px solid rgba(255,255,255,0.14) !important;
    border-radius:20px !important;
    background:rgba(12,12,20,0.90) !important;
    box-shadow:0 14px 38px rgba(0,0,0,0.46) !important;
    backdrop-filter:blur(14px) !important;
    -webkit-backdrop-filter:blur(14px) !important;
  }}
  .st-key-mobile_start_cta [data-testid="stButton"] {{
    margin:0 !important;
    width:100% !important;
  }}
  .st-key-mobile_start_cta > [data-testid="stElementContainer"] {{
    width:100% !important;
    max-width:none !important;
  }}
  .st-key-mobile_start_cta button {{
    width:100% !important;
    min-height:54px !important;
    border-radius:15px !important;
    box-shadow:0 10px 28px rgba(255,75,75,0.34) !important;
  }}
  .st-key-birthday_quiz_nav [data-testid="stHorizontalBlock"] {{
    flex-wrap:nowrap !important;
    gap:0.7rem !important;
  }}
  .st-key-birthday_quiz_nav [data-testid="stColumn"] {{
    flex:1 1 0 !important;
    width:calc(50% - 0.35rem) !important;
    min-width:0 !important;
  }}
  .st-key-birthday_quiz_nav button {{
    min-height:54px !important;
    padding:0.75rem 0.45rem !important;
    font-size:0.98rem !important;
  }}
}}
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# 6) Sidebar：顧問卡
# =========================
st.sidebar.write("---")

sb_name = str(partner.get("name", "")).strip()
sb_title = str(partner.get("title", "")).strip()
sb_ref = str(partner.get("ref", "")).strip()

img_html = (
    f'<img class="sb-img" src="{p_img}" alt="partner" loading="lazy" onerror="this.style.display=\'none\';" />'
    if p_img
    else ""
)
ref_html = f'<div class="sb-ref">ref：{sb_ref}</div>' if DEBUG and sb_ref else ""
sb_badge_html = (
    f'<img class="card-badge" src="{BADGE_URL}" alt="badge" onerror="this.style.display=\'none\';" />'
    if BADGE_URL
    else ""
)

st.sidebar.markdown(
    f"""
<div class="sb-card">
  {sb_badge_html}
  {img_html}
  <div class="sb-kicker">{ENTRY_UI["partner_kicker"]}</div>
  <div class="sb-name gold-gradient">{sb_name}</div>
  <div class="sb-title">🎖️ {sb_title}</div>
  {ref_html}
</div>
""",
    unsafe_allow_html=True,
)


def show_partner_card():
    name = str(partner.get("name", "")).strip()
    title = str(partner.get("title", "")).strip()
    ref_text = str(partner.get("ref", "")).strip()

    badge_html = (
        f'<img class="card-badge" src="{BADGE_URL}" alt="badge" onerror="this.style.display=\'none\';" />'
        if BADGE_URL
        else ""
    )
    ref_html2 = f'<div class="partner-ref">ref：{ref_text}</div>' if DEBUG and ref_text else ""

    if p_img:
        html = f"""
        <div class="partner-card">
          {badge_html}
          <img class="partner-img" src="{p_img}" alt="partner" loading="lazy"
               onerror="this.style.display='none';" />
          <div class="partner-meta">
            <div class="partner-kicker">{ENTRY_UI["partner_kicker"]}</div>
            <div class="partner-name gold-gradient">{name}</div>
            <div class="partner-title">🎖️ {title}</div>
            {ref_html2}
          </div>
        </div>
        """
    else:
        html = f"""
        <div class="partner-card">
          {badge_html}
          <div class="partner-meta">
            <div class="partner-kicker">{ENTRY_UI["partner_kicker"]}</div>
            <div class="partner-name gold-gradient">{name}</div>
            <div class="partner-title">🎖️ {title}</div>
            {ref_html2}
          </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)


# =========================
# 7) Session State
# =========================
if "page" not in st.session_state:
    st.session_state.page = "intro"  # intro / life_path_result / quiz / result
if "quiz_id" not in st.session_state:
    st.session_state.quiz_id = ACQUISITION.forced_quiz or "birthday"
if "step" not in st.session_state:
    st.session_state.step = 1
if "u_name" not in st.session_state:
    st.session_state.u_name = ""
if "u_state" not in st.session_state:
    st.session_state.u_state = ""  # 財富需要（狀態）
if "u_state_other" not in st.session_state:
    st.session_state.u_state_other = ""
if "answers_map" not in st.session_state:
    st.session_state.answers_map = {}  # {step -> tag/score}
if "birth_month" not in st.session_state:
    st.session_state.birth_month = 0
if "birth_day" not in st.session_state:
    st.session_state.birth_day = 0
if "birth_year" not in st.session_state:
    st.session_state.birth_year = 0
if "birth_energy" not in st.session_state:
    st.session_state.birth_energy = 0
if "life_path" not in st.session_state:
    st.session_state.life_path = 0
if "u_interest" not in st.session_state:
    st.session_state.u_interest = ""
if "u_interest_other" not in st.session_state:
    st.session_state.u_interest_other = ""
if "notified" not in st.session_state:
    st.session_state.notified = False
if "notified_lead_id" not in st.session_state:
    st.session_state.notified_lead_id = ""
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:20]
if "tracked_events" not in st.session_state:
    st.session_state.tracked_events = set()


def track_event(
    event: str,
    *,
    quiz_id: str = "",
    step: Any = "",
    lead_id: str = "",
    meta: Optional[Dict[str, Any]] = None,
    once_key: str = "",
) -> bool:
    """Append one privacy-light funnel event when event tracking is enabled."""
    if not EVENT_TRACKING_ENABLED:
        return False

    event_key = once_key or f"{event}|{quiz_id}|{step}|{lead_id}"
    if event_key in st.session_state.tracked_events:
        return True
    st.session_state.tracked_events.add(event_key)

    tz = timezone(timedelta(hours=8))
    row = build_event_row(
        now_text=datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
        session_id=st.session_state.session_id,
        event=event,
        context=ACQUISITION,
        ref_resolved=str(partner.get("ref", "")).strip(),
        partner_name=str(partner.get("name", "")).strip(),
        quiz_id=quiz_id,
        step=step,
        lead_id=lead_id,
        meta=meta,
    )
    try:
        return gs_append_row_best_effort(get_conn(), "events", row, EVENT_COLUMNS)
    except Exception as exc:
        if DEBUG:
            st.sidebar.warning(f"事件追蹤暫停：{type(exc).__name__}")
        return False


track_event(
    "page_opened",
    quiz_id=ACQUISITION.forced_quiz,
    meta={"ref_fallback": ref_input != str(partner.get("ref", "")).strip()},
    once_key="page_opened",
)


def reset_all(keep_profile: bool = True):
    st.session_state.page = "intro"
    st.session_state.step = 1
    st.session_state.answers_map = {}
    st.session_state.notified = False
    st.session_state.notified_lead_id = ""
    st.session_state.u_interest = ""
    st.session_state.u_interest_other = ""
    st.session_state.tracked_events = {
        key for key in st.session_state.tracked_events if key == "page_opened"
    }
    if not keep_profile:
        st.session_state.u_name = ""
        st.session_state.u_state = ""
        st.session_state.u_state_other = ""
        st.session_state.birth_year = 0
        st.session_state.birth_month = 0
        st.session_state.birth_day = 0
        st.session_state.birth_energy = 0
        st.session_state.life_path = 0


# =========================
# 8) 財富題庫（v1.2）
# =========================
WEALTH_QUESTIONS = [
    ("① AI 起風了，你會？", [("🚀 先衝先卡位", "A"), ("🧠 先做一套方法", "B"), ("🤝 先找對的人一起", "C"), ("🛡️ 先確認不會翻車", "D")]),
    ("② 你想要的「有錢」是？", [("✨ 人生自由選擇", "A"), ("💤 睡覺也進帳", "B"), ("❤️ 顧家也能助人", "C"), ("🏦 穩穩變富安心", "D")]),
    ("③ 機會來了，你會？", [("⚡ 先出手再優化", "A"), ("📊 先算勝率再做", "B"), ("👥 先組隊再放大", "C"), ("🧯 先看最壞情況", "D")]),
    ("④ 你的天賦底牌是？", [("🧭 抓趨勢定方向", "A"), ("🧩 拆解系統化", "B"), ("🌿 連結信任感", "C"), ("🧱 穩住抗風險", "D")]),
    ("⑤ 你最受不了的是？", [("🐢 慢到錯過風口", "A"), ("🌀 沒邏輯亂做", "B"), ("🧊 冷冰冰沒連結", "C"), ("🎢 太冒險不穩", "D")]),
    ("⑥ 你下決策最靠？", [("🔮 趨勢直覺", "A"), ("🧾 數據計算", "B"), ("🫶 圈層建議", "C"), ("📌 穩定經驗", "D")]),
    ("⑦ 你卡關時會？", [("🌪️ 換路找新風口", "A"), ("🔧 回頭修流程", "B"), ("☎️ 找人聊再出發", "C"), ("🧊 縮風險先守住", "D")]),
    ("⑧ 你帶新人第一步？", [("🔥 先點燃願景", "A"), ("🗂️ 先定 SOP 節奏", "B"), ("🤗 先建立信任感", "C"), ("🧷 先畫底線規則", "D")]),
    ("⑨ 你說服人最自然？", [("🌅 講未來藍圖", "A"), ("🧠 講步驟做法", "B"), ("🫂 先懂他再帶他", "C"), ("🛡️ 講風險怎麼控", "D")]),
    ("⑩ 三年後你最想？", [("🌊 抓浪潮大跳躍", "A"), ("⚙️ 打造自動化引擎", "B"), ("🌸 做出溫暖強團隊", "C"), ("🏰 穩住成果更踏實", "D")]),
]
WEALTH_TOTAL = len(WEALTH_QUESTIONS)

DB_P = {
    "A": "⚡ 領航型（Navigator）",
    "B": "🧠 軍師型（Strategist）",
    "C": "🤝 社群型（Connector）",
    "D": "🛡️ 守護型（Guardian）",
}
TYPE_SHORT = {"A": "領航", "B": "軍師", "C": "社群", "D": "守護"}
TYPE_PRIORITY = ["A", "B", "C", "D"]  # 平手固定


def pick_primary_secondary(counts: Counter) -> Tuple[str, str]:
    """primary: 最高票；secondary: 平手才出現（與 v1.2 一致）"""
    if not counts:
        return "A", ""
    max_n = max(counts.values())
    primary_candidates = [t for t, n in counts.items() if n == max_n]
    primary = next((t for t in TYPE_PRIORITY if t in primary_candidates), primary_candidates[0])
    secondary_candidates = [t for t in primary_candidates if t != primary]
    secondary = next((t for t in TYPE_PRIORITY if t in secondary_candidates), "") if secondary_candidates else ""
    return primary, secondary


# =========================
# 9) 財富：狀態、解析、練習、興趣
# =========================
STATE_OPTIONS = [
    "更靠近夢想",
    "我有危機感／想找方向",
    "我想顧好健康",
    "我想提升財富",
    "我想突破事業",
    "我想經營家庭",
    "我想拿回時間",
    "其他（可填）",
]
STATE_PLACEHOLDER = "先跳過，直接測驗"

STATE_SOOTHE_LINE = {
    "更靠近夢想": "你不是想逃離現況，你只是想把人生拉回更靠近夢想的位置。",
    "我有危機感／想找方向": "你現在最需要的不是答案，而是先把方向感找回來，心才會安。",
    "我想顧好健康": "你不是怕老，你是想把身體照顧好，讓日子走得更長更穩。",
    "我想提升財富": "你想要的不是更多壓力，而是更有選擇權、也更安心的底氣。",
    "我想突破事業": "你其實不是卡住，你是在等一個能放大的方法，而不是硬撐。",
    "我想經營家庭": "你很在乎家要穩，所以你也需要一個不內耗、能長久的節奏。",
    "我想拿回時間": "你想拿回的不是空檔，而是屬於自己的呼吸與掌控感。",
    "其他（可填）": "你心裡其實有一個更重要的在意，我們先把它說清楚，路就會變簡單。",
}


def normalize_state(selection: str, other_text: str) -> str:
    if not selection or selection == STATE_PLACEHOLDER:
        return ""
    if selection == "其他（可填）":
        t = str(other_text or "").strip()
        return f"其他：{t}" if t else ""
    return selection


def soothe_line_from_state(state_final: str) -> str:
    if not state_final:
        return ""
    if str(state_final).startswith("其他："):
        return STATE_SOOTHE_LINE["其他（可填）"]
    return STATE_SOOTHE_LINE.get(state_final, "你正在整理自己在意的事，先讓心安下來就好。")


PRACTICE_BY_TYPE = {
    "A": "放下肩膀 → 吸氣 3 秒、吐氣 5 秒 ×2 → 只寫下『我現在最重要的一步』",
    "B": "看著一件待辦 → 問『下一步是什麼？』→ 只做 30 秒就停",
    "C": "手放胸口 → 吸吐 2 次 → 對自己說『我可以先照顧好自己』",
    "D": "腳踩地感覺支撐 → 吸氣 3 秒、吐氣 5 秒 ×2 → 對自己說『我先求穩就好』",
}
PRACTICE_NOTE = "（做完再看下一步，會更清楚。）"

TYPE_COPY = {
    "A": {
        "analysis": "你那份敢於走在最前面的勇氣，真的很有感染力。",
        "understand": "領航者常常跑得很快，也常常得回頭處理瑣事；你不是不夠努力，而是你值得一套能跟上你節奏的支援方式。",
        "advice": "建議你找時間和 {p_name} 聊聊他那套『AI 自動化助攻工具』，把你手上的雜事交給系統，你才能把時間用在真正重要的方向上。",
    },
    "B": {
        "analysis": "你有一顆細膩又清楚的大腦，總能看透事情的本質。",
        "understand": "你在意的是『可複製、可控、有效率』；當事情變得混亂或不可預期，你會更容易累，因為你一直在替全局收拾。",
        "advice": "你和 {p_name} 的頻率很可能很合。他的『複製系統』結構清楚、節奏明確，會讓你用更省力的方式放大影響力。",
    },
    "C": {
        "analysis": "你溫暖的特質，是很多人願意靠近你的原因。",
        "understand": "你常把別人的需要放在前面，久了容易電量被掏空；你不是不夠堅強，而是你需要更好的界線與補給方式。",
        "advice": "你可以問問 {p_name}，他如何用 AI 幫自己『設下保護圈』，在幫助別人的同時，也保留自己的時間與能量。",
    },
    "D": {
        "analysis": "你很踏實，也很有責任感，是家人和團隊的靠山。",
        "understand": "你渴望的是『穩』：你不想讓自己和重要的人承擔不明風險，所以你會先把安全感建立起來才往前走。",
        "advice": "推薦你跟 {p_name} 深聊，是因為他也重視安全與節奏；你可以請他分享那份『低風險的路徑地圖』，會讓你更安心。",
    },
}

WEALTH_INTEREST_OPTIONS = [
    "AI 工具/自動化課",
    "健康講座（植化素/水素/生活習慣）",
    "被動收入/第二收入",
    "團隊經營/複製系統",
    "其他（可填）",
]
INTEREST_PLACEHOLDER = "先不選，直接看結果"

OUTRO_BY_INTEREST = {
    "AI 工具/自動化課": "關於你感興趣的 AI 自動化，單靠文字很難感受它的震撼。{p_name} 剛好有參與我們內部的「AI 實戰拆解會」，那裡會現場展示如何讓 AI 代替人力。既然他在旁邊，請他幫你預約下一次的線上/實體觀摩名額，你會更快看懂未來的路。",
    "健康講座（植化素/水素/生活習慣）": "你對健康的重視是最好的投資。我們團隊最近剛好有「內在修復與生活節奏」的分享，{p_name} 手上可能有名額，建議請他帶你去聽一場，讓你用更省力的方式照顧身體。",
    "被動收入/第二收入": "追求被動收入需要的是看懂成功的『模型』。{p_name} 這裡有我們「RICH 系統」的說明與現場分享資訊，與其自己摸索，不如請他帶你直接進入系統現場，會更安心也更快。",
    "團隊經營/複製系統": "帶領團隊是一門心與節奏的藝術。我們有一個「菁英實戰營」分享如何讓團隊在互助中自動成長；{p_name} 就在核心圈子裡，請他帶你去感受那種帶心的氛圍，你會發現經營團隊可以很有溫度。",
    "其他（可填）": "關於你的目標，{p_name} 背後有一套完整的支援系統。請他幫你對接下一次交流聚會，你可以一次看到更適合你的選項，比單打獨鬥快很多。",
}


def _normalize_interest(selection: str, other_text: str) -> str:
    if not selection or selection == INTEREST_PLACEHOLDER:
        return ""
    if selection == "其他（可填）":
        t = str(other_text or "").strip()
        return f"其他：{t}" if t else ""
    return selection


def _interest_key_for_outro(interest_final: str) -> str:
    if not interest_final:
        return ""
    if str(interest_final).startswith("其他："):
        return "其他（可填）"
    return str(interest_final).strip()


def status_short_text(status: str) -> str:
    s = str(status or "").strip()
    if s.startswith("其他："):
        return "其他"
    for prefix in ("我想", "我有"):
        if s.startswith(prefix):
            return s[len(prefix):].strip()
    if s.startswith("更靠近"):
        return "靠近夢想"
    return s


# =========================
# 10) 健康題庫 + 解析/建議/對接
# =========================
HEALTH_AXES = ["睡覺", "心情", "消化", "體質"]  # ✅ 固定 4 軸（本版鎖死）

HEALTH_SCALE = [("幾乎沒有（0分）", 0), ("偶爾（1分）", 1), ("經常（2分）", 2), ("天天（3分）", 3)]
HEALTH_FLAG = [("否", 0), ("是（請先就醫）", 1)]

HEALTH_QUESTIONS = [
    {"id": "H01", "section": "睡覺", "text": "睡醒還是覺得累？", "options": HEALTH_SCALE, "qtype": "scale"},
    {"id": "H02", "section": "睡覺", "text": "晚上腦袋轉不停？", "options": HEALTH_SCALE, "qtype": "scale"},
    {"id": "H03", "section": "心情", "text": "最近比較容易煩躁？", "options": HEALTH_SCALE, "qtype": "scale"},
    {"id": "H04", "section": "心情", "text": "肩頸整天緊繃繃？", "options": HEALTH_SCALE, "qtype": "scale"},
    {"id": "H05", "section": "消化", "text": "吃飽飯就想睡？", "options": HEALTH_SCALE, "qtype": "scale"},
    {"id": "H06", "section": "消化", "text": "肚子容易脹氣？", "options": HEALTH_SCALE, "qtype": "scale"},
    {"id": "H07", "section": "體質", "text": "變天就容易感冒？", "options": HEALTH_SCALE, "qtype": "scale"},
    {"id": "H08", "section": "體質", "text": "覺得體力大不如前？", "options": HEALTH_SCALE, "qtype": "scale"},
    {"id": "HF1", "section": "紅旗", "text": "最近胸口悶痛呼吸不順？", "options": HEALTH_FLAG, "qtype": "flag"},
    {"id": "HF2", "section": "紅旗", "text": "有便血或劇烈疼痛？", "options": HEALTH_FLAG, "qtype": "flag"},
]
HEALTH_TOTAL = len(HEALTH_QUESTIONS)
BIRTHDAY_TOTAL = len(HUMANITY_QUESTIONS)

BIRTHDAY_INTEREST_OPTIONS = [
    "更了解我的優勢",
    "改善拖延與卡點",
    "建立穩定行動節奏",
    "探索事業與副業方向",
    "其他（可填）",
]

BIRTHDAY_OUTRO_BY_INTEREST = {
    "更了解我的優勢": "可以請 {p_name} 陪你從最有感的優勢開始，找出一個更適合你的使用方式。",
    "改善拖延與卡點": "你的結果已經指出容易卡住的位置；可以請 {p_name} 陪你把它縮成一個做得到的小步驟。",
    "建立穩定行動節奏": "你需要的不是逼自己更努力，而是找到能長期維持的節奏；可以請 {p_name} 陪你一起整理。",
    "探索事業與副業方向": "先從你的核心優勢與行動風格出發，再和 {p_name} 一起排除不適合的路，會比追熱門方向更有效。",
    "其他（可填）": "你在意的方向很重要；可以把這份結果交給 {p_name}，只針對最有感的一段繼續聊。",
}


def quiz_label(quiz_id: str) -> str:
    return {
        "birthday": "10 秒生命靈數",
        "wealth": "財富與行動風格",
        "health": "健康節奏對帳",
    }.get(str(quiz_id), "成長風格")


def quiz_total(quiz_id: str) -> int:
    return {
        "birthday": BIRTHDAY_TOTAL,
        "wealth": WEALTH_TOTAL,
        "health": HEALTH_TOTAL,
    }.get(str(quiz_id), BIRTHDAY_TOTAL)


def quiz_card_copy(quiz_id: str) -> Dict[str, str]:
    return {
        "birthday": {
            "icon": "🔮",
            "title": quiz_label("birthday"),
            "desc": "輸入完整生日，先看生命路徑、生日天賦、外在態度與今年主題；想更深入，再自願進入 20 題團隊人性探索。",
        },
        "wealth": {
            "icon": "🚀",
            "title": quiz_label("wealth"),
            "desc": "看見你的行動優勢、卡點與適合的下一步。",
        },
        "health": {
            "icon": "🌿",
            "title": quiz_label("health"),
            "desc": "整理睡眠、心情、消化與體力訊號。",
        },
    }.get(str(quiz_id), {})

# ✅ section 名稱可能漂移：這裡統一映射回 4 軸
AXIS_ALIAS = {
    "睡眠": "睡覺",
    "情緒": "心情",
    "腸胃": "消化",
    "免疫": "體質",
}
def _norm_axis(sec: str) -> str:
    s = str(sec or "").strip()
    s = AXIS_ALIAS.get(s, s)
    return s if s in HEALTH_AXES else ""


HEALTH_SECTION_INTERPRET = {
    "睡覺": "你的身體可能沒有真正進入修復狀態；先把睡眠『修復效率』拉回來，整體能量會明顯上升。",
    "心情": "你可能長期處於高張力狀態；先把壓力與情緒的『煞車』找回來，才有空間做更好的決定。",
    "消化": "你的能量入口可能卡住了；先把消化節奏調順，精神與體力常會同步回來。",
    "體質": "你的底盤可能需要補強；先把基本功（作息/水分/活動）做穩，身體就比較不會被環境牽著走。",
}

HEALTH_PAINPOINT_LINE = {
    "睡覺": "你現在最像的痛點：『睡了也沒恢復，越睡越累。』",
    "心情": "你現在最像的痛點：『腦袋停不下來，身體一直緊繃在線。』",
    "消化": "你現在最像的痛點：『能量轉換卡住，吃完反而更沉更脹。』",
    "體質": "你現在最像的痛點：『底盤不夠穩，變天/忙起來就容易掉狀態。』",
}

HEALTH_ADVICE_BY_BAND = {
    "🟢 身體穩健": [
        "你現在最重要的是『維持』：睡眠固定時間、每天走 10 分鐘、喝水不要斷。",
        "如果想升級，先從『晚餐提早 + 週末補眠變平日補覺』這種小改開始。",
    ],
    "🟡 開始扣利息": [
        "先做『減一件』：晚間少一段刺激（手機/工作/含糖），讓身體回到可修復狀態。",
        "做『三件小修復』：水 300ml、走 5 分鐘、提早 15 分鐘上床。",
    ],
    "🔴 嚴重超載": [
        "先把自己從硬撐模式拉出來：今天只求『穩』，不要追求完美。",
        "若你有明顯不適或紅旗題命中，請把就醫/專業評估排在第一順位（測驗僅自我檢視非診斷）。",
    ],
}

HEALTH_PRACTICE_BY_BAND = {
    "🟢 身體穩健": "吸吐 2 次 → 寫下『我今天維持的一件事』→ 做 30 秒收操伸展",
    "🟡 開始扣利息": "放下肩膀 → 吸氣 3 秒、吐氣 5 秒 ×2 → 喝水 3 口",
    "🔴 嚴重超載": "腳踩地感覺支撐 → 吸氣 3 秒、吐氣 5 秒 ×2 → 對自己說『我先求穩就好』",
}

HEALTH_INTEREST_OPTIONS = [
    "健康講座（植化素/水素/生活習慣）",
    "睡眠/壓力節奏調整",
    "腸胃/消化修復",
    "體力/體質底盤",
    "其他（可填）",
]

HEALTH_OUTRO_BY_INTEREST = {
    "健康講座（植化素/水素/生活習慣）": "你想做的是『用更省力的方式修復底盤』。{p_name} 手上通常有團隊的健康分享名額，請他幫你對接一場，你會更快找到適合你的做法。",
    "睡眠/壓力節奏調整": "你需要的是『把修復效率拉回來』。請 {p_name} 幫你安排一個最簡單可執行的 7 天節奏（不用完美，只要做得到）。",
    "腸胃/消化修復": "你現在很可能是『能量入口卡住』。請 {p_name} 協助你對接團隊的飲食節奏與日常修復做法，先把消化順起來。",
    "體力/體質底盤": "你要的是『底盤穩』。請 {p_name} 幫你對接一套低門檻的日常底盤方案（作息/水分/活動），你會更有感。",
    "其他（可填）": "你的目標很重要。請 {p_name} 用這份結果幫你對接最適合的下一步（方法/講座/節奏）。",
}

SECTION_PRIORITY = HEALTH_AXES[:]  # 同軸同優先序


def _section_level(score: int) -> str:
    """每關卡最高 6 分（兩題×3分）
    0-1：穩定
    2-3：開始扣利息
    4-6：明顯超載
    """
    s = int(score or 0)
    if s <= 1:
        return "low"
    if s <= 3:
        return "mid"
    return "high"


HEALTH_SECTION_TIPS = {
    "睡覺": {
        "low": ["維持就很棒：固定起床時間＋睡前減刺激（光/訊息）即可。"],
        "mid": ["先做 3 天節奏：固定起床＋睡前 30 分鐘關機（少光少訊息）。"],
        "high": ["先做 7 天睡眠重置：固定起床＋睡前關機儀式；若長期失眠影響生活，建議評估。"],
    },
    "心情": {
        "low": ["維持穩定：晚上不處理高刺激訊息，白天處理更省力。"],
        "mid": ["先減一件刺激：晚上不做爭議/工作收尾，改用呼吸＋伸展收工。"],
        "high": ["先把壓力源排程化：睡前固定放鬆流程；若情緒困擾持續影響生活，建議尋求支持。"],
    },
    "消化": {
        "low": ["維持即可：慢吃＋少冰＋晚餐不要太晚。"],
        "mid": ["先做 3 天：主食減 1/4＋飯後走 5 分鐘，常常立刻有感。"],
        "high": ["先做 7 天腸胃節奏：定時吃、少刺激、晚餐提早；若合併劇痛/便血等，請先就醫。"],
    },
    "體質": {
        "low": ["維持底盤：水分分段喝＋每天 10 分鐘走路。"],
        "mid": ["先穩地基：睡眠＋水分＋低門檻活動（每天 5 分鐘伸展/深蹲）。"],
        "high": ["先做 7 天底盤防守：作息固定＋水分分段＋每日低門檻活動；若疲倦明顯持續，建議檢查。"],
    },
}

HEALTH_SIGNAL_TIPS_LV = {
    "H01": {2: "（經常）先做『起床時間固定』連續 3 天，修復感通常會回來。",
            3: "（天天）做 7 天『睡眠節奏重置』：固定起床＋睡前 30 分鐘降刺激；若影響生活，建議評估。"},
    "H02": {2: "（經常）睡前 30 分鐘『腦內清空』：寫下明天 3 件事，讓大腦收工。",
            3: "（天天）晚上刺激降到最低：工作訊息白天處理；睡前固定關機儀式（伸展/呼吸）。"},
    "H03": {2: "（經常）晚上不碰爭議訊息/工作，改白天處理，情緒會更穩。",
            3: "（天天）把壓力源排程化＋固定放鬆流程；若困擾持續影響生活，建議尋求支持。"},
    "H04": {2: "（經常）30 秒肩頸放鬆：聳肩 2 秒→放掉×3，再慢吐氣。",
            3: "（天天）加上『分段放鬆』：每 3–4 小時 30 秒伸展，累積效果更大。"},
    "H05": {2: "（經常）主食減 1/4＋飯後走 5 分鐘，通常立刻改善。",
            3: "（天天）7 天餐後能量策略：主食減量＋蛋白質/菜量補足＋晚餐提早。"},
    "H06": {2: "（經常）先做『慢吃＋少冰＋晚餐提早』三天觀察。",
            3: "（天天）7 天腸胃節奏：定時吃、少刺激、早睡；若合併劇痛/便血等，請先就醫。"},
    "H07": {2: "（經常）先把睡眠＋水分做穩，再補白天活動量。",
            3: "（天天）7 天底盤防守：作息固定＋水分分段＋每日低門檻活動；若反覆嚴重不適，建議檢查。"},
    "H08": {2: "（經常）每天 5 分鐘伸展/深蹲，比偶爾爆衝更有效。",
            3: "（天天）地基先穩（睡眠/水分）＋每日低門檻活動；若疲倦持續，建議基本檢查。"},
}


def _pick_signal_tip(qid: str, val: int, section: str, section_score: int) -> str:
    lv = 3 if int(val) >= 3 else 2
    tip = (HEALTH_SIGNAL_TIPS_LV.get(qid, {}) or {}).get(lv, "")
    if not tip:
        lvl = _section_level(int(section_score or 0))
        tips = HEALTH_SECTION_TIPS.get(section, {}).get(lvl, [])
        tip = tips[0] if tips else ""
    return tip


def _combine_sections(sections):
    secs = [s for s in SECTION_PRIORITY if s in set(sections)]
    return "＋".join(secs[:2]) if len(secs) >= 2 else (secs[0] if secs else "")


def _painpoint_for_sections(sections):
    secs = [s for s in SECTION_PRIORITY if s in set(sections)]
    if not secs:
        return "你現在最像的痛點：『目前沒有明顯扣分訊號，維持住就很強。』"
    if len(secs) == 1:
        return HEALTH_PAINPOINT_LINE.get(secs[0], "你現在最像的痛點：『身體在提醒你要先修復，不要再硬撐。』")
    p1 = HEALTH_PAINPOINT_LINE.get(secs[0], "").replace("你現在最像的痛點：", "").strip("： ")
    p2 = HEALTH_PAINPOINT_LINE.get(secs[1], "").replace("你現在最像的痛點：", "").strip("： ")
    return f"你現在最像的痛點：『{p1}』＋『{p2}』"


def health_advice_lines(*, band: str, scale_total: int, top_sections, sections_score: dict, flags_yes):
    if int(scale_total or 0) == 0:
        return [
            "目前沒有明顯扣分訊號：維持住就很強。",
            "維持三件事：固定起床時間／水分分段喝／每天走 10 分鐘。",
        ]

    sec = ""
    if top_sections:
        sec = top_sections[0]
    else:
        sec = max(sections_score.keys(), key=lambda k: sections_score.get(k, 0)) if sections_score else ""

    lvl = _section_level(int(sections_score.get(sec, 0) if sections_score else 0))
    sec_tip = (HEALTH_SECTION_TIPS.get(sec, {}).get(lvl, []) or ["先從作息、水分、活動三件事做穩。"])[0]

    if band == "🟢 身體穩健":
        base = "你屬於『身體穩健』：現在做的是針對最高分關卡微調，讓修復效率更好。"
        second = sec_tip
    elif band == "🟡 開始扣利息":
        base = "你開始在『扣利息』：先做最小可執行修復（少一段刺激＋水 300ml＋走 5 分鐘）。"
        second = sec_tip
    else:
        base = "你目前偏『嚴重超載』：先把自己從硬撐模式拉出來，今天先求穩。"
        second = sec_tip

    if flags_yes:
        second += "（你有勾到紅旗題，請先以就醫/專業評估為優先）"

    return [base, second]


def _label_for_health_value(options: List[Tuple[str, int]], value: int) -> str:
    for lab, v in options:
        if int(v) == int(value):
            return lab
    return str(value)


def compute_health_report(answers_map: Dict[int, int]) -> Dict[str, Any]:
    # ✅ 固定 4 軸，永遠初始化
    sections = {k: 0 for k in HEALTH_AXES}
    flags_yes = []
    scale_total = 0
    max_scale = 0

    for i in range(1, HEALTH_TOTAL + 1):
        q = HEALTH_QUESTIONS[i - 1]
        val = int(answers_map.get(i, 0) or 0)

        sec = _norm_axis(q.get("section", ""))

        if q["qtype"] == "scale":
            scale_total += val
            max_scale += 3
            if sec:
                sections[sec] += val
        else:
            if val == 1:
                flags_yes.append(q["id"])

    if scale_total < 8:
        band = "🟢 身體穩健"
    elif scale_total < 16:
        band = "🟡 開始扣利息"
    else:
        band = "🔴 嚴重超載"

    if scale_total == 0:
        top_sections = []
        top_section_name = "維持"
        painpoint = "你現在最像的痛點：『目前沒有明顯扣分訊號，維持住就很強。』"
        interpret = "你的狀態很穩，最重要的是維持節奏（睡眠/水分/活動）不要斷。"
    else:
        max_sec = max(sections.values()) if sections else 0
        top_sections = [k for k, v in sections.items() if v == max_sec and v > 0]
        top_sections = [s for s in SECTION_PRIORITY if s in set(top_sections)]
        top_section_name = _combine_sections(top_sections) or (top_sections[0] if top_sections else "")
        painpoint = _painpoint_for_sections(top_sections)

        if len(top_sections) == 1:
            interpret = HEALTH_SECTION_INTERPRET.get(top_sections[0], "")
        else:
            i1 = HEALTH_SECTION_INTERPRET.get(top_sections[0], "")
            i2 = HEALTH_SECTION_INTERPRET.get(top_sections[1], "") if len(top_sections) > 1 else ""
            interpret = "／".join([x for x in [i1, i2] if x])

    candidates = []
    for i in range(1, HEALTH_TOTAL + 1):
        q = HEALTH_QUESTIONS[i - 1]
        if q["qtype"] != "scale":
            continue
        val = int(answers_map.get(i, 0) or 0)
        if val >= 2:
            sec = _norm_axis(q.get("section", ""))
            if not sec:
                continue
            qid = q["id"]
            tip = _pick_signal_tip(qid, val, sec, sections.get(sec, 0))
            candidates.append({
                "no": i,
                "id": qid,
                "section": sec,
                "text": q["text"],
                "value": val,
                "answer": _label_for_health_value(q["options"], val),
                "tip": tip,
            })

    # 每關卡最多 2 題
    per_sec = {}
    for t in candidates:
        per_sec.setdefault(t["section"], []).append(t)

    trimmed = []
    for sec, lst in per_sec.items():
        lst.sort(key=lambda x: (-x["value"], x["no"]))
        trimmed.extend(lst[:2])

    trimmed.sort(key=lambda x: (-x["value"], x["no"]))
    top_items = trimmed[:3]

    advice_lines = health_advice_lines(
        band=band,
        scale_total=scale_total,
        top_sections=top_sections,
        sections_score=sections,
        flags_yes=flags_yes,
    )

    return {
        "band": band,
        "total_scale_score": scale_total,
        "max_scale_score": max_scale,
        "sections_score": sections,          # ✅ 一定含 4 軸
        "top_section": top_section_name,
        "top_sections": top_sections,
        "flags_yes": flags_yes,
        "painpoint": painpoint,
        "interpret": interpret,
        "advice_lines": advice_lines,
        "practice": HEALTH_PRACTICE_BY_BAND.get(band, HEALTH_PRACTICE_BY_BAND["🟡 開始扣利息"]),
        "top_items": top_items,
        "top_items_summary": " / ".join(
            [f"{t['section']}:{t['text']}({t['answer']})→{t.get('tip','')}" for t in top_items]
        ) if top_items else "",
    }


# =========================
# 11) Lead ID / Scores payload（兼容 v1.2）
# =========================
def compute_lead_id(
    quiz_id: str,
    quiz_version: str,
    ref_resolved: str,
    client_name: str,
    state: str,
    interest: str,
    primary: str,
    secondary: str,
    funnel: str,
    mode: str,
) -> str:
    base = f"{quiz_id}|{quiz_version}|{ref_resolved}|{client_name}|{state}|{interest}|{primary}|{secondary}|{funnel}|{mode}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def build_wealth_answers_payload(answers_map: dict, meta: Optional[Dict] = None) -> dict:
    payload = {"_meta": meta or {}}
    for i in range(1, WEALTH_TOTAL + 1):
        q_txt, opts = WEALTH_QUESTIONS[i - 1]
        tag = str(answers_map.get(i, "")).strip()
        label = ""
        for lab, t in opts:
            if t == tag:
                label = lab
                break
        payload[f"q{i}"] = {"question": q_txt, "tag": tag, "answer": label}
    return payload


def build_birthday_answers_payload(
    answers_map: dict,
    meta: Optional[Dict] = None,
    report: Optional[Dict] = None,
) -> dict:
    """Build an opt-in payload without storing the visitor's raw birth date."""
    safe_report = {
        key: value
        for key, value in dict(report or {}).items()
        if key
        not in {
            "birth_year",
            "birth_month",
            "birth_day",
            "year",
            "month",
            "day",
        }
    }
    payload = {"_meta": meta or {}, "_report": safe_report}
    for i, question in enumerate(HUMANITY_QUESTIONS, start=1):
        value = int(answers_map.get(i, 0) or 0)
        answer = next(
            (
                label
                for label, score in question["options"]
                if int(score) == value
            ),
            "",
        )
        payload[f"q{i}"] = {
            "id": question["id"],
            "question": question["text"],
            "value": value,
            "answer": answer,
            "animal": (
                ANIMAL_PROFILES[value]["label"]
                if value in ANIMAL_PROFILES
                else ""
            ),
        }
    return payload


def build_health_answers_payload(answers_map: dict, meta: Optional[Dict] = None, report: Optional[Dict] = None) -> dict:
    payload = {"_meta": meta or {}, "_report": report or {}}
    for i in range(1, HEALTH_TOTAL + 1):
        q = HEALTH_QUESTIONS[i - 1]
        val = int(answers_map.get(i, 0) or 0)
        payload[f"q{i}"] = {
            "id": q["id"],
            "section": str(q["section"]),
            "qtype": q["qtype"],
            "question": q["text"],
            "value": val,
            "answer": _label_for_health_value(q["options"], val),
        }
    return payload


# =========================
# 12) LINE Push（推播）
# =========================
def push_line(token: str, to_id: str, text: str):
    if DEMO_MODE:
        return
    if not token or not to_id:
        return
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": to_id, "messages": [{"type": "text", "text": text}]},
            timeout=8,
        )
    except Exception:
        pass


LEADS_COLS = [
    "time",
    "ref",
    "partner_name",
    "client_name",
    "client_job",        # 保留欄名，但存「狀態」
    "interest",
    "result",
    "result_primary",
    "result_secondary",
    "scores",
    "keyword",           # 暫存 lead_id（向下相容）
    "mode",
    "funnel",
]


def build_push_message_birthday(
    *,
    lead_id: str,
    report: Dict[str, Any],
    interest: str,
) -> str:
    ref_resolved = str(partner.get("ref", "")).strip()
    return (
        f"🚀 新名單報到（{FUNNEL_TAG}/{MODE}）\n"
        f"🧑‍💼 顧問：{partner.get('name','')}（ref：{ref_resolved}）\n"
        f"🧪 測驗：birthday\n"
        f"🆔 lead_id：{lead_id}\n"
        f"👤 受測者：{st.session_state.u_name}\n"
        f"✨ 結果：{report.get('combined_title','')}\n"
        f"🔢 生命靈數：{report.get('life_path','')}號 {report.get('core_label','')}\n"
        f"🐾 動物原型：{report.get('animal_title','')}\n"
        f"🎯 興趣：{interest}\n"
        f"🔁 ref_in→ref_ok：{norm_ref(get_qp('ref','master'))} → {ref_resolved}"
    )


def build_push_message_wealth(*, lead_id: str, persona: str, primary: str, secondary: str, interest: str, state: str) -> str:
    p_main = TYPE_SHORT.get(primary, primary)
    p_sec = TYPE_SHORT.get(secondary, secondary) if secondary else ""
    soothe = soothe_line_from_state(state)
    summary = f"{status_short_text(state)}/{p_main}為主{('/'+p_sec+'為輔') if p_sec else ''}/{interest}"
    ref_resolved = str(partner.get("ref", "")).strip()

    msg = (
        f"🚀 新名單報到（{FUNNEL_TAG}/{MODE}）\n"
        f"🧑‍💼 顧問：{partner.get('name','')}（ref：{ref_resolved}）\n"
        f"🧪 測驗：wealth\n"
        f"🆔 lead_id：{lead_id}\n"
        f"👤 受測者：{st.session_state.u_name}\n"
        f"🧩 類型：{persona}\n"
        f"🎯 興趣：{interest}\n"
        f"🧠 狀態：{state}\n"
        f"🎯 痛點句：{soothe}\n"
        f"🧾 摘要：{summary}\n"
        f"🔁 ref_in→ref_ok：{norm_ref(get_qp('ref','master'))} → {ref_resolved}"
    )
    return msg


def build_push_message_health(*, lead_id: str, report: Dict[str, Any], interest: str, state: str) -> str:
    ref_resolved = str(partner.get("ref", "")).strip()
    band = report.get("band", "")
    top_sec = report.get("top_section", "")
    pain = report.get("painpoint", "")

    msg = (
        f"🚀 新名單報到（{FUNNEL_TAG}/{MODE}）\n"
        f"🧑‍💼 顧問：{partner.get('name','')}（ref：{ref_resolved}）\n"
        f"🧪 測驗：health\n"
        f"🆔 lead_id：{lead_id}\n"
        f"👤 受測者：{st.session_state.u_name}\n"
        f"📌 結果：{band}\n"
        f"🔎 最高分關卡：{top_sec}\n"
        f"🎯 痛點句：{pain}\n"
        f"🎯 興趣：{interest}\n"
        + (f"🧠 狀態：{state}\n" if state else "")
        + f"🔁 ref_in→ref_ok：{norm_ref(get_qp('ref','master'))} → {ref_resolved}"
    )
    return msg


def write_lead_and_notify_birthday(
    report: Dict[str, Any],
    interest: str,
) -> str:
    """Persist only raw-date-free derived numbers and the report after opt-in."""
    tz = timezone(timedelta(hours=8))
    now_tw = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    ref_in = norm_ref(get_qp("ref", "master"))
    ref_resolved = str(partner.get("ref", "")).strip()

    lead_id = compute_lead_id(
        "birthday",
        BIRTHDAY_QUIZ_VERSION,
        ref_resolved,
        st.session_state.u_name,
        "",
        interest,
        str(report.get("primary", "")),
        str(report.get("secondary", "")),
        FUNNEL_TAG,
        MODE,
    )
    if DEMO_MODE:
        return f"demo-{lead_id}"

    meta = {
        "lead_id": lead_id,
        "quiz_id": "birthday",
        "quiz_version": BIRTHDAY_QUIZ_VERSION,
        "ref_input": ref_in,
        "ref_resolved": ref_resolved,
        "funnel": FUNNEL_TAG,
        "mode": MODE,
        "app_version": APP_VERSION,
        "session_id": st.session_state.session_id,
        "source": ACQUISITION.source,
        "campaign": ACQUISITION.campaign,
        "entry": ACQUISITION.entry,
        "life_path": int(report.get("life_path", 0) or 0),
        "animal_primary": str(report.get("primary", "")),
        "animal_secondary": str(report.get("secondary", "")),
        "animal_intensity": str(report.get("animal_intensity", "")),
    }
    answers_payload = build_birthday_answers_payload(
        st.session_state.answers_map,
        meta=meta,
        report=report,
    )
    row = {
        "time": now_tw,
        "ref": ref_resolved,
        "partner_name": partner.get("name", ""),
        "client_name": st.session_state.u_name,
        "client_job": "",
        "interest": interest,
        "result": report.get("combined_title", ""),
        "result_primary": report.get("primary_label", ""),
        "result_secondary": report.get("secondary_label", ""),
        "scores": json.dumps(answers_payload, ensure_ascii=False),
        "keyword": lead_id,
        "mode": MODE,
        "funnel": FUNNEL_TAG,
    }
    gs_append_row_best_effort(get_conn(), "leads", row, LEADS_COLS)

    line_cfg = secret_value("line", default={}) or {}
    master_token = str(
        line_cfg.get("channel_access_token")
        or secret_value("LINE_CHANNEL_ACCESS_TOKEN", default="")
    ).strip()
    master_to_id = str(
        line_cfg.get("user_id")
        or secret_value("LINE_USER_ID", default="")
    ).strip()
    msg = build_push_message_birthday(
        lead_id=lead_id,
        report=report,
        interest=interest,
    )
    push_line(master_token, master_to_id, msg)
    push_line(
        str(partner.get("line_token") or "").strip(),
        str(partner.get("line_id") or "").strip(),
        msg,
    )
    return lead_id


def write_lead_and_notify_wealth(primary: str, secondary: str, persona_name: str, counts: Counter, interest: str) -> str:
    tz = timezone(timedelta(hours=8))
    now_tw = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    ref_in = norm_ref(get_qp("ref", "master"))
    ref_resolved = str(partner.get("ref", "")).strip()

    lead_id = compute_lead_id(
        "wealth",
        WEALTH_QUIZ_VERSION,
        ref_resolved,
        st.session_state.u_name,
        st.session_state.u_state,
        interest,
        primary,
        secondary,
        FUNNEL_TAG,
        MODE,
    )
    if DEMO_MODE:
        return f"demo-{lead_id}"
    conn = get_conn()

    meta = {
        "lead_id": lead_id,
        "quiz_id": "wealth",
        "quiz_version": WEALTH_QUIZ_VERSION,
        "ref_input": ref_in,
        "ref_resolved": ref_resolved,
        "funnel": FUNNEL_TAG,
        "mode": MODE,
        "app_version": APP_VERSION,
        "session_id": st.session_state.session_id,
        "source": ACQUISITION.source,
        "campaign": ACQUISITION.campaign,
        "entry": ACQUISITION.entry,
    }

    answers_payload = build_wealth_answers_payload(st.session_state.answers_map, meta=meta)

    row = {
        "time": now_tw,
        "ref": ref_resolved,
        "partner_name": partner.get("name", ""),
        "client_name": st.session_state.u_name,
        "client_job": st.session_state.u_state,  # 欄名保留，但內容是狀態
        "interest": interest,
        "result": persona_name,
        "result_primary": primary,
        "result_secondary": secondary,
        "scores": json.dumps(answers_payload, ensure_ascii=False),
        "keyword": lead_id,
        "mode": MODE,
        "funnel": FUNNEL_TAG,
    }

    gs_append_row_best_effort(conn, "leads", row, LEADS_COLS)

    line_cfg = secret_value("line", default={}) or {}
    master_token = str(line_cfg.get("channel_access_token") or secret_value("LINE_CHANNEL_ACCESS_TOKEN", default="")).strip()
    master_to_id = str(line_cfg.get("user_id") or secret_value("LINE_USER_ID", default="")).strip()
    partner_token = str(partner.get("line_token") or "").strip()
    partner_to_id = str(partner.get("line_id") or "").strip()

    msg = build_push_message_wealth(
        lead_id=lead_id,
        persona=persona_name,
        primary=primary,
        secondary=secondary,
        interest=interest,
        state=st.session_state.u_state,
    )
    push_line(master_token, master_to_id, msg)
    push_line(partner_token, partner_to_id, msg)
    return lead_id


def write_lead_and_notify_health(report: Dict[str, Any], interest: str) -> str:
    tz = timezone(timedelta(hours=8))
    now_tw = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    ref_in = norm_ref(get_qp("ref", "master"))
    ref_resolved = str(partner.get("ref", "")).strip()

    lead_id = compute_lead_id(
        "health",
        HEALTH_QUIZ_VERSION,
        ref_resolved,
        st.session_state.u_name,
        st.session_state.u_state,
        interest,
        report.get("top_section", ""),
        "",
        FUNNEL_TAG,
        MODE,
    )
    if DEMO_MODE:
        return f"demo-{lead_id}"
    conn = get_conn()

    meta = {
        "lead_id": lead_id,
        "quiz_id": "health",
        "quiz_version": HEALTH_QUIZ_VERSION,
        "ref_input": ref_in,
        "ref_resolved": ref_resolved,
        "funnel": FUNNEL_TAG,
        "mode": MODE,
        "app_version": APP_VERSION,
        "session_id": st.session_state.session_id,
        "source": ACQUISITION.source,
        "campaign": ACQUISITION.campaign,
        "entry": ACQUISITION.entry,
    }

    answers_payload = build_health_answers_payload(st.session_state.answers_map, meta=meta, report=report)

    row = {
        "time": now_tw,
        "ref": ref_resolved,
        "partner_name": partner.get("name", ""),
        "client_name": st.session_state.u_name,
        "client_job": st.session_state.u_state,
        "interest": interest,
        "result": report.get("band", ""),
        "result_primary": report.get("top_section", ""),
        "result_secondary": "",
        "scores": json.dumps(answers_payload, ensure_ascii=False),
        "keyword": lead_id,
        "mode": MODE,
        "funnel": FUNNEL_TAG,
    }

    gs_append_row_best_effort(conn, "leads", row, LEADS_COLS)

    line_cfg = secret_value("line", default={}) or {}
    master_token = str(line_cfg.get("channel_access_token") or secret_value("LINE_CHANNEL_ACCESS_TOKEN", default="")).strip()
    master_to_id = str(line_cfg.get("user_id") or secret_value("LINE_USER_ID", default="")).strip()
    partner_token = str(partner.get("line_token") or "").strip()
    partner_to_id = str(partner.get("line_id") or "").strip()

    msg = build_push_message_health(
        lead_id=lead_id,
        report=report,
        interest=interest,
        state=st.session_state.u_state,
    )
    push_line(master_token, master_to_id, msg)
    push_line(partner_token, partner_to_id, msg)
    return lead_id


# =========================
# 13) LINE「可直接貼」文案（生命靈數 × 人性動物原型）
# =========================
def build_line_share_text_life_path(
    *,
    client_name: str,
    partner_name: str,
    report: Dict[str, Any],
) -> str:
    """Build a useful first-stage share without exposing the raw birth date."""
    display_name = client_name if client_name != "匿名訪客" else "我"
    return "\n".join(
        [
            "🔮【我的完整生命靈數摘要】",
            f"👤 {display_name}",
            (
                f"✨ 生命路徑：{report.get('life_path', '')}號 "
                f"{report.get('core_emoji', '')}{report.get('core_label', '')}"
            ),
            (
                f"💎 生日天賦：{report.get('birthday_number', '')}號 "
                f"{report.get('birthday_label', '')}"
            ),
            (
                f"👀 外在態度：{report.get('attitude_number', '')}號 "
                f"{report.get('attitude_label', '')}"
            ),
            (
                f"🗓️ {report.get('report_year', '')} 主題："
                f"{report.get('personal_year', '')}號 "
                f"{report.get('personal_year_focus', '')}"
            ),
            "—",
            f"💬 {report.get('cross_insight', '')}",
            f"✅ 今年可以先做：{report.get('personal_year_action', '')}",
            "—",
            f"這份探索由 {partner_name} 分享；完整結果直接看，不用先加好友。",
            "生命靈數屬於自我探索工具，不是科學心理測驗或診斷。",
        ]
    )


def build_line_share_text_birthday(
    *,
    client_name: str,
    interest: str,
    lead_id: str,
    partner_name: str,
    report: Dict[str, Any],
) -> str:
    lines = [
        "✨【生命靈數 × 人性動物原型｜結果摘要】",
        f"👤 {client_name}",
        f"🔮 我的生命原型：{report.get('combined_title','')}",
        (
            f"🔢 生命靈數：{report.get('life_path','')}號 "
            f"{report.get('core_emoji','')} {report.get('core_label','')}"
        ),
        (
            f"💎 生日天賦：{report.get('birthday_number','')}號 "
            f"{report.get('birthday_label','')}"
        ),
        (
            f"👀 外在態度：{report.get('attitude_number','')}號 "
            f"{report.get('attitude_label','')}"
        ),
        f"🐾 團隊溝通風格：{report.get('animal_emoji','')} {report.get('animal_title','')}",
        "—",
        f"💬 {report.get('summary','')}",
        "",
        "💎 我的三個優勢",
    ]
    lines.extend(f"• {strength}" for strength in report.get("strengths", [])[:3])
    lines.extend(
        [
            "",
            f"👀 容易忽略：{report.get('blind_spot','')}",
            f"🤝 和我合作：{report.get('collaboration','')}",
            f"✅ 現在可以做：{report.get('next_action','')}",
            f"🎯 想繼續探索：{interest}",
        ]
    )
    if lead_id:
        lines.append(f"🆔 lead_id：{lead_id}")
    lines.extend(
        [
            "—",
            f"這份測驗由 {partner_name} 分享；完整結果直接看，不用先加好友。",
        ]
    )
    return "\n".join(lines)


# =========================
# 14) LINE「可直接貼」文案（財富）
# =========================
def build_line_share_text_wealth(
    *,
    client_name: str,
    interest: str,
    state: str,
    primary: str,
    secondary: str,
    lead_id: str,
    partner_name: str,
    answers_map: Dict[int, str],
) -> str:
    main_short = TYPE_SHORT.get(primary, primary)
    sec_short = TYPE_SHORT.get(secondary, secondary) if secondary else ""
    type_line = f"{main_short}為主" + (f"/{sec_short}為輔" if sec_short else "")

    soothe = soothe_line_from_state(state)
    practice = PRACTICE_BY_TYPE.get(primary, PRACTICE_BY_TYPE["A"])

    lines = []
    lines.append("🧾【AI 風格診斷｜可直接貼】")
    lines.append(f"👤 受測者：{client_name}")
    lines.append(f"🎯 興趣：{interest}")
    lines.append(f"🧠 內在狀態：{state}")
    lines.append(f"🧬 類型：{type_line}")
    if lead_id:
        lines.append(f"🆔 lead_id：{lead_id}")
    lines.append("—")
    lines.append(f"📌 給顧問 {partner_name}：我想請你用這份結果，幫我對接最適合的下一步。")
    lines.append("")
    lines.append("🧩【每題選擇】")
    for i in range(1, WEALTH_TOTAL + 1):
        q_txt, opts = WEALTH_QUESTIONS[i - 1]
        tag = str(answers_map.get(i, "")).strip()
        ans_label = "（未選）"
        for lab, t in opts:
            if t == tag:
                ans_label = lab
                break
        lines.append(f"{i:02d}. {q_txt}")
        lines.append(f"→ {ans_label}")

    lines.append("")
    lines.append("🌿【溫柔小練習（30秒）】")
    lines.append(f"🫶 你的狀態：{soothe}")
    lines.append(f"⏱️ 30 秒小練習：{practice}")
    lines.append(PRACTICE_NOTE)

    return "\n".join(lines)


# =========================
# 15) LINE「可直接貼」文案（健康）
# =========================
def build_line_share_text_health(
    *,
    client_name: str,
    interest: str,
    state: str,
    lead_id: str,
    partner_name: str,
    report: Dict[str, Any],
    answers_map: Dict[int, int],
) -> str:
    band = report.get("band", "")
    total = report.get("total_scale_score", 0)
    max_s = report.get("max_scale_score", 24)
    top_sec = report.get("top_section", "")
    painpoint = report.get("painpoint", "")
    interpret = report.get("interpret", "")
    flags = report.get("flags_yes", [])
    sec_scores = report.get("sections_score", {})
    advice_lines = report.get("advice_lines", [])
    practice = report.get("practice", "")
    top_items = report.get("top_items", []) or []

    lines = []
    lines.append("🧾【健康對帳｜可直接貼】")
    lines.append(f"🎯 {painpoint}")
    lines.append(f"👤 受測者：{client_name}")
    if state:
        lines.append(f"🧠 內在狀態：{state}")
    lines.append(f"📌 結果：{band}（{total}/{max_s}）")
    if top_sec:
        lines.append(f"🔎 最需要修復的關卡：{top_sec}")
    if sec_scores:
        lines.append(
            f"📊 分項：睡覺{sec_scores.get('睡覺',0)} / 心情{sec_scores.get('心情',0)} / 消化{sec_scores.get('消化',0)} / 體質{sec_scores.get('體質',0)}"
        )
    if lead_id:
        lines.append(f"🆔 lead_id：{lead_id}")
    lines.append("—")
    lines.append(f"📌 給顧問 {partner_name}：我想請你用這份對帳，幫我安排最適合的下一步（方法/講座/節奏）。")
    lines.append("")

    lines.append("🧠【解析】")
    if interpret:
        lines.append(f"→ {interpret}")
    else:
        lines.append("→ 先把身體回到穩定，很多事就會順起來。")

    if flags:
        lines.append("🚩【紅旗提醒】我有勾到紅旗題，請先以就醫/專業評估為優先。（此測驗僅自我檢視，非醫療診斷）")

    lines.append("")
    lines.append("🎬【建議】")
    for a in advice_lines[:2]:
        lines.append(f"• {a}")
    lines.append(f"•（我這次想先對接：{interest}）")

    lines.append("")
    lines.append("🔥【Top3 訊號（含建議）】")
    if top_items:
        for t in top_items:
            lines.append(f"•（{t.get('section','')}）{t.get('text','')} → {t.get('answer','')}")
            if t.get("tip"):
                lines.append(f"  → 建議：{t.get('tip','')}")
    else:
        lines.append("• 目前沒有明顯高頻扣分訊號（維持住就很強）。")

    lines.append("")
    lines.append("🧩【每題選擇】")
    for i in range(1, HEALTH_TOTAL + 1):
        q = HEALTH_QUESTIONS[i - 1]
        val = int(answers_map.get(i, 0) or 0)
        ans = _label_for_health_value(q["options"], val)
        lines.append(f"{i:02d}. [{q['section']}] {q['text']}")
        lines.append(f"→ {ans}")

    lines.append("")
    lines.append("🌿【溫柔小練習（30秒）】")
    lines.append(f"⏱️ 30 秒小練習：{practice}")
    lines.append(PRACTICE_NOTE)

    return "\n".join(lines)


# =========================
# 16) UI：Header / Progress / Sticky CTA / Radar
# =========================
def render_header():
    st.caption(ENTRY_UI["eyebrow"])
    st.markdown(
        f'<div class="hero-title">{html_escape(ENTRY_UI["title"])}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="hero-subtitle">{html_escape(ENTRY_UI["subtitle"])}</div>',
        unsafe_allow_html=True,
    )


def progress_value(total: int):
    if st.session_state.page == "intro":
        return 0.0
    if st.session_state.page == "quiz":
        return min((int(st.session_state.step) - 1) / max(total, 1), 1.0)
    return 1.0


def render_sticky_cta(label="➕ 加顧問 LINE 領取完整報告"):
    line_sid = str(partner.get("line_search_id", "")).strip() or str(
        secret_value("MASTER_LINE_ADD", default="")
    ).strip()
    if not line_sid:
        return
    track_event(
        "line_cta_shown",
        quiz_id=st.session_state.quiz_id,
        once_key=f"line_cta_shown|{st.session_state.quiz_id}",
    )
    if line_sid.startswith("@"):
        line_url = f"https://line.me/R/ti/p/{line_sid}"
    else:
        line_url = f"https://line.me/ti/p/~{line_sid}"

    st.markdown(
        f"""
        <div class="sticky-cta-container">
            <a class="sticky-cta-btn" href="{line_url}" target="_blank">{label}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_copy_box(text: str, button_label: str, key: str):
    text_js = json.dumps(str(text or ""), ensure_ascii=False)
    safe_key = re.sub(r"[^a-zA-Z0-9_-]", "_", key)
    components.html(
        f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Microsoft JhengHei',sans-serif;">
          <button id="copy_{safe_key}" style="
            width:100%; padding:10px 12px; border-radius:12px;
            border:1px solid rgba(255,215,0,0.30);
            background:#FFD166; color:#151515; font-weight:900; cursor:pointer;
          ">{html_escape(button_label)}</button>
          <div id="msg_{safe_key}" style="margin-top:6px;color:#B8B8C6;font-size:13px;"></div>
        </div>
        <script>
          const btn = document.getElementById("copy_{safe_key}");
          const msg = document.getElementById("msg_{safe_key}");
          btn.addEventListener("click", async () => {{
            try {{
              await navigator.clipboard.writeText({text_js});
              msg.textContent = "✅ 已複製";
            }} catch (e) {{
              msg.textContent = "⚠️ 無法自動複製，請長按上方文字";
            }}
          }});
        </script>
        """,
        height=70,
    )


def render_campaign_share_pack():
    quiz_id = ACQUISITION.forced_quiz or st.session_state.quiz_id
    label = quiz_label(quiz_id)
    share_url = build_share_url(APP_PUBLIC_URL, ACQUISITION, quiz_id)
    pack = build_campaign_share_pack(
        partner_name=str(partner.get("name", "")).strip(),
        quiz_label=label,
        share_url=share_url,
    )
    with st.expander("📣 夥伴分享包｜LINE・IG・FB"):
        st.caption("文字已帶入你的 ref、來源與活動參數；可直接複製後發布。")
        tabs = st.tabs(["LINE", "Instagram", "Facebook"])
        for tab, platform, label in zip(
            tabs,
            ("line", "instagram", "facebook"),
            ("複製 LINE 分享文字", "複製 IG 貼文文字", "複製 FB 貼文文字"),
        ):
            with tab:
                st.code(pack[platform], language=None)
                render_copy_box(pack[platform], label, f"campaign_{platform}")


def render_result_share_pack(result_title: str, result_summary: str):
    quiz_id = st.session_state.quiz_id
    label = quiz_label(quiz_id)
    share_url = build_share_url(APP_PUBLIC_URL, ACQUISITION, quiz_id)
    pack = build_partner_share_pack(
        partner_name=str(partner.get("name", "")).strip(),
        client_name=st.session_state.u_name,
        quiz_label=label,
        result_title=result_title,
        result_summary=result_summary,
        share_url=share_url,
    )
    track_event(
        "share_pack_viewed",
        quiz_id=quiz_id,
        once_key=f"share_pack_viewed|{quiz_id}",
    )
    st.markdown("## 📣 分享我的結果")
    st.caption("可以分享結果，也可以讓夥伴使用跟進文字繼續對話。")
    tabs = st.tabs(["LINE", "Instagram", "Facebook", "夥伴跟進"])
    for tab, platform, label in zip(
        tabs,
        ("line", "instagram", "facebook", "follow_up"),
        ("複製 LINE 文字", "複製 IG 文字", "複製 FB 文字", "複製跟進文字"),
    ):
        with tab:
            st.code(pack[platform], language=None)
            render_copy_box(pack[platform], label, f"result_{platform}")


def render_radar_chart_birthday(scores: Dict[str, int]):
    labels = [ANIMAL_PROFILES[key]["label"] for key in (1, 2, 3, 4)]
    values = [int(scores.get(label, 0) or 0) for label in labels]

    if HAS_PLOTLY:
        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name="你的人性動物原型",
            )
        )
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(8, max(values, default=0))],
                    dtick=2,
                    showticklabels=False,
                ),
                angularaxis=dict(
                    categoryorder="array",
                    categoryarray=labels,
                    showticklabels=True,
                ),
            ),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=32, r=32, t=20, b=20),
            height=330,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    # The responsive score grid rendered below remains the fallback when
    # Plotly is unavailable, so no duplicate text list is needed here.


def render_radar_chart_wealth(answers_map: Dict[int, str]):
    counts = Counter(answers_map.values())
    a = counts.get("A", 0)
    b = counts.get("B", 0)
    c = counts.get("C", 0)
    d = counts.get("D", 0)

    if HAS_PLOTLY:
        categories = ["領航（A）", "軍師（B）", "社群（C）", "守護（D）"]
        r = [a, b, c, d]
        r.append(r[0])
        theta = categories + [categories[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=r, theta=theta, fill="toself", name="你的風格"))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, WEALTH_TOTAL], showticklabels=False),
                angularaxis=dict(showticklabels=True),
            ),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=30, r=30, t=10, b=10),
            height=280,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.write(f"A:{a}  B:{b}  C:{c}  D:{d}")


def _health_gap_label(sec_scores: Dict[str, int]) -> str:
    vals = [int(sec_scores.get(k, 0) or 0) for k in HEALTH_AXES]
    mx = max(vals) if vals else 0
    if mx == 0:
        return "維持"
    tops = [k for k in HEALTH_AXES if int(sec_scores.get(k, 0) or 0) == mx]
    return "＋".join(tops[:2]) if len(tops) >= 2 else tops[0]


def render_radar_chart_health(sec_scores: Dict[str, int]):
    # ✅ 永遠固定 4 軸 + 鎖定類別順序
    values = [int(sec_scores.get(k, 0) or 0) for k in HEALTH_AXES]
    max_range = 6  # 每關卡 0~6（兩題*3）
    gap = _health_gap_label(sec_scores)

    st.markdown("#### 🕰️ 生理時鐘雷達圖（健康缺口一眼看懂）")
    st.caption("你正在付的隱形利息在哪裡？")
    st.markdown(f"**⚠️ 缺口最大：{gap}**")

    if HAS_PLOTLY:
        theta = HEALTH_AXES + [HEALTH_AXES[0]]
        r = values + [values[0]]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=r, theta=theta, fill="toself", name="健康缺口"))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, max_range], showticklabels=False),
                angularaxis=dict(
                    categoryorder="array",
                    categoryarray=HEALTH_AXES,
                    showticklabels=True,
                ),
            ),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=30, r=30, t=10, b=10),
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.write(" / ".join([f"{k}:{int(sec_scores.get(k,0) or 0)}" for k in HEALTH_AXES]))


# =========================
# 16) Pages
# =========================
def begin_quiz(
    name: str,
    state_final: str,
    birth_year: int = 0,
    birth_month: int = 0,
    birth_day: int = 0,
) -> bool:
    is_birthday = st.session_state.quiz_id == "birthday"
    if is_birthday:
        try:
            life_path = calculate_life_path(
                birth_year,
                birth_month,
                birth_day,
            )
        except (TypeError, ValueError):
            st.warning("請先選擇正確的出生年月日。")
            return False
        st.session_state.life_path = life_path
        st.session_state.birth_energy = life_path
        st.session_state.birth_year = int(birth_year)
        st.session_state.birth_month = int(birth_month)
        st.session_state.birth_day = int(birth_day)

    st.session_state.u_name = name.strip() or "匿名訪客"
    if st.session_state.quiz_id == "wealth":
        st.session_state.u_state = state_final

    st.session_state.page = "life_path_result" if is_birthday else "quiz"
    st.session_state.step = 1
    st.session_state.answers_map = {}
    st.session_state.notified = False
    st.session_state.notified_lead_id = ""
    st.session_state.u_interest = ""
    st.session_state.u_interest_other = ""
    if is_birthday:
        life_report = build_life_path_report(
            birth_year,
            birth_month,
            birth_day,
            current_year=datetime.now().year,
        )
        track_event(
            "life_path_completed",
            quiz_id="birthday",
            meta={
                "life_path": life_report["life_path"],
                "birthday_number": life_report["birthday_number"],
                "attitude_number": life_report["attitude_number"],
                "personal_year": life_report["personal_year"],
            },
            once_key="life_path_completed|birthday",
        )
    else:
        track_event(
            "quiz_started",
            quiz_id=st.session_state.quiz_id,
            once_key=f"quiz_started|{st.session_state.quiz_id}",
        )
    st.rerun()
    return True


def begin_humanity_quiz() -> None:
    """Start the optional 20-question layer after the life-path result."""
    st.session_state.page = "quiz"
    st.session_state.step = 1
    st.session_state.answers_map = {}
    track_event(
        "humanity_quiz_started",
        quiz_id="birthday",
        meta={"question_count": BIRTHDAY_TOTAL},
        once_key="humanity_quiz_started|birthday",
    )
    track_event(
        "quiz_started",
        quiz_id="birthday",
        meta={"stage": "humanity", "question_count": BIRTHDAY_TOTAL},
        once_key="quiz_started|birthday|humanity",
    )
    st.rerun()


def page_intro():
    render_header()
    show_partner_card()
    st.progress(0.0)
    track_event("intro_viewed", quiz_id=st.session_state.quiz_id, once_key="intro_viewed")

    st.markdown("---")
    st.markdown("### 🧪 先從最有共鳴的方式認識自己")
    if ACQUISITION.forced_quiz:
        st.session_state.quiz_id = ACQUISITION.forced_quiz
    cur_id = st.session_state.quiz_id

    if ACQUISITION.forced_quiz:
        card = quiz_card_copy(cur_id)
        st.markdown(
            f"""
            <div class="glass-card">
              <div class="glass-title">{card["icon"]} {card["title"]}</div>
              <div class="glass-body">{card["desc"]}</div>
              <div class="glass-hint">已依分享連結直接帶你進入這個主題。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        active_cls = "active" if cur_id == "birthday" else ""
        st.markdown(
            f"""
            <div class="dopamine-card featured-quiz card-birthday {active_cls}">
              <div class="dopa-icon">🔮</div>
              <div class="dopa-title">10 秒看見你的生命靈數</div>
              <div class="dopa-badge">本月主打｜先看結果，不用答題</div>
              <div class="dopa-desc">完整生日一次看生命路徑、生日天賦、外在態度、數字分布與今年主題；想更深入，再自願做 20 題人性探索。</div>
              <div class="privacy-note">完整生日只用於當次計算；結果免註冊、直接看。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if cur_id != "birthday":
            if st.button("選擇 10 秒生命靈數", key="pick_birthday"):
                st.session_state.quiz_id = "birthday"
                track_event(
                    "quiz_selected",
                    quiz_id="birthday",
                    once_key="quiz_selected|birthday",
                )
                st.rerun()

        with st.expander("更多探索｜財富與健康", expanded=cur_id in {"wealth", "health"}):
            c1, c2 = st.columns(2)
            with c1:
                active_cls = "active" if cur_id == "wealth" else ""
                st.markdown(
                    f"""
                    <div class="dopamine-card card-wealth {active_cls}">
                      <div class="dopa-icon">🚀</div>
                      <div class="dopa-title">財富與行動風格</div>
                      <div class="dopa-badge">完整結果直接看</div>
                      <div class="dopa-desc">看見你的行動優勢、卡點與適合的下一步。</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("選擇財富與行動", key="pick_wealth"):
                    st.session_state.quiz_id = "wealth"
                    track_event(
                        "quiz_selected",
                        quiz_id="wealth",
                        once_key="quiz_selected|wealth",
                    )
                    st.rerun()

            with c2:
                active_cls = "active" if cur_id == "health" else ""
                st.markdown(
                    f"""
                    <div class="dopamine-card card-health {active_cls}">
                      <div class="dopa-icon">🌿</div>
                      <div class="dopa-title">健康節奏對帳</div>
                      <div class="dopa-badge">完整結果直接看</div>
                      <div class="dopa-desc">整理睡眠、心情、消化與體力訊號。</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("選擇健康節奏", key="pick_health"):
                    st.session_state.quiz_id = "health"
                    track_event(
                        "quiz_selected",
                        quiz_id="health",
                        once_key="quiz_selected|health",
                    )
                    st.rerun()

    birth_year = int(st.session_state.birth_year or 0)
    birth_month = int(st.session_state.birth_month or 0)
    birth_day = int(st.session_state.birth_day or 0)
    if st.session_state.quiz_id == "birthday":
        st.markdown("### 🎂 輸入完整生日")
        year_col, month_col, day_col = st.columns(3)
        current_year = datetime.now().year
        year_options = [0, *range(current_year, 1919, -1)]
        with year_col:
            birth_year = st.selectbox(
                "出生年份",
                year_options,
                index=year_options.index(birth_year) if birth_year in year_options else 0,
                format_func=lambda value: "請選擇年份" if value == 0 else f"{value} 年",
                key="birth_year_select_v2",
            )
        month_options = [0, *range(1, 13)]
        with month_col:
            birth_month = st.selectbox(
                "出生月份",
                month_options,
                index=month_options.index(birth_month) if birth_month in month_options else 0,
                format_func=lambda value: "請選擇月份" if value == 0 else f"{value} 月",
                key="birth_month_select_v2",
            )
        day_options = [0, *range(1, 32)]
        with day_col:
            birth_day = st.selectbox(
                "出生日",
                day_options,
                index=day_options.index(birth_day) if birth_day in day_options else 0,
                format_func=lambda value: "請選擇日期" if value == 0 else f"{value} 日",
                key="birth_day_select_v2",
                disabled=not bool(birth_month),
            )
        st.caption("🔒 年、月、日只留在這次瀏覽階段，用於推導生命靈數；不會寫入事件追蹤、名單或分享文字。")

    name = ""
    state_final = st.session_state.u_state or ""
    with st.expander("選填：讓結果更貼近你", expanded=False):
        name = st.text_input(
            "如何稱呼你？（選填）",
            placeholder="可以只填暱稱，也可以先不填",
            value="" if st.session_state.u_name == "匿名訪客" else st.session_state.u_name,
            key="u_name_input_v2",
        )

        if st.session_state.quiz_id == "wealth":
            st.markdown("### 你目前最在意的是哪一塊？（選填）")
            state_selection = st.selectbox(
                "可以先跳過",
                [STATE_PLACEHOLDER] + STATE_OPTIONS,
                index=0,
                key="u_state_select_v2",
            )

            state_other = ""
            if state_selection == "其他（可填）":
                state_other = st.text_input(
                    "其他（請填寫）",
                    value=st.session_state.u_state_other,
                    key="state_other_input",
                )
                st.session_state.u_state_other = state_other

            state_final = normalize_state(state_selection, state_other)
        elif st.session_state.quiz_id != "wealth":
            state_final = st.session_state.u_state or ""

    st.caption("免註冊，完整結果直接看；只有主動同意才會建立後續名單。")
    start_label = (
        "立即看我的完整生命靈數"
        if st.session_state.quiz_id == "birthday"
        else ENTRY_UI["start_label"]
    )
    birthday_ready = (
        st.session_state.quiz_id != "birthday"
        or bool(birth_year and birth_month and birth_day)
    )
    start_display_label = (
        start_label if birthday_ready else "請先選完整生日"
    )
    with st.container(key="inline_start_cta"):
        inline_start_clicked = st.button(
            start_display_label,
            key="start_btn",
            disabled=not birthday_ready,
        )

    with st.container(key="mobile_start_cta"):
        mobile_start_clicked = st.button(
            f"🚀 {start_display_label}",
            key="start_btn_mobile",
            disabled=not birthday_ready,
        )

    if inline_start_clicked or mobile_start_clicked:
        begin_quiz(name, state_final, birth_year, birth_month, birth_day)

    st.markdown("---")
    render_campaign_share_pack()


def page_life_path_result():
    """Show the complete birthday-derived layer before the optional 20 items."""
    show_partner_card()
    render_header()

    try:
        report = build_life_path_report(
            st.session_state.birth_year,
            st.session_state.birth_month,
            st.session_state.birth_day,
            current_year=datetime.now().year,
        )
    except (TypeError, ValueError):
        st.warning("生命靈數資料已失效，請重新輸入完整生日。")
        st.session_state.page = "intro"
        st.rerun()
        return

    track_event(
        "life_path_result_viewed",
        quiz_id="birthday",
        meta={
            "life_path": report["life_path"],
            "birthday_number": report["birthday_number"],
            "attitude_number": report["attitude_number"],
            "personal_year": report["personal_year"],
        },
        once_key="life_path_result_viewed|birthday",
    )

    display_name = (
        "你的"
        if st.session_state.u_name == "匿名訪客"
        else f"{html_escape(st.session_state.u_name)} 的"
    )
    st.markdown(
        f'<div class="hero-title">{display_name}完整生命靈數</div>',
        unsafe_allow_html=True,
    )
    st.caption("第一階段結果已完整顯示，不用做 20 題，也不用先留下聯絡資料。")

    st.markdown(
        f"## {report['core_emoji']} {report['life_path']} 號・{report['core_label']}"
    )
    st.write(report["core_essence"])
    strength_text = "、".join(report["core_strengths"])
    st.markdown(f"**核心優勢：** {strength_text}")
    st.markdown(f"**容易忽略：** {report['core_blind_spot']}")

    st.markdown("### 🧩 四組生日數字交叉解讀")
    st.markdown(
        f"""
        <div class="glass-card">
          <div class="glass-title">💎 生日天賦｜{report["birthday_number"]} 號・{html_escape(report["birthday_label"])}</div>
          <div class="glass-body">{html_escape(report["birthday_gift"])}</div>
          <div class="glass-hint">這組數字用來提醒你較容易上手、可以主動運用的能力。</div>
        </div>
        <div class="glass-card">
          <div class="glass-title">👀 外在態度｜{report["attitude_number"]} 號・{html_escape(report["attitude_label"])}</div>
          <div class="glass-body">{html_escape(report["attitude_approach"])}</div>
          <div class="glass-hint">{html_escape(report["attitude_practice"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(report["cross_insight"])

    st.markdown(
        f"### 🗓️ {report['report_year']} 個人年｜"
        f"{report['personal_year']} 號・{report['personal_year_focus']}"
    )
    st.write(
        "這是依出生月日與今年年份推導的年度提醒，"
        "適合拿來設定觀察方向，不代表事件預測。"
    )
    st.markdown(
        f"""
        <div class="glass-card">
          <div class="glass-title">✅ 今年可以先做的一步</div>
          <div class="glass-body">{html_escape(report["personal_year_action"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("看完整數字分布與待練習方向", expanded=False):
        st.markdown(
            f"**出生月份能量：** {report['month_number']} 號・"
            f"{report['month_label']}（{report['month_gift']}）"
        )
        st.markdown(
            f"**出生年份背景：** {report['generation_number']} 號・"
            f"{report['generation_label']}（{report['generation_gift']}）"
        )
        if report["repeated_numbers"]:
            st.markdown("**較常出現的數字：**")
            for item in report["repeated_numbers"]:
                st.write(
                    f"• {item['number']} 號出現 {item['count']} 次｜"
                    f"{item['label']}：{item['gift']}"
                )
        else:
            st.write("數字分布較平均，沒有出現兩次以上的非零數字。")

        if report["missing_themes"]:
            st.markdown("**生日中未出現的數字（當成練習題，不是缺點）：**")
            for item in report["missing_themes"]:
                st.write(
                    f"• {item['number']} 號・{item['label']}｜{item['practice']}"
                )
        else:
            st.write("1–9 的數字都有出現，沒有未出現的數字。")

    st.caption(
        "🔒 完整生日只留在這次瀏覽階段；事件追蹤、名單與分享文字都不含出生年月日。"
    )
    st.caption(
        "說明：生命靈數各流派的算法與詮釋不同，這裡採 1–9 單數化作為自我反思框架；"
        "不是經科學驗證的心理測驗、預測或診斷。"
    )

    st.markdown("---")
    st.markdown("## 想知道你在團隊裡怎麼被看見嗎？")
    st.write("生命靈數看內在主軸；下一階段用情境題觀察你平常的溝通與合作反應。")
    st.caption("進階人性探索｜約 2 分鐘・20 題，可隨時返回；不影響上面的生命靈數結果。")

    with st.container(key="inline_start_cta"):
        inline_advanced_clicked = st.button(
            "進階人性探索｜約 2 分鐘・20 題",
            key="start_humanity_btn",
        )
    with st.container(key="mobile_start_cta"):
        mobile_advanced_clicked = st.button(
            "🚀 進階人性探索｜20 題",
            key="start_humanity_btn_mobile",
        )
    if inline_advanced_clicked or mobile_advanced_clicked:
        begin_humanity_quiz()

    p_name = str(partner.get("name", "")).strip() or "分享夥伴"
    st.markdown("---")
    st.markdown("## 🧾 我的生命靈數｜現在就能分享")
    share_text = build_line_share_text_life_path(
        client_name=st.session_state.u_name,
        partner_name=p_name,
        report=report,
    )
    st.code(share_text, language=None)
    render_copy_box(share_text, "複製我的生命靈數", "life_path_summary")
    render_result_share_pack(
        f"{report['life_path']}號{report['core_label']}",
        report["summary"],
    )

    if st.button("重新輸入生日", key="restart_life_path"):
        reset_all(keep_profile=False)
        st.rerun()


def page_quiz():
    show_partner_card()

    quiz_id = st.session_state.quiz_id
    is_wealth = quiz_id == "wealth"
    total = quiz_total(quiz_id)
    st.progress(progress_value(total))

    step = int(st.session_state.step)
    track_event(
        "quiz_step_viewed",
        quiz_id=st.session_state.quiz_id,
        step=step,
        once_key=f"quiz_step_viewed|{st.session_state.quiz_id}|{step}",
    )
    st.markdown(f'<div class="quiz-step">第 {step} 題 / 共 {total} 題</div>', unsafe_allow_html=True)

    if quiz_id == "birthday":
        question = HUMANITY_QUESTIONS[step - 1]
        st.caption("人性探索｜請依照平常最自然的反應作答")
        st.markdown(
            f'<div class="quiz-question">{html_escape(question["text"])}</div>',
            unsafe_allow_html=True,
        )

        labels = [label for label, _ in question["options"]]
        values = [int(value) for _, value in question["options"]]
        saved_value = st.session_state.answers_map.get(step)
        default_index = (
            values.index(int(saved_value))
            if saved_value is not None and int(saved_value) in values
            else None
        )
        choice_label = st.radio(
            "請選擇最像你的選項：",
            labels,
            index=default_index,
            key=f"b_{step}",
        )

        with st.container(key="birthday_quiz_nav"):
            c1, c2 = st.columns(2)
            with c1:
                if st.button("⬅️ 上一題", key=f"b_prev_{step}"):
                    if choice_label:
                        st.session_state.answers_map[step] = values[
                            labels.index(choice_label)
                        ]
                    if step > 1:
                        st.session_state.step = step - 1
                    else:
                        st.session_state.page = "life_path_result"
                    st.rerun()

            with c2:
                btn_txt = "下一題 ➡️" if step < total else "查看我的生命原型 ✅"
                if st.button(btn_txt, key=f"b_next_{step}"):
                    if not choice_label:
                        st.warning("請先選擇一個最接近平常自己的答案。")
                        st.stop()
                    st.session_state.answers_map[step] = values[
                        labels.index(choice_label)
                    ]
                    if step < total:
                        st.session_state.step = step + 1
                        st.rerun()
                    else:
                        track_event(
                            "humanity_quiz_completed",
                            quiz_id="birthday",
                            step=total,
                            once_key="humanity_quiz_completed|birthday",
                        )
                        track_event(
                            "quiz_completed",
                            quiz_id=quiz_id,
                            step=total,
                            once_key=f"quiz_completed|{quiz_id}",
                        )
                        st.session_state.page = "result"
                        st.rerun()

    elif is_wealth:
        q_txt, opts = WEALTH_QUESTIONS[step - 1]
        st.markdown(f'<div class="quiz-question">{q_txt}</div>', unsafe_allow_html=True)

        labels = [o[0] for o in opts]
        label_to_tag = {o[0]: o[1] for o in opts}
        tag_to_label = {o[1]: o[0] for o in opts}

        saved_tag = st.session_state.answers_map.get(step)
        default_label = tag_to_label.get(saved_tag, "")
        default_index = labels.index(default_label) if default_label in labels else None
        choice = st.radio(
            "請選擇一個最像你的選項",
            labels,
            index=default_index,
            key=f"q_{step}",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 上一題", key=f"prev_{step}"):
                if choice:
                    st.session_state.answers_map[step] = label_to_tag[choice]
                if step > 1:
                    st.session_state.step = step - 1
                else:
                    st.session_state.page = "intro"
                st.rerun()

        with c2:
            btn_txt = "下一題 ➡️" if step < total else "查看結果 ✅"
            if st.button(btn_txt, key=f"next_{step}"):
                if not choice:
                    st.warning("請先選擇一個最像你的答案。")
                    st.stop()
                st.session_state.answers_map[step] = label_to_tag[choice]
                if step < total:
                    st.session_state.step = step + 1
                    st.rerun()
                else:
                    track_event(
                        "quiz_completed",
                        quiz_id=st.session_state.quiz_id,
                        step=total,
                        once_key=f"quiz_completed|{st.session_state.quiz_id}",
                    )
                    st.session_state.page = "result"
                    st.rerun()

    else:
        q = HEALTH_QUESTIONS[step - 1]
        st.caption(f"【{q['section']}】{('🚩紅旗題' if q['qtype']=='flag' else '')}".strip())
        st.markdown(f'<div class="quiz-question">{q["text"]}</div>', unsafe_allow_html=True)

        labels = [o[0] for o in q["options"]]
        vals = [int(o[1]) for o in q["options"]]

        saved_val = st.session_state.answers_map.get(step)
        default_idx = vals.index(int(saved_val)) if saved_val is not None and int(saved_val) in vals else None
        choice_label = st.radio("請選擇：", labels, index=default_idx, key=f"h_{step}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("⬅️ 上一題", key=f"h_prev_{step}"):
                if choice_label:
                    st.session_state.answers_map[step] = vals[labels.index(choice_label)]
                if step > 1:
                    st.session_state.step = step - 1
                else:
                    st.session_state.page = "intro"
                st.rerun()

        with c2:
            btn_txt = "下一題 ➡️" if step < total else "查看結果 ✅"
            if st.button(btn_txt, key=f"h_next_{step}"):
                if not choice_label:
                    st.warning("請先選擇一個最接近目前狀況的答案。")
                    st.stop()
                st.session_state.answers_map[step] = vals[labels.index(choice_label)]
                if step < total:
                    st.session_state.step = step + 1
                    st.rerun()
                else:
                    track_event(
                        "quiz_completed",
                        quiz_id=st.session_state.quiz_id,
                        step=total,
                        once_key=f"quiz_completed|{st.session_state.quiz_id}",
                    )
                    st.session_state.page = "result"
                    st.rerun()



def render_optional_interest(options: List[str], key_prefix: str) -> str:
    """Render an optional interest field without blocking the full result."""
    current = str(st.session_state.u_interest or "").strip()
    if current.startswith("其他："):
        default_index = 1 + options.index("其他（可填）")
    elif current in options:
        default_index = 1 + options.index(current)
    else:
        default_index = 0

    selection = st.selectbox(
        "想繼續深入的方向（選填）",
        [INTEREST_PLACEHOLDER] + options,
        index=default_index,
        key=f"{key_prefix}_interest_select_v2",
        disabled=bool(st.session_state.notified),
    )
    other_text = ""
    if selection == "其他（可填）":
        other_text = st.text_input(
            "其他方向",
            value=st.session_state.u_interest_other,
            key=f"{key_prefix}_interest_other_v2",
            disabled=bool(st.session_state.notified),
        )
        st.session_state.u_interest_other = str(other_text or "")

    if not st.session_state.notified:
        st.session_state.u_interest = _normalize_interest(selection, other_text)
    return str(st.session_state.u_interest or "").strip()


def save_optional_lead(save_fn, *, quiz_id: str, interest: str) -> str:
    """Persist only after the visitor explicitly opts in."""
    if not interest:
        st.caption("你可以不選興趣、不建立名單，完整結果與分享功能仍可使用。")
        return str(st.session_state.notified_lead_id or "")

    if st.session_state.notified:
        st.success("已儲存你的選擇並通知分享夥伴。")
        return str(st.session_state.notified_lead_id or "")

    st.caption("按下按鈕後，稱呼、測驗結果與興趣才會寫入名單並通知分享夥伴。")
    if st.button("同意儲存結果並通知分享夥伴", key=f"save_lead_v2_{quiz_id}"):
        try:
            track_event(
                "interest_opted_in",
                quiz_id=quiz_id,
                meta={"interest": interest},
                once_key=f"interest_opted_in|{quiz_id}|{interest}",
            )
            lead_id = str(save_fn() or "")
            st.session_state.notified = True
            st.session_state.notified_lead_id = lead_id
            track_event(
                "lead_saved",
                quiz_id=quiz_id,
                lead_id=lead_id,
                once_key=f"lead_saved|{quiz_id}|{lead_id}",
            )
            st.success("已儲存。你仍可自由選擇是否加 LINE。")
        except Exception as exc:
            st.warning("結果仍可正常查看，但名單寫入或通知暫時失敗。")
            if DEBUG:
                st.exception(exc)
    return str(st.session_state.notified_lead_id or "")


def page_result():
    show_partner_card()
    render_header()

    quiz_id = st.session_state.quiz_id
    is_wealth = quiz_id == "wealth"
    total = quiz_total(quiz_id)
    if len(st.session_state.answers_map) < total:
        st.warning("⚠️ 尚未完成全部題目，已返回未完成的位置。")
        st.session_state.page = "quiz"
        st.session_state.step = min(total, max(1, len(st.session_state.answers_map) + 1))
        st.rerun()

    display_name = (
        "你的" if st.session_state.u_name == "匿名訪客"
        else f"{html_escape(st.session_state.u_name)} 的"
    )
    st.markdown(
        f'<div class="hero-title">{display_name}完整分析報告</div>',
        unsafe_allow_html=True,
    )
    st.caption("完整結果已解鎖；以下任何聯絡與資料儲存都是選填。")

    p_name = str(partner.get("name", "")).strip() or "分享夥伴"
    render_sticky_cta(label=f"💬 加 LINE 討論這份結果")

    if quiz_id == "birthday":
        life_path = int(st.session_state.life_path or st.session_state.birth_energy or 0)
        if life_path not in BIRTHDAY_CORES:
            try:
                life_path = calculate_life_path(
                    st.session_state.birth_year,
                    st.session_state.birth_month,
                    st.session_state.birth_day,
                )
            except (TypeError, ValueError):
                st.warning("生命靈數資料已失效，請重新輸入完整生日。")
                st.session_state.page = "intro"
                st.rerun()

        report = compute_humanity_report(
            st.session_state.answers_map,
            life_path,
        )
        life_report = build_life_path_report(
            st.session_state.birth_year,
            st.session_state.birth_month,
            st.session_state.birth_day,
            current_year=datetime.now().year,
        )
        for key in (
            "birthday_number",
            "birthday_label",
            "birthday_gift",
            "attitude_number",
            "attitude_label",
            "attitude_approach",
            "personal_year",
            "personal_year_focus",
            "personal_year_action",
            "report_year",
            "cross_insight",
        ):
            report[key] = life_report[key]
        track_event(
            "result_viewed",
            quiz_id="birthday",
            meta={
                "life_path": report["life_path"],
                "animal_primary": report["primary"],
                "animal_secondary": report["secondary"],
                "animal_intensity": report["animal_intensity"],
            },
            once_key="result_viewed|birthday",
        )

        st.markdown(
            f"### {report['core_emoji']}{report['animal_emoji']} 你的生命原型：**{report['combined_title']}**"
        )
        st.markdown(
            f"**內在動力：生命靈數 {report['life_path']} 號・{report['core_label']}**"
        )
        st.markdown(
            f"**生日天賦：{report['birthday_number']} 號・{report['birthday_label']}**"
            f"｜{report['birthday_gift']}"
        )
        st.markdown(
            f"**外在態度：{report['attitude_number']} 號・{report['attitude_label']}**"
        )
        st.markdown(f"**外在／團隊風格：{report['animal_title']}**")
        st.write(report["summary"])
        st.info(report["cross_insight"])
        st.markdown(
            f"**{report['report_year']} 個人年：{report['personal_year']} 號・"
            f"{report['personal_year_focus']}**"
        )
        st.caption("完整生日不會出現在事件追蹤、名單或分享文字；只使用不含原始日期的推導數字。")

        st.markdown("#### 📊 四種動物傾向")
        render_radar_chart_birthday(report["scores"])
        score_items = "".join(
            (
                '<div class="score-item">'
                f'<div class="score-label">{html_escape(label)}</div>'
                f'<div class="score-value">{int(report["scores"][label])} 題</div>'
                "</div>"
            )
            for label in ("老虎", "海豚", "企鵝", "蜜蜂")
        )
        st.markdown(
            f'<div class="score-grid">{score_items}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("## 🧠 完整解析")
        st.markdown("### 💎 你可以信任的三個優勢")
        for strength in report["strengths"][:3]:
            st.write(f"• {strength}")

        st.markdown("### 👀 容易忽略的地方")
        st.write(report["blind_spot"])

        st.markdown("### 🤝 別人怎麼和你合作更順")
        st.write(report["collaboration"])

        st.markdown(
            f"""
            <div class="glass-card">
              <div class="glass-title">✅ 現在可以做的一步</div>
              <div class="glass-body">{html_escape(report["next_action"])}</div>
              <div class="glass-hint">先試一次，再觀察這個方法是否真的適合你。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "說明：生命靈數與動物原型是自我探索、團隊溝通的趣味工具；"
            "不是經科學驗證的心理測驗，也不是心理或醫療診斷。"
        )

        st.markdown("---")
        st.markdown("## 想把結果變成下一步嗎？")
        interest = render_optional_interest(
            BIRTHDAY_INTEREST_OPTIONS,
            "birthday",
        )
        if interest:
            outro_key = _interest_key_for_outro(interest)
            outro = BIRTHDAY_OUTRO_BY_INTEREST.get(
                outro_key,
                BIRTHDAY_OUTRO_BY_INTEREST["其他（可填）"],
            )
            st.write(outro.format(p_name=p_name))

        lead_id = save_optional_lead(
            lambda: write_lead_and_notify_birthday(report, interest),
            quiz_id="birthday",
            interest=interest,
        )

        st.markdown("---")
        st.markdown("## 🧾 我的生命原型｜可直接貼 LINE")
        share_text = build_line_share_text_birthday(
            client_name=st.session_state.u_name,
            interest=interest or "先保留結果",
            lead_id=lead_id,
            partner_name=p_name,
            report=report,
        )
        st.code(share_text, language=None)
        render_copy_box(share_text, "複製我的生命原型", "birthday_summary")
        render_result_share_pack(
            str(report["combined_title"]),
            str(report["summary"]),
        )

    elif is_wealth:
        counts = Counter(st.session_state.answers_map.values())
        primary, secondary = pick_primary_secondary(counts)
        persona_name = DB_P.get(primary, primary)
        if secondary:
            persona_name = f"{DB_P.get(primary, primary)} × {DB_P.get(secondary, secondary)}"
        tcopy = TYPE_COPY.get(primary, TYPE_COPY["A"])

        track_event(
            "result_viewed",
            quiz_id="wealth",
            meta={"primary": primary, "secondary": secondary},
            once_key="result_viewed|wealth",
        )
        st.markdown(f"### ✅ 類型：**{persona_name}**")
        st.markdown("#### 📊 四力分析雷達圖")
        render_radar_chart_wealth(st.session_state.answers_map)

        st.markdown("## 🧠 完整解析")
        soothe = soothe_line_from_state(st.session_state.u_state)
        if soothe:
            st.markdown("### 你的內在狀態")
            st.write(f"🫶 {soothe}")
        st.markdown("### 你的風格傾向")
        st.write(tcopy["analysis"])
        st.markdown("### 你可能正在經歷的感受")
        st.write(str(tcopy["understand"]))

        advice = str(tcopy["advice"]).format(p_name=p_name)
        st.markdown(
            f"""
            <div class="glass-card">
              <div class="glass-title">🧭 可以先做的一步</div>
              <div class="glass-body">{html_escape(advice)}</div>
              <div class="glass-hint">先保留結果，再由你決定要不要找 {html_escape(p_name)} 討論。</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.markdown("## 想繼續深入嗎？")
        interest = render_optional_interest(WEALTH_INTEREST_OPTIONS, "wealth")
        if interest:
            outro_key = _interest_key_for_outro(interest)
            outro_template = OUTRO_BY_INTEREST.get(
                outro_key,
                OUTRO_BY_INTEREST["其他（可填）"],
            )
            st.write(outro_template.format(p_name=p_name))

        lead_id = save_optional_lead(
            lambda: write_lead_and_notify_wealth(
                primary,
                secondary,
                persona_name,
                counts,
                interest,
            ),
            quiz_id="wealth",
            interest=interest,
        )

        st.markdown("---")
        st.markdown("## 🧾 結果摘要｜可直接貼 LINE")
        share_text = build_line_share_text_wealth(
            client_name=st.session_state.u_name,
            interest=interest or "尚未選擇",
            state=str(st.session_state.u_state),
            primary=primary,
            secondary=secondary,
            lead_id=lead_id,
            partner_name=p_name,
            answers_map=st.session_state.answers_map,
        )
        st.code(share_text, language=None)
        render_copy_box(share_text, "複製結果摘要", "wealth_summary")
        render_result_share_pack(persona_name, str(tcopy["analysis"]))

    else:
        report = compute_health_report(st.session_state.answers_map)
        band = report["band"]
        total_score = report["total_scale_score"]
        max_score = report["max_scale_score"]
        top_sec = report["top_section"]
        painpoint = report["painpoint"]
        flags = report["flags_yes"]
        sec_scores = report.get("sections_score", {}) or {}

        track_event(
            "result_viewed",
            quiz_id="health",
            meta={"band": band, "top_section": top_sec},
            once_key="result_viewed|health",
        )
        st.markdown(f"### ✅ 結果：**{band}**（{total_score}/{max_score}）")
        st.progress(min(total_score / max(max_score, 1), 1.0))
        st.markdown(f"**🔎 最高分關卡：{top_sec}**")
        st.markdown(f"**🎯 痛點句：{painpoint}**")
        render_radar_chart_health(sec_scores)

        top_items = report.get("top_items", []) or []
        if top_items:
            st.markdown("### 🔥 Top3 訊號與建議")
            for item in top_items:
                st.write(f"• （{item['section']}）{item['text']} → {item['answer']}")
                if item.get("tip"):
                    st.caption(f"✅ 建議：{item['tip']}")
        else:
            st.caption("✅ 目前沒有明顯高頻扣分訊號，繼續維持目前節奏。")

        if flags:
            st.error("🚩 你勾選了紅旗題：建議優先尋求醫療或專業評估；本測驗不是診斷。")

        st.markdown("## 🧠 完整解析")
        st.write(report.get("interpret") or "先把身體回到穩定，很多事就會順起來。")

        st.markdown("---")
        st.markdown("## 想繼續深入嗎？")
        interest = render_optional_interest(HEALTH_INTEREST_OPTIONS, "health")
        if interest:
            outro_key = _interest_key_for_outro(interest)
            outro = HEALTH_OUTRO_BY_INTEREST.get(
                outro_key,
                HEALTH_OUTRO_BY_INTEREST["其他（可填）"],
            )
            st.write(outro.format(p_name=p_name))

        lead_id = save_optional_lead(
            lambda: write_lead_and_notify_health(report, interest),
            quiz_id="health",
            interest=interest,
        )

        st.markdown("---")
        st.markdown("## 🧾 健康結果摘要｜可直接貼 LINE")
        share_text = build_line_share_text_health(
            client_name=st.session_state.u_name,
            interest=interest or "尚未選擇",
            state=str(st.session_state.u_state),
            lead_id=lead_id,
            partner_name=p_name,
            report=report,
            answers_map=st.session_state.answers_map,
        )
        st.code(share_text, language=None)
        render_copy_box(share_text, "複製健康結果摘要", "health_summary")
        render_result_share_pack(str(band), str(painpoint))

    if st.session_state.notified_lead_id:
        st.caption(f"🆔 lead_id：{st.session_state.notified_lead_id}")
    st.markdown("---")
    if st.button("重新測驗", key="reset_btn_v2"):
        reset_all(keep_profile=False)
        st.rerun()


# =========================
# 17) Admin Panel（主控/顧問）
# =========================
def sidebar_admin_panel():
    if not ADMIN_PANEL_ENABLED:
        return
    st.sidebar.write("---")
    pwd = st.sidebar.text_input("🔐 管理授權碼", type="password")
    if not pwd:
        return

    try:
        conn = get_conn()
        all_leads = gs_read(conn, "leads", ttl=0 if DEBUG else 30)
        all_leads.columns = all_leads.columns.str.strip().str.lower()

        admin_pwd = str(secret_value("ADMIN_PWD", default="")).strip()
        partner_pwd = str(partner.get("password", "")).strip()
        partner_ref = str(partner.get("ref", "")).strip()

        if admin_pwd and str(pwd) == admin_pwd:
            st.subheader("📊 團隊全名單（主控）")
            st.dataframe(all_leads, use_container_width=True)
        elif partner_pwd and str(pwd) == partner_pwd:
            st.subheader(f"📈 {partner.get('name','')} 的個人名單")
            mask = all_leads["ref"].astype(str).map(norm_ref) == norm_ref(partner_ref)
            st.dataframe(all_leads[mask], use_container_width=True)
        else:
            st.sidebar.error("密碼錯誤")

    except Exception as e:
        st.sidebar.error("後台讀取失敗（加上 ?debug=1 看原始錯誤）")
        if DEBUG:
            st.exception(e)


# =========================
# 18) Router
# =========================
if st.session_state.page == "intro":
    page_intro()
elif st.session_state.page == "life_path_result":
    page_life_path_result()
elif st.session_state.page == "quiz":
    page_quiz()
else:
    page_result()

sidebar_admin_panel()
