import ssl
import json
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


# =========================
# 2) CSS（只注入一次，避免重覆插入）
# =========================
if "css_loaded" not in st.session_state:
    st.session_state.css_loaded = True
    st.markdown(
        """
        <style>
        :root{
          --bg0:#0B0B10;
          --bg2:#1B1B28;
          --gold:#FFD700;
          --muted:#B8B8C6;
          --accent:#D3544E;
          --accent2:#FF4B4B;
          --font: 'Microsoft JhengHei', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
        }

        .stApp{
          background:
            radial-gradient(1200px 600px at 70% 15%, rgba(255,215,0,0.10), transparent 60%),
            radial-gradient(900px 500px at 20% 30%, rgba(255,75,75,0.10), transparent 60%),
            linear-gradient(135deg, var(--bg0), var(--bg2));
        }
        *{ font-family: var(--font) !important; }
        h1,h2,h3,p,div,span,label{ color:#fff !important; }
        .muted{ color: var(--muted) !important; }

        [data-testid="stSidebar"]{
          background:
            radial-gradient(900px 500px at 30% 20%, rgba(255,215,0,0.08), transparent 60%),
            linear-gradient(180deg, #0E0E15, #0B0B10);
          border-right: 1px solid rgba(255,255,255,0.06);
        }

        /* --- Partner Card (mobile friendly) --- */
        .partner-card{
          display:flex; align-items:center; gap:12px;
          padding:12px 14px;
          border-radius:18px;
          border:1px solid rgba(255,255,255,0.10);
          background: rgba(255,255,255,0.05);
          box-shadow: 0 10px 25px rgba(0,0,0,0.22);
          margin: 6px 0 12px 0;
        }
        .partner-img{
          width:56px; height:56px; border-radius:16px;
          object-fit:cover;
          border:1px solid rgba(255,215,0,0.25);
          flex: 0 0 auto;
        }
        .partner-meta{ line-height:1.15; }
        .partner-kicker{
          font-size:12px; color:rgba(255,255,255,0.72) !important;
          letter-spacing:0.3px;
        }
        .partner-name{
          font-size: clamp(18px, 2.2vw, 24px);
          font-weight: 900;
          margin-top:2px;
        }
        .partner-title{
          font-size: clamp(13px, 1.6vw, 16px);
          color: rgba(255,255,255,0.78) !important;
          margin-top:2px;
        }
        .partner-ref{
          margin-top:4px;
          font-size:12px;
          color: rgba(255,255,255,0.65) !important;
        }

        /* --- Hero text sizes --- */
        .hero-title{
          font-size: clamp(26px, 3.2vw, 40px);
          font-weight: 1000;
          margin: 6px 0 2px 0;
          letter-spacing: 0.2px;
        }
        .hero-subtitle{
          font-size: clamp(14px, 1.7vw, 18px);
          color: rgba(255,255,255,0.78) !important;
          margin: 0 0 8px 0;
        }
        .quiz-step{
          font-size: clamp(18px, 2.1vw, 24px);
          font-weight: 900;
          margin-top: 4px;
        }
        .quiz-question{
          font-size: clamp(20px, 2.5vw, 30px);
          font-weight: 1000;
          margin: 6px 0 10px 0;
        }

        /* inputs */
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea{
          background: rgba(255,255,255,0.06) !important;
          border: 1px solid rgba(255,255,255,0.10) !important;
          color:#fff !important;
          border-radius: 14px !important;
          font-size: 16px !important;
        }
        [data-baseweb="select"] > div{
          background: rgba(255,255,255,0.06) !important;
          border: 1px solid rgba(255,255,255,0.10) !important;
          border-radius: 14px !important;
        }
        [data-baseweb="select"] *{ color:#fff !important; }

        /* progress */
        .stProgress > div > div > div > div{
          background: linear-gradient(90deg, var(--accent), var(--accent2));
        }

        /* buttons */
        div.stButton > button{
          background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
          color:#fff !important;
          border-radius: 14px;
          width: 100%;
          border: none;
          padding: 0.92rem 1rem;
          box-shadow: 0 14px 35px rgba(255,75,75,0.22);
          transition: 0.16s;
          font-size: 16px !important;
          font-weight: 900 !important;
        }
        div.stButton > button:hover{
          transform: translateY(-1px) scale(1.01);
          box-shadow: 0 18px 46px rgba(255,75,75,0.32);
        }

        /* radio option */
        div[role="radiogroup"] > label{
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.10);
          padding: 12px 14px;
          border-radius: 16px;
          margin: 10px 0;
        }
        div[role="radiogroup"] > label:hover{
          border-color: rgba(255,215,0,0.35);
          background: rgba(255,215,0,0.06);
        }
        div[role="radiogroup"] p,
        div[role="radiogroup"] span{
          font-size: clamp(16px, 1.9vw, 20px) !important;
          font-weight: 800 !important;
          line-height: 1.25 !important;
        }

        /* code */
        pre, code{
          background: rgba(255,255,255,0.06) !important;
          color: #EEE !important;
          border: 1px solid rgba(255,255,255,0.10) !important;
          border-radius: 14px !important;
          font-size: 16px !important;
        }
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


# =========================
# 4) Spreadsheet URL
# =========================
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1GxpOmk108RM8wd9lvrQSpngTm5_KWpKkF31bbXjZKv8/edit"
SPREADSHEET_URL = (
    sget(st.secrets, "connections", "gsheets", "spreadsheet", default=DEFAULT_SHEET_URL)
    or DEFAULT_SHEET_URL
)


# =========================
# 5) GSheets 讀寫相容封裝
# =========================
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)


def gs_read(conn, worksheet: str, ttl: int = 60):
    try:
        return conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet, ttl=ttl)
    except TypeError:
        return conn.read(worksheet=worksheet, ttl=ttl)


def gs_update(conn, worksheet: str, data):
    try:
        return conn.update(spreadsheet=SPREADSHEET_URL, worksheet=worksheet, data=data)
    except TypeError:
        return conn.update(worksheet=worksheet, data=data)


# =========================
# ✅ GSheets 自檢（debug=1）
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
# 6) partners
# =========================
REQUIRED_PARTNER_COLS = {
    "ref", "name", "title", "img_url", "line_id", "line_search_id", "line_token", "password"
}


def drive_img(url: str) -> str:
    if not url or pd.isna(url):
        return ""
    s = str(url).strip()
    if "/file/d/" in s:
        try:
            fid = s.split("/file/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=view&id={fid}"
        except Exception:
            return s
    if "open?id=" in s:
        try:
            fid = s.split("open?id=")[1].split("&")[0]
            return f"https://drive.google.com/uc?export=view&id={fid}"
        except Exception:
            return s
    return s


def load_all_partners():
    conn = get_conn()
    ttl = 0 if DEBUG else 60

    df_m = gs_read(conn, "partners_master", ttl=ttl)
    df_t = gs_read(conn, "partners_team", ttl=ttl)

    df_m.columns = df_m.columns.str.strip().str.lower()
    df_t.columns = df_t.columns.str.strip().str.lower()

    df_all = pd.concat([df_m, df_t], ignore_index=True)

    missing = REQUIRED_PARTNER_COLS - set(df_all.columns)
    if missing:
        st.error("❌ partners 表缺少必要欄位：")
        st.code(", ".join(sorted(missing)))
        st.stop()

    # ✅ ref 統一化（避免找不到）
    df_all["ref"] = df_all["ref"].astype(str).map(norm_ref)

    # ✅ line_search_id / line_id / line_token 也順便清理空白
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
    df_all = load_all_partners()
except Exception as e:
    st.error("❌ Google Sheets 讀取失敗（請看原始錯誤）")
    st.exception(e)
    st.stop()


ref = norm_ref(get_qp("ref", "master"))
partner = pick_partner(df_all, ref)
p_img = drive_img(partner.get("img_url", ""))


# =========================
# 7) Sidebar（桌機用）
# =========================
st.sidebar.write("---")
if p_img:
    st.sidebar.image(p_img, width=160)
st.sidebar.markdown(f"### 專屬顧問：**{partner.get('name','')}**")
st.sidebar.caption(f"🎖️ {partner.get('title','')}")
if DEBUG:
    st.sidebar.caption(f"ref：{partner.get('ref','')}")


# =========================
# 7.5) ✅ 主要頁面顧問卡（手機也看得到）
# =========================
def show_partner_card():
    name = str(partner.get("name", "")).strip()
    title = str(partner.get("title", "")).strip()
    img = str(p_img or "").strip()

    ref_text = str(partner.get("ref", "")).strip()
    ref_html = f'<div class="partner-ref">ref：{ref_text}</div>' if DEBUG and ref_text else ""

    if img:
        html = f"""
        <div class="partner-card">
          <img class="partner-img" src="{img}" alt="partner" />
          <div class="partner-meta">
            <div class="partner-kicker">你的專屬顧問</div>
            <div class="partner-name">{name}</div>
            <div class="partner-title">🎖️ {title}</div>
            {ref_html}
          </div>
        </div>
        """
    else:
        html = f"""
        <div class="partner-card">
          <div class="partner-meta">
            <div class="partner-kicker">你的專屬顧問</div>
            <div class="partner-name">{name}</div>
            <div class="partner-title">🎖️ {title}</div>
            {ref_html}
          </div>
        </div>
        """
    st.markdown(html, unsafe_allow_html=True)


# =========================
# 8) 題庫 / 文案
# =========================
questions = [
    ("① AI 起風了，你會？", [("🚀 先衝先卡位", "A"), ("🧠 先做一套方法", "B"), ("🤝 先找對的人一起", "C"), ("🛡️ 先確認不會翻車", "D")]),
    ("② 你想要的「有錢」是？", [("✨ 人生自由選擇", "A"), ("💤 睡覺也進帳", "B"), ("❤️ 顧家也能助人", "C"), ("🏦 穩穩變富安心", "D")]),
    ("③ 機會來了，你會？", [
        ("⚡ 先出手再優化", "A"),
        ("📊 先算勝率再做", "B"),
        ("👥 先組隊再放大", "C"),
        ("🧯 先看最壞情況", "D")
    ]),
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
    "A": {"id":"你是領航型：越亂你越敢先走第一步。","pain":"你最容易被「雜務＋反覆溝通」拖慢，忙到沒時間做真正的佈局。","hook":"你會需要「引流自動化」：先把人流聚起來，讓你只做高價值決策與帶隊。","cta":"A1","traits":["快狠準","敢賭敢試","帶頭衝第一波"],"blind":"太快＝容易分心/分散","next":"把引流交給系統，你只要挑對的人。"},
    "B": {"id":"你是軍師型：你不是靠熱血，你靠方法。","pain":"流程不一致、資料分散，會讓你的方法「無法複製放大」。","hook":"你會喜歡「一套可複製 SOP」：陌生人→分類→交棒，全流程模板化。","cta":"B1","traits":["系統控","會拆解","重視可驗證"],"blind":"想太久＝容易慢半拍","next":"先套模板跑起來，再慢慢優化到極致。"},
    "C": {"id":"你是社群型：你一開口，人就願意靠近你。","pain":"你常卡在：要顧很多人、要產內容、要維持熱度，最後累到轉化不成比例。","hook":"你會需要「先分層再陪伴」：漏斗把人分類，你只把力氣用在對的人。","cta":"C1","traits":["高共感","會經營","信任感強"],"blind":"太在乎＝容易耗能/內耗","next":"先分層再陪伴，關係會更穩、更有效。"},
    "D": {"id":"你是守護型：你不求快，你求穩且不翻車。","pain":"資訊太雜、風險不清楚，你就會寧可慢也不敢衝。","hook":"你會喜歡「透明可控」：流程每一步都看得懂，覺得安全才敢放大。","cta":"D1","traits":["穩健","可靠","風險意識強"],"blind":"太保守＝容易錯過窗口","next":"用安全版本先跑一輪，你會越來越敢放大。"},
}


# =========================
# 9) Header / Progress（改成 function，讓顧問卡可以放在標題上方）
# =========================
def progress_value():
    if st.session_state.page == "intro":
        return 0.0
    if st.session_state.page == "quiz":
        return min((int(st.session_state.step) - 1) / TOTAL, 1.0)
    return 1.0


def render_header():
    st.markdown('<div class="hero-title">© 2026 AI 財富診斷</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">10 題快速測出你的風格，給你「1頁專屬解析」與下一步建議</div>', unsafe_allow_html=True)
    st.progress(progress_value())


# =========================
# 10) leads + LINE 推播
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


def write_lead_and_notify(primary: str, secondary: str, persona_name: str, counts: Counter, keyword: str):
    tz = timezone(timedelta(hours=8))
    now_tw = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    conn = get_conn()

    try:
        df_leads = gs_read(conn, "leads", ttl=0 if DEBUG else 30)
        df_leads.columns = df_leads.columns.str.strip().str.lower()
    except Exception:
        df_leads = pd.DataFrame(columns=[
            "time","ref","partner_name","client_name","client_job",
            "result_primary","result_secondary","scores","keyword","mode","funnel"
        ])

    new_lead = pd.DataFrame([{
        "time": now_tw,
        "ref": str(partner.get("ref","")).strip(),
        "partner_name": partner.get("name",""),
        "client_name": st.session_state.u_name,
        "client_job": st.session_state.u_domain,
        "result_primary": primary,
        "result_secondary": secondary,
        "scores": json.dumps(dict(counts), ensure_ascii=False),
        "keyword": keyword,
        "mode": MODE,
        "funnel": FUNNEL_TAG,
    }])

    updated = pd.concat([df_leads, new_lead], ignore_index=True)
    gs_update(conn, "leads", updated)

    line_cfg = sget(st.secrets, "line", default={}) or {}
    master_token = str(line_cfg.get("channel_access_token") or st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN","")).strip()
    master_to_id = str(line_cfg.get("user_id") or st.secrets.get("LINE_USER_ID","")).strip()

    partner_token = str(partner.get("line_token") or "").strip()
    partner_to_id = str(partner.get("line_id") or "").strip()

    msg = (
        f"🚀 新名單報到（{FUNNEL_TAG}/{MODE}）\n"
        f"👤 {st.session_state.u_name}\n"
        f"🧩 類型：{primary}{('/'+secondary) if secondary else ''}  {persona_name}\n"
        f"🧷 關鍵字：{keyword}\n"
        f"💼 狀態：{st.session_state.u_domain}\n"
        f"🔗 ref：{partner.get('ref','')}"
    )

    push_line(master_token, master_to_id, msg)
    push_line(partner_token, partner_to_id, msg)


# =========================
# Pages
# =========================
def page_intro():
    show_partner_card()
    render_header()

    st.markdown('<div class="hero-title">開始前 10 秒，測出你是哪一型</div>', unsafe_allow_html=True)
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
    st.markdown(
        f'<div class="hero-title">{st.session_state.u_name} 的測驗結果</div>',
        unsafe_allow_html=True
    )
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
    st.markdown("### ✅ 想領取「1頁專屬解析＋你適合的引流方式」")
    st.write("加 LINE 後回覆關鍵字：")
    st.code(CTA_KEYWORD, language=None)
    st.caption("（下方可一鍵複製到剪貼簿）")

    # ✅ 一鍵複製（iframe 隔離，避免 removeChild）
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

    # leads + LINE 通知（只做一次）
    if not st.session_state.notified:
        try:
            write_lead_and_notify(primary, secondary, persona_name, counts, CTA_KEYWORD)
            st.session_state.notified = True
        except Exception as e:
            st.warning("名單已產生，但寫入 leads 或推播失敗。")
            if DEBUG:
                st.exception(e)

    # LINE 按鈕（原生）
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
# Router
# =========================
if st.session_state.page == "intro":
    page_intro()
elif st.session_state.page == "quiz":
    page_quiz()
else:
    page_result()

sidebar_admin_panel()
