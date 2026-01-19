import ssl
import json
import re
import time
import random
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone, timedelta

import requests
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection


# =========================
# 0) SSL 修正（Mac 常見）
# =========================
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass


# =========================
# 1) Page Config
# =========================
st.set_page_config(page_title="2026 AI 財富診斷", page_icon="🤖", layout="centered")
APP_VERSION = "multiuser-friendly-003"
st.sidebar.caption(f"APP_VERSION: {APP_VERSION}")


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


def norm_ref(x: str) -> str:
    """ref 統一化（避免空白/大小寫造成找不到夥伴）"""
    return str(x or "").strip().lower()


DEBUG = str(get_qp("debug", "0")).lower() in ("1", "true", "yes", "y")
FUNNEL_TAG = str(get_qp("cl", "cl3")).strip()
MODE = str(get_qp("mode", "A")).strip()


def _retry(fn, *, attempts=4, base_sleep=0.5, max_sleep=3.0, name="op"):
    """
    簡易重試：應對 Streamlit Cloud / Google API 偶發 RemoteDisconnected / ConnectionError
    """
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
                st.sidebar.write(f"🔁 retry({name}) {i+1}/{attempts-1} -> {type(e).__name__}: {e} (sleep {sleep:.2f}s)")
            time.sleep(sleep)
    raise last


# =========================
# 2) CSS（每次 rerun 都注入）
# =========================
CSS_VERSION = "2026-01-19-multiuser"

st.markdown(
    f"""
    <style>
    /* CSS_VERSION:{CSS_VERSION} */
    :root{{
      --bg0:#0B0B10;
      --bg2:#1B1B28;
      --gold:#FFD700;
      --muted:#B8B8C6;
      --accent:#D3544E;
      --accent2:#FF4B4B;
      --font: 'Microsoft JhengHei', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;

      --fs-root: clamp(18px, 0.55vw + 16px, 22px);
      --fs-caption: clamp(14px, 0.25vw + 12px, 16px);

      --form-bg: #141423;
      --form-bg-2: #0E0E15;
      --form-border: rgba(255,255,255,0.16);
    }}

    html{{ font-size: var(--fs-root) !important; }}
    body, .stApp{{ font-size: 1rem !important; }}
    *{{ font-family: var(--font) !important; }}

    .stApp{{
      background:
        radial-gradient(1200px 600px at 70% 15%, rgba(255,215,0,0.10), transparent 60%),
        radial-gradient(900px 500px at 20% 30%, rgba(255,75,75,0.10), transparent 60%),
        linear-gradient(135deg, var(--bg0), var(--bg2));
    }}
    h1,h2,h3,p,div,span,label{{ color:#fff !important; }}
    p, li{{ line-height: 1.55 !important; }}
    .muted{{ color: var(--muted) !important; }}

    [data-testid="stCaptionContainer"] *{{
      font-size: var(--fs-caption) !important;
      color: rgba(255,255,255,0.72) !important;
    }}

    [data-testid="stSidebar"]{{
      background:
        radial-gradient(900px 500px at 30% 20%, rgba(255,215,0,0.08), transparent 60%),
        linear-gradient(180deg, #0E0E15, #0B0B10);
      border-right: 1px solid rgba(255,255,255,0.06);
    }}

    .partner-card{{
      position: relative;
      overflow: hidden;
      display:flex !important;
      flex-direction: row !important;
      align-items:center !important;
      gap:12px !important;
      padding:12px 14px;
      border-radius:18px;
      border:1px solid rgba(255,255,255,0.10);
      background: rgba(255,255,255,0.05);
      box-shadow: 0 10px 25px rgba(0,0,0,0.22);
      margin: 6px 0 12px 0;
    }}
    .partner-img{{
      width:56px !important;
      height:56px !important;
      max-width:56px !important;
      max-height:56px !important;
      border-radius:16px !important;
      object-fit:cover !important;
      border:1px solid rgba(255,215,0,0.25);
      flex: 0 0 auto;
      position: relative;
      z-index: 1;
    }}
    .partner-meta{{ line-height:1.15; position: relative; z-index: 2; }}
    .partner-kicker{{ font-size: 0.85rem; color:rgba(255,255,255,0.72) !important; letter-spacing:0.3px; }}
    .partner-name{{ font-size: 1.25rem; font-weight: 1000; margin-top:2px; text-shadow: 0 10px 26px rgba(0,0,0,0.20); }}
    .partner-title{{ font-size: 0.98rem; color: rgba(255,255,255,0.78) !important; margin-top:2px; }}
    .partner-ref{{ margin-top:4px; font-size: 0.82rem; color: rgba(255,255,255,0.65) !important; }}

    .sb-card{{
      position: relative;
      overflow: hidden;
      padding: 16px 14px;
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.10);
      background: rgba(255,255,255,0.05);
      box-shadow: 0 14px 35px rgba(0,0,0,0.28);
      margin-top: 10px;
    }}
    .sb-img{{
      width: 100%;
      max-width: 180px !important;
      border-radius: 18px;
      object-fit: cover;
      border: 1px solid rgba(255,215,0,0.22);
      display: block;
      margin: 0 auto 12px auto;
      position: relative;
      z-index: 1;
    }}
    .sb-kicker{{ font-size: 0.95rem; color: rgba(255,255,255,0.74) !important; letter-spacing: 0.5px; }}
    .sb-name{{ font-size: clamp(26px, 1.4vw + 18px, 38px); font-weight: 1000; line-height: 1.12; margin-top: 4px; }}
    .sb-title{{ font-size: clamp(16px, 0.6vw + 14px, 20px); color: rgba(255,255,255,0.82) !important; margin-top: 6px; }}
    .sb-ref{{ margin-top: 10px; font-size: 0.9rem; color: rgba(255,255,255,0.62) !important; }}

    .hero-title{{ font-size: clamp(32px, 2.6vw, 54px); font-weight: 1000; margin: 6px 0 2px 0; letter-spacing: 0.2px; }}
    .hero-subtitle{{ font-size: clamp(16px, 1.2vw, 22px); color: rgba(255,255,255,0.78) !important; margin: 0 0 8px 0; }}
    .quiz-step{{ font-size: clamp(20px, 1.6vw, 28px); font-weight: 1000; margin-top: 4px; }}
    .quiz-question{{ font-size: clamp(22px, 2.0vw, 34px); font-weight: 1000; margin: 6px 0 10px 0; }}

    html, body, .stApp{{ color-scheme: dark !important; }}

    .stApp input,
    .stApp textarea {{
      background-color: var(--form-bg) !important;
      color: #fff !important;
      -webkit-text-fill-color: #fff !important;
      caret-color: #fff !important;
      border: 1px solid var(--form-border) !important;
      border-radius: 14px !important;
      outline: none !important;
    }}

    .stApp div[data-baseweb="select"] > div {{
      background-color: var(--form-bg) !important;
      border: 1px solid var(--form-border) !important;
      border-radius: 14px !important;
    }}
    .stApp div[data-baseweb="select"] * {{
      color: #fff !important;
      -webkit-text-fill-color: #fff !important;
    }}

    .stProgress > div > div > div > div{{
      background: linear-gradient(90deg, var(--accent), var(--accent2));
    }}

    div.stButton > button{{
      background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
      color:#fff !important;
      border-radius: 14px;
      width: 100%;
      border: none;
      padding: 1.05rem 1.05rem;
      box-shadow: 0 14px 35px rgba(255,75,75,0.22);
      transition: 0.16s;
      font-size: 1.05rem !important;
      font-weight: 1000 !important;
    }}

    [data-testid="stLinkButton"] a{{
      display:flex !important;
      align-items:center !important;
      justify-content:center !important;
      gap:10px !important;
      width:100% !important;
      text-decoration:none !important;
      background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
      color:#fff !important;
      border-radius:14px !important;
      padding: 1.05rem 1.05rem !important;
      border: none !important;
      font-size: 1.05rem !important;
      font-weight: 1000 !important;
      box-shadow: 0 14px 35px rgba(255,75,75,0.22) !important;
      transition: 0.16s !important;
    }}

    pre, code{{
      background: rgba(255,255,255,0.06) !important;
      color: #EEE !important;
      border: 1px solid rgba(255,255,255,0.10) !important;
      border-radius: 14px !important;
      font-size: 0.98rem !important;
    }}

    .gold-gradient{{
      background: linear-gradient(90deg, #FFF2B8 0%, #FFD700 35%, #FFB84D 70%, #FFE9A6 100%);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent !important;
      text-shadow: 0 10px 28px rgba(255, 215, 0, 0.16);
    }}

    .card-badge{{
      position: absolute;
      top: 10px;
      right: 10px;
      width: clamp(22px, 0.9vw + 14px, 32px) !important;
      height: auto;
      opacity: 0.98;
      filter: drop-shadow(0 10px 22px rgba(255,215,0,0.18));
      pointer-events: none;
      z-index: 9999 !important;
    }}

    div[data-baseweb="popover"]{{ z-index: 99999 !important; }}
    div[data-baseweb="popover"] [role="listbox"],
    div[data-baseweb="popover"] ul{{
      background-color: var(--form-bg-2) !important;
      border: 1px solid rgba(255,255,255,0.14) !important;
      border-radius: 14px !important;
      overflow: hidden !important;
    }}
    div[data-baseweb="popover"] [role="option"],
    div[data-baseweb="popover"] li{{ color: #fff !important; background: transparent !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# 3) Session State
# =========================
if "page" not in st.session_state:
    st.session_state.page = "intro"  # intro / quiz / result
if "step" not in st.session_state:
    st.session_state.step = 1
if "u_name" not in st.session_state:
    st.session_state.u_name = ""
if "u_domain" not in st.session_state:
    st.session_state.u_domain = ""
if "answers_map" not in st.session_state:
    st.session_state.answers_map = {}
if "notified" not in st.session_state:
    st.session_state.notified = False
if "u_interest" not in st.session_state:
    st.session_state.u_interest = ""
if "u_interest_other" not in st.session_state:
    st.session_state.u_interest_other = ""


# =========================
# 4) Spreadsheet URL
# =========================
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1GxpOmk108RM8wd9lvrQSpngTm5_KWpKkF31bbXjZKv8/edit"
SPREADSHEET_URL = (
    sget(st.secrets, "connections", "gsheets", "spreadsheet", default=DEFAULT_SHEET_URL)
    or DEFAULT_SHEET_URL
)


# =========================
# 5) GSheets 讀寫相容封裝 + Retry
# =========================
def get_conn():
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


# =========================
# 6) Google Drive 圖片連結：最穩的做法（thumbnail）
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
    """
    把 Drive 分享連結轉成可直接顯示的圖片直連（最穩：thumbnail）
    - Drive 常擋 HEAD，所以不要用 HEAD 去 gate
    """
    if not url or pd.isna(url):
        return ""
    s = str(url).strip()
    fid = extract_drive_file_id(s)
    if fid:
        return f"https://drive.google.com/thumbnail?id={fid}&sz=w{int(width)}"
    return s


# =========================
# GSheets 自檢（debug=1）
# =========================
def gsheets_self_check():
    st.sidebar.write("---")
    st.sidebar.subheader("🧪 GSheets 連線自檢（debug=1 才顯示）")

    cfg = sget(st.secrets, "connections", "gsheets", default={}) or {}
    spreadsheet = str(cfg.get("spreadsheet", "")).strip()
    sa_file = str(cfg.get("service_account_file", "")).strip()

    st.sidebar.write("✅ [connections.gsheets]：", "OK" if cfg else "❌ 找不到")
    st.sidebar.write("📌 spreadsheet：", spreadsheet if spreadsheet else "❌ 未填")
    st.sidebar.write("📌 type：", str(cfg.get("type", "")) if cfg else "❌")
    st.sidebar.write("📌 service_account_file：", sa_file if sa_file else "（未使用檔案模式）")
    st.sidebar.caption(f"🎛️ CSS_VERSION: {CSS_VERSION}")

    if sa_file:
        p = Path(sa_file)
        st.sidebar.write("📁 檔案存在：", "✅" if p.exists() else "❌")
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                required = ["type", "client_email", "token_uri", "private_key", "project_id"]
                miss = [k for k in required if not data.get(k)]
                st.sidebar.write("🔑 JSON 欄位完整：", "✅" if not miss else f"❌ 缺少 {miss}")
                st.sidebar.write("👤 client_email：", data.get("client_email", "❌"))
                st.sidebar.write("🌐 token_uri：", data.get("token_uri", "❌"))
                st.sidebar.write("🧩 project_id：", data.get("project_id", "❌"))
            except Exception as e:
                st.sidebar.error("❌ service_account.json 不是合法 JSON 或內容不完整")
                st.sidebar.write(e)


if DEBUG:
    gsheets_self_check()


# =========================
# 7) partners（多人友善：cache_data 共用 300 秒）
# =========================
REQUIRED_PARTNER_COLS = {
    "ref", "name", "title", "img_url", "line_id", "line_search_id", "line_token", "password"
}


@st.cache_data(ttl=300, show_spinner=False)
def load_all_partners_cached(spreadsheet_url: str, debug_flag: bool):
    """
    多人友善重點：
    - 用 st.cache_data 讓同一台 Streamlit worker 在 300 秒內只讀一次 partners 表
    - 讀取本身仍帶 retry，避免 Google API 偶發斷線
    """
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
    for col in ["line_search_id", "line_id", "line_token"]:
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


try:
    df_all = load_all_partners_cached(SPREADSHEET_URL, DEBUG)
except Exception as e:
    st.error("❌ Google Sheets（partners）讀取失敗")
    st.exception(e)
    st.stop()


ref = norm_ref(get_qp("ref", "master"))
partner = pick_partner(df_all, ref)

# ✅ 直接用 thumbnail 直連（不做 HEAD gate）
p_img = drive_img(partner.get("img_url", ""), width=800)

# ✅ badge 也用 thumbnail（更穩）
BADGE_FILE_ID = "1Dz9q_hoxG4BN9YOHymw7JjqJaq5kEFGf"
BADGE_URL = drive_img(BADGE_FILE_ID, width=200)

if DEBUG:
    st.sidebar.write("---")
    st.sidebar.subheader("🖼️ Image Debug")
    st.sidebar.write("img_url(raw):", str(partner.get("img_url", "")))
    st.sidebar.write("img_url(final):", p_img)
    st.sidebar.write("badge(final):", BADGE_URL)


# =========================
# 8) Sidebar（海報式顧問卡 + 徽章）
# =========================
st.sidebar.write("---")

sb_name = str(partner.get("name", "")).strip()
sb_title = str(partner.get("title", "")).strip()
sb_ref = str(partner.get("ref", "")).strip()

img_html = (
    f'<img class="sb-img" src="{p_img}" alt="partner" loading="lazy" '
    f'onerror="this.style.display=\'none\';" />'
    if p_img else ""
)
ref_html = f'<div class="sb-ref">ref：{sb_ref}</div>' if DEBUG and sb_ref else ""

st.sidebar.markdown(
    f"""
    <div class="sb-card">
      <img class="card-badge" src="{BADGE_URL}" alt="badge" onerror="this.style.display='none';" />
      {img_html}
      <div class="sb-kicker">你的專屬顧問</div>
      <div class="sb-name gold-gradient">{sb_name}</div>
      <div class="sb-title">🎖️ {sb_title}</div>
      {ref_html}
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# 9) 主要頁面顧問卡（安全版）＋徽章
# =========================
def show_partner_card():
    name = str(partner.get("name", "")).strip()
    title = str(partner.get("title", "")).strip()

    img = str(p_img or "").strip()
    has_img = bool(img)

    ref_text = str(partner.get("ref", "")).strip()
    ref_html2 = f'<div class="partner-ref">ref：{ref_text}</div>' if DEBUG and ref_text else ""

    badge_html = (
        f'<img class="card-badge" src="{BADGE_URL}" alt="badge" onerror="this.style.display=\'none\';" />'
        if BADGE_URL else ""
    )

    if has_img:
        html = f"""
        <div class="partner-card">
          {badge_html}
          <img class="partner-img" src="{img}" alt="partner" loading="lazy"
               onerror="this.style.display='none';"
               style="width:56px;height:56px;max-width:56px;max-height:56px;object-fit:cover;border-radius:16px;" />
          <div class="partner-meta">
            <div class="partner-kicker">你的專屬顧問</div>
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
            <div class="partner-kicker">你的專屬顧問</div>
            <div class="partner-name gold-gradient">{name}</div>
            <div class="partner-title">🎖️ {title}</div>
            {ref_html2}
          </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)


# =========================
# 10) 題庫 / 文案
# =========================
questions = [
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
TOTAL = len(questions)

DB_P = {
    "A": "⚡ 領航型（Navigator）",
    "B": "🧠 軍師型（Strategist）",
    "C": "🤝 社群型（Connector）",
    "D": "🛡️ 守護型（Guardian）",
}

COPY = {
    "A": {"id": "你是領航型：越亂你越敢先走第一步。", "pain": "你最容易被「雜務＋反覆溝通」拖慢，忙到沒時間做真正的佈局。", "hook": "你會需要「引流自動化」：先把人流聚起來，讓你只做高價值決策與帶隊。", "cta": "A1", "traits": ["快狠準", "敢賭敢試", "帶頭衝第一波"], "blind": "太快＝容易分心/分散", "next": "把引流交給系統，你只要挑對的人。"},
    "B": {"id": "你是軍師型：你不是靠熱血，你靠方法。", "pain": "流程不一致、資料分散，會讓你的方法「無法複製放大」。", "hook": "你會喜歡「一套可複製 SOP」：陌生人→分類→交棒，全流程模板化。", "cta": "B1", "traits": ["系統控", "會拆解", "重視可驗證"], "blind": "想太久＝容易慢半拍", "next": "先套模板跑起來，再慢慢優化到極致。"},
    "C": {"id": "你是社群型：你一開口，人就願意靠近你。", "pain": "你常卡在：要顧很多人、要產內容、要維持熱度，最後累到轉化不成比例。", "hook": "你會需要「先分層再陪伴」：漏斗把人分類，你只把力氣用在對的人。", "cta": "C1", "traits": ["高共感", "會經營", "信任感強"], "blind": "太在乎＝容易耗能/內耗", "next": "先分層再陪伴，關係會更穩、更有效。"},
    "D": {"id": "你是守護型：你不求快，你求穩且不翻車。", "pain": "資訊太雜、風險不清楚，你就會寧可慢也不敢衝。", "hook": "你會喜歡「透明可控」：流程每一步都看得懂，覺得安全才敢放大。", "cta": "D1", "traits": ["穩健", "可靠", "風險意識強"], "blind": "太保守＝容易錯過窗口", "next": "用安全版本先跑一輪，你會越來越敢放大。"},
}

INTEREST_OPTIONS = [
    "AI 工具/自動化課",
    "健康講座（植化素/水素/生活習慣）",
    "被動收入/第二收入",
    "團隊經營/複製系統",
    "其他（可填）",
]
INTEREST_PLACEHOLDER = "請選擇（必填）"


# =========================
# 11) Header / Progress
# =========================
def progress_value():
    if st.session_state.page == "intro":
        return 0.0
    if st.session_state.page == "quiz":
        return min((int(st.session_state.step) - 1) / TOTAL, 1.0)
    return 1.0


def render_header():
    st.markdown('<div class="hero-title">© 2026 AI 財富診斷</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">10 題快速測出你的風格，價值1200元 限時免費！給你「1頁專屬解析」與下一步建議</div>',
        unsafe_allow_html=True
    )
    st.progress(progress_value())


# =========================
# 12) leads + LINE 推播（多人友善：盡量用 append_row，失敗再 fallback update）
# =========================
def push_line(token: str, to_id: str, text: str):
    if not token or not to_id:
        return
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": to_id, "messages": [{"type": "text", "text": text}]},
            timeout=8
        )
    except Exception:
        pass


LEADS_COLS = [
    "time",
    "ref",
    "partner_name",
    "client_name",
    "client_job",
    "interest",
    "result",
    "result_primary",
    "result_secondary",
    "scores",
    "keyword",
    "mode",
    "funnel",
]


def _sheet_id_from_url(url: str) -> str:
    m = re.search(r"/spreadsheets/d/([^/]+)", str(url))
    return m.group(1) if m else ""


def gs_append_row_best_effort(conn, worksheet: str, row_dict: dict, cols: list[str]) -> bool:
    """
    多人同時寫入最怕「讀-改-寫」覆蓋。
    這裡優先嘗試用 gspread worksheet.append_row（原子性較好）。
    若環境/權限不支援，再 fallback 到讀表 concat update。
    """
    values = [row_dict.get(c, "") for c in cols]

    # 1) 先嘗試從 connection 拿到底層 gspread client
    try:
        client = getattr(conn, "client", None) or getattr(conn, "_client", None)
        if client is None:
            raise AttributeError("no gspread client on connection")

        # open spreadsheet
        ss = None
        try:
            ss = client.open_by_url(SPREADSHEET_URL)
        except Exception:
            sid = _sheet_id_from_url(SPREADSHEET_URL)
            if not sid:
                raise
            ss = client.open_by_key(sid)

        ws = ss.worksheet(worksheet)

        def _do_append():
            # USER_ENTERED 讓日期、字串更像手動輸入
            return ws.append_row(values, value_input_option="USER_ENTERED")

        _retry(_do_append, name=f"append_row:{worksheet}")
        return True
    except Exception as e:
        if DEBUG:
            st.sidebar.write(f"append_row fallback -> {type(e).__name__}: {e}")

    # 2) fallback：讀取 -> concat -> update（可能覆蓋，但至少能工作）
    try:
        df_leads = gs_read(conn, worksheet, ttl=0 if DEBUG else 30)
        df_leads.columns = df_leads.columns.str.strip().str.lower()
    except Exception:
        df_leads = pd.DataFrame(columns=cols)

    for c in cols:
        if c not in df_leads.columns:
            df_leads[c] = ""

    new_df = pd.DataFrame([row_dict]).reindex(columns=cols)
    updated = pd.concat([df_leads, new_df], ignore_index=True).reindex(columns=cols)
    gs_update(conn, worksheet, updated)
    return True


def write_lead_and_notify(primary: str, secondary: str, persona_name: str, counts: Counter, keyword: str, interest: str):
    tz = timezone(timedelta(hours=8))
    now_tw = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    conn = get_conn()

    row = {
        "time": now_tw,
        "ref": str(partner.get("ref", "")).strip(),
        "partner_name": partner.get("name", ""),
        "client_name": st.session_state.u_name,
        "client_job": st.session_state.u_domain,
        "interest": interest,
        "result": persona_name,
        "result_primary": primary,
        "result_secondary": secondary,
        "scores": json.dumps(dict(counts), ensure_ascii=False),
        "keyword": keyword,
        "mode": MODE,
        "funnel": FUNNEL_TAG,
    }

    # ✅ 多人友善：優先 append
    gs_append_row_best_effort(conn, "leads", row, LEADS_COLS)

    line_cfg = sget(st.secrets, "line", default={}) or {}
    master_token = str(line_cfg.get("channel_access_token") or st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN", "")).strip()
    master_to_id = str(line_cfg.get("user_id") or st.secrets.get("LINE_USER_ID", "")).strip()

    partner_token = str(partner.get("line_token") or "").strip()
    partner_to_id = str(partner.get("line_id") or "").strip()

    msg = (
        f"🚀 新名單報到（{FUNNEL_TAG}/{MODE}）\n"
        f"👤 {st.session_state.u_name}\n"
        f"🎯 興趣：{interest}\n"
        f"🧩 類型：{primary}{('/'+secondary) if secondary else ''}  {persona_name}\n"
        f"🧷 關鍵字：{keyword}\n"
        f"💼 狀態：{st.session_state.u_domain}\n"
        f"🔗 ref：{partner.get('ref', '')}"
    )

    push_line(master_token, master_to_id, msg)
    push_line(partner_token, partner_to_id, msg)


# =========================
# Pages
# =========================
def page_intro():
    show_partner_card()
    render_header()

    line_sid = str(partner.get("line_search_id", "")).strip()
    if not line_sid:
        line_sid = str(st.secrets.get("MASTER_LINE_ADD", "")).strip()

    if line_sid:
        if line_sid.startswith("@"):
            line_url = f"https://line.me/R/ti/p/{line_sid}"
        else:
            line_url = f"https://line.me/ti/p/~{line_sid}"
        st.link_button("💬 立即加 LINE", line_url)
        st.caption("（加 LINE 後可領取專屬解析與活動資訊）")
    else:
        st.info("（尚未設定 line_search_id / MASTER_LINE_ADD）")

    st.markdown("---")
    st.markdown('<div class="hero-title">價值1200元，限時免費！想領取專屬解析？做 10 題</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">你會拿到：人格類型＋卡關點＋下一步建議</div>', unsafe_allow_html=True)

    name = st.text_input("如何稱呼你？", placeholder="輸入暱稱/名字", value=st.session_state.u_name)
    domains = ["想增加收入", "想轉型/第二收入", "想建立團隊", "想更懂AI工具", "其他"]
    default_idx = domains.index(st.session_state.u_domain) if st.session_state.u_domain in domains else 0
    domain = st.selectbox("你現在的狀態比較像？", domains, index=default_idx)

    if st.button("開始測驗 🚀", key="start_btn"):
        if name and name.strip():
            st.session_state.u_name = name.strip()
            st.session_state.u_domain = domain
            st.session_state.page = "quiz"
            st.session_state.step = 1
            st.session_state.answers_map = {}
            st.session_state.notified = False
            st.session_state.u_interest = ""
            st.session_state.u_interest_other = ""
            st.rerun()
        else:
            st.warning("請先輸入稱呼。")


def page_quiz():
    show_partner_card()
    render_header()

    step = int(st.session_state.step)
    q_txt, opts = questions[step - 1]

    st.markdown(f'<div class="quiz-step">第 {step} 題 / 共 {TOTAL} 題</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="quiz-question">{q_txt}</div>', unsafe_allow_html=True)

    labels = [o[0] for o in opts]
    label_to_tag = {o[0]: o[1] for o in opts}
    tag_to_label = {o[1]: o[0] for o in opts}

    saved_tag = st.session_state.answers_map.get(step)
    default_label = tag_to_label.get(saved_tag, labels[0])
    default_index = labels.index(default_label) if default_label in labels else 0

    choice = st.radio("請選擇一個最像你的選項", labels, index=default_index, key=f"q_{step}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅️ 上一題", key=f"prev_{step}"):
            st.session_state.answers_map[step] = label_to_tag[choice]
            if step > 1:
                st.session_state.step = step - 1
                st.session_state.page = "quiz"
            else:
                st.session_state.page = "intro"
            st.rerun()

    with c2:
        if st.button("下一題 ➡️", key=f"next_{step}"):
            st.session_state.answers_map[step] = label_to_tag[choice]
            if step < TOTAL:
                st.session_state.step = step + 1
                st.session_state.page = "quiz"
            else:
                st.session_state.page = "result"
            st.rerun()


def _interest_default_index():
    cur = str(st.session_state.u_interest or "").strip()
    if not cur:
        return 0
    if cur.startswith("其他"):
        return 1 + INTEREST_OPTIONS.index("其他（可填）")
    if cur in INTEREST_OPTIONS:
        return 1 + INTEREST_OPTIONS.index(cur)
    return 0


def _normalize_interest(selection: str, other_text: str) -> str:
    if not selection or selection == INTEREST_PLACEHOLDER:
        return ""
    if selection == "其他（可填）":
        t = str(other_text or "").strip()
        if not t:
            return ""
        return f"其他：{t}"
    return selection


def page_result():
    show_partner_card()
    render_header()

    if len(st.session_state.answers_map) < TOTAL:
        st.warning("⚠️ 你尚未完成全部題目，系統已幫你返回題目頁。")
        st.session_state.page = "quiz"
        st.session_state.step = max(1, len(st.session_state.answers_map))
        st.rerun()

    counts = Counter(st.session_state.answers_map.values())
    top = counts.most_common()
    primary = top[0][0]
    secondary = top[1][0] if len(top) > 1 and top[1][1] == top[0][1] else ""

    persona_name = DB_P.get(primary, primary)
    if secondary:
        persona_name = f"{DB_P.get(primary, primary)} × {DB_P.get(secondary, secondary)}"

    copy = COPY.get(primary, COPY["A"])
    CTA_KEYWORD = copy.get("cta", "R1")

    st.balloons()
    st.markdown(f'<div class="hero-title">{st.session_state.u_name} 的測驗結果</div>', unsafe_allow_html=True)
    st.markdown(f"### 類型：**{persona_name}**")
    st.caption("特質： " + "｜".join(copy["traits"]))

    st.markdown("### 🏆 你的強項")
    st.write(copy["id"])
    st.markdown("### ⚠️ 你最容易卡的點")
    st.write(copy["pain"])
    st.markdown("### 🔍 你會對這個特別有感（關鍵）")
    st.write(copy["hook"])
    st.markdown("### 🧭 下一步")
    st.write(f"盲點提醒：{copy['blind']}")
    st.write(f"下一步：{copy['next']}")

    st.markdown("---")
    st.markdown("### ✅ 最後一步：你對什麼課程有興趣？（必填）")

    interest_selection = st.selectbox(
        "請選擇一個最有興趣的方向",
        [INTEREST_PLACEHOLDER] + INTEREST_OPTIONS,
        index=_interest_default_index(),
        key="interest_select",
        disabled=bool(st.session_state.notified),
    )

    other_text = ""
    if interest_selection == "其他（可填）":
        other_text = st.text_input(
            "其他（請填寫）",
            value=st.session_state.u_interest_other,
            key="interest_other",
            disabled=bool(st.session_state.notified),
        )

    interest_final = _normalize_interest(interest_selection, other_text)
    if interest_selection == "其他（可填）":
        st.session_state.u_interest_other = str(other_text or "")

    if interest_final:
        st.session_state.u_interest = interest_final

    ready = bool(st.session_state.u_interest)

    if not ready and not st.session_state.notified:
        st.info("請先完成「興趣（必填）」選擇，系統才會寫入名單並推播通知。")

    if ready:
        st.markdown("---")
        st.markdown("### ✅ 想領取「1頁專屬解析＋你適合的引流方式」")
        st.write("加 LINE 後回覆關鍵字：")
        st.code(CTA_KEYWORD, language=None)
        st.caption("（下方可一鍵複製到剪貼簿）")

        kw_js = json.dumps(CTA_KEYWORD, ensure_ascii=False)
        components.html(
            f"""
            <div style="font-family:-apple-system,BlinkMacSystemFont,'Microsoft JhengHei',sans-serif;">
              <button id="copyBtn" style="
                width:100%;
                padding:12px 14px;
                border-radius:14px;
                border:1px solid rgba(255,215,0,0.25);
                background: linear-gradient(135deg, rgba(255,215,0,0.92), rgba(255,200,87,0.92));
                color:#0B0B10;
                font-weight:900;
                cursor:pointer;
              ">一鍵複製關鍵字</button>
              <div id="msg" style="margin-top:8px; color:#B8B8C6; font-size:13px;"></div>
            </div>
            <script>
              const kw = {kw_js};
              const btn = document.getElementById("copyBtn");
              const msg = document.getElementById("msg");
              btn.addEventListener("click", async () => {{
                try {{
                  await navigator.clipboard.writeText(kw);
                  msg.textContent = "✅ 已複製到剪貼簿";
                }} catch (e) {{
                  msg.textContent = "⚠️ 無法自動複製（請手動長按/複製）";
                }}
              }});
            </script>
            """,
            height=90,
        )

        if not st.session_state.notified:
            try:
                write_lead_and_notify(primary, secondary, persona_name, counts, CTA_KEYWORD, st.session_state.u_interest)
                st.session_state.notified = True
            except Exception as e:
                st.warning("名單已產生，但寫入 leads 或推播失敗。")
                if DEBUG:
                    st.exception(e)

        line_sid = str(partner.get("line_search_id", "")).strip()
        if not line_sid:
            line_sid = str(st.secrets.get("MASTER_LINE_ADD", "")).strip()

        if line_sid:
            if line_sid.startswith("@"):
                line_url = f"https://line.me/R/ti/p/{line_sid}"
            else:
                line_url = f"https://line.me/ti/p/~{line_sid}"
            st.link_button("💬 加 LINE 領取解析", line_url)
        else:
            st.info("（尚未設定 line_search_id / MASTER_LINE_ADD）")

    if st.button("重新測驗", key="reset_btn"):
        st.session_state.page = "intro"
        st.session_state.step = 1
        st.session_state.u_name = ""
        st.session_state.u_domain = ""
        st.session_state.answers_map = {}
        st.session_state.notified = False
        st.session_state.u_interest = ""
        st.session_state.u_interest_other = ""
        st.rerun()


# =========================
# 後台（側邊欄）
# =========================
def sidebar_admin_panel():
    st.sidebar.write("---")
    pwd = st.sidebar.text_input("🔐 管理授權碼", type="password")

    if not pwd:
        return

    try:
        conn = get_conn()
        all_leads = gs_read(conn, "leads", ttl=0 if DEBUG else 30)
        all_leads.columns = all_leads.columns.str.strip().str.lower()

        admin_pwd = str(st.secrets.get("ADMIN_PWD", "")).strip()
        partner_pwd = str(partner.get("password", "")).strip()
        partner_ref = str(partner.get("ref", "")).strip()

        if admin_pwd and str(pwd) == admin_pwd:
            st.subheader("📊 團隊全名單（主控）")
            st.dataframe(all_leads, use_container_width=True)

        elif partner_pwd and str(pwd) == partner_pwd:
            st.subheader(f"📈 {partner.get('name', '')} 的個人名單")
            mask = all_leads["ref"].astype(str).map(norm_ref) == norm_ref(partner_ref)
            st.dataframe(all_leads[mask], use_container_width=True)

        else:
            st.sidebar.error("密碼錯誤")

    except Exception as e:
        st.sidebar.error("後台讀取失敗（加上 ?debug=1 看原始錯誤）")
        if DEBUG:
            st.exception(e)


# =========================
# Router
# =========================
if st.session_state.page == "intro":
    page_intro()
elif st.session_state.page == "quiz":
    page_quiz()
else:
    page_result()

sidebar_admin_panel()
