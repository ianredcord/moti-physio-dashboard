#!/usr/bin/env python3
"""Moti-Physio Web Dashboard — Streamlit App (Enhanced)"""

import os
import io
import json
import base64
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests as req_lib
from dotenv import load_dotenv

from moti_client import MotiClient, MotiAPIError

load_dotenv()

# ── Moti 品牌色 ──

MOTI_BLUE = "#0080ff"
MOTI_DARK = "#0a0a0a"
MOTI_GRAY = "#1a1a2e"
MOTI_LIGHT_BG = "#f0f4f8"
MOTI_CARD_BG = "#ffffff"
MOTI_TEXT = "#212121"
MOTI_SUBTEXT = "#6b7280"
MOTI_BLUE_LIGHT = "rgba(0, 128, 255, 0.08)"
MOTI_BLUE_FILL = "rgba(0, 128, 255, 0.15)"
MOTI_RED = "#ef4444"
MOTI_ORANGE = "#f59e0b"
MOTI_GREEN = "#10b981"

# ── 頁面設定 ──

st.set_page_config(
    page_title="Moti-Physio Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 自訂 CSS ──

st.markdown(f"""
<style>
    /* ── 全域字體與背景 ── */
    .stApp {{
        background-color: {MOTI_LIGHT_BG};
    }}

    /* ── 側邊欄 ── */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {MOTI_DARK} 0%, {MOTI_GRAY} 100%);
    }}
    section[data-testid="stSidebar"] * {{
        color: #ffffff !important;
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        background: rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 10px 16px;
        margin-bottom: 4px;
        transition: all 0.2s ease;
    }}
    section[data-testid="stSidebar"] .stRadio label:hover {{
        background: rgba(0, 128, 255, 0.25);
    }}

    /* ── 頁面標題 ── */
    h1 {{
        color: {MOTI_DARK} !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
        padding-bottom: 4px;
        border-bottom: 3px solid {MOTI_BLUE};
        display: inline-block;
    }}
    h2, h3 {{
        color: {MOTI_DARK} !important;
        font-weight: 600 !important;
    }}

    /* ── Metric 卡片 ── */
    div[data-testid="stMetric"] {{
        background: {MOTI_CARD_BG};
        border: 1px solid #e5e7eb;
        border-left: 4px solid {MOTI_BLUE};
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    div[data-testid="stMetric"] label {{
        color: {MOTI_SUBTEXT} !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: {MOTI_DARK} !important;
        font-weight: 700 !important;
        font-size: 1.5rem !important;
    }}

    /* ── 按鈕 ── */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {{
        background: {MOTI_BLUE} !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 28px !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px;
        box-shadow: 0 2px 8px rgba(0,128,255,0.3);
        transition: all 0.2s ease;
    }}
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {{
        background: #006acc !important;
        box-shadow: 0 4px 12px rgba(0,128,255,0.4);
        transform: translateY(-1px);
    }}
    .stButton > button {{
        border-radius: 10px !important;
        border: 1px solid #d1d5db !important;
        transition: all 0.2s ease;
    }}

    /* ── 輸入框 ── */
    .stTextInput input, .stSelectbox select {{
        border-radius: 10px !important;
        border: 1px solid #d1d5db !important;
        transition: border-color 0.2s ease;
    }}
    .stTextInput input:focus {{
        border-color: {MOTI_BLUE} !important;
        box-shadow: 0 0 0 2px rgba(0,128,255,0.15) !important;
    }}

    /* ── 資料表格 ── */
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0;
        font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{
        border-bottom-color: {MOTI_BLUE} !important;
        color: {MOTI_BLUE} !important;
    }}

    /* ── 提示框 ── */
    .stAlert {{
        border-radius: 10px !important;
    }}

    /* ── Divider ── */
    hr {{
        border-color: #e5e7eb !important;
    }}

    /* ── 表格美化 ── */
    .stTable table {{
        border-radius: 10px;
        overflow: hidden;
    }}

    /* ── 隱藏 Streamlit branding ── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)


# ── 初始化 Client ──

@st.cache_resource
def get_client():
    try:
        pid = st.secrets["PROGRAM_ID"]
        key = st.secrets["SECURITY_KEY"]
    except (KeyError, FileNotFoundError):
        pid = os.getenv("PROGRAM_ID", "")
        key = os.getenv("SECURITY_KEY", "")
    if not pid or not key:
        st.error("請設定 PROGRAM_ID 和 SECURITY_KEY（Streamlit Secrets 或 .env）")
        st.stop()
    return MotiClient(pid, key)


client = get_client()

# ── 工具函式 ──

def ts_to_date(ts):
    if not ts:
        return "-"
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return str(ts)


def gender_text(g):
    return "男" if g == 0 else "女" if g == 1 else str(g)


# 靜態分析指標中英對照
METRIC_LABELS = {
    "acromialEnd": "肩峰高度差",
    "C7CSL": "C7 偏移",
    "pelvicAxialRotation": "骨盆軸向旋轉",
    "Lt_HKA": "左側 HKA",
    "Rt_HKA": "右側 HKA",
    "cranialVertical": "頭部垂直偏移",
    "roundShoulder": "圓肩角度",
    "thoracicKyphosis": "胸椎後凸",
    "lumbarLordosis": "腰椎前凸",
    "pelvicShift": "骨盆位移",
    "pelvisTilt": "骨盆傾斜",
    "kneeFlexionRecuvatum": "膝屈曲/過伸",
    "scoliosisCobbs": "脊椎側彎 Cobb",
    "pelvicObliquity": "骨盆傾斜差",
}

METRIC_KEYS = list(METRIC_LABELS.keys())

REPORT_CATEGORY_LABELS = {
    "skeleton_result_sheet": "骨架分析",
    "expert_result_sheet": "專家報告",
    "original_image_result_sheet": "原始影像結果",
    "original_image": "原始影像",
    "risk_ranking_result_sheet": "風險排行",
    "Skeleton": "骨架分析",
    "Expert": "專家報告",
    "OriginalImage": "原始影像",
    "OriginalImageResult": "原始影像結果",
    "RiskRanking": "風險排行",
    "OHSResultSheet": "OHS 結果",
    "OneLegStand_L": "單腳站立（左）",
    "OneLegStand_R": "單腳站立（右）",
}

# ── Plotly 統一主題 ──

PLOTLY_LAYOUT = dict(
    font=dict(family="system-ui, -apple-system, sans-serif", color=MOTI_TEXT),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=50, b=20),
    title_font=dict(size=16, color=MOTI_DARK),
)

TREND_COLORS = [MOTI_BLUE, MOTI_RED, MOTI_GREEN, MOTI_ORANGE,
                "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
                "#6366f1", "#84cc16", "#06b6d4", "#e11d48",
                "#a855f7", "#22d3ee"]


def risk_color(v):
    """風險值對應顏色"""
    if v >= 70:
        return MOTI_RED
    elif v >= 40:
        return MOTI_ORANGE
    return MOTI_GREEN


# ── 掃描結果（有報告的會員） ──

AVAILABLE_REPORTS = {
    "0719-01683": {"static": [4, 5]},
    "0719-01698": {"static": [2]},
    "0719-01821": {"static": [1]},
    "0719-01894": {"static": [4, 5]},
    "0719-01950": {"static": [1]},
    "0719-01963": {"static": [0]},
    "0719-01964": {"static": [0]},
    "0719-01965": {"static": [0]},
    "0719-01966": {"static": [0]},
    "0719-01967": {"static": [0]},
    "0719-01968": {"static": [0]},
    "0719-01969": {"static": [0]},
    "0719-01970": {"static": [0]},
    "0719-01971": {"static": [0]},
    "0719-01972": {"static": [0]},
    "0719-01973": {"static": [0]},
    "0719-01974": {"static": [0]},
    "0719-01975": {"static": [0]},
    "0719-01976": {"static": [0, 1]},
    "0719-01977": {"static": [0]},
    "0719-01978": {"static": [0]},
    "0719-01979": {"static": [0]},
    "0719-01981": {"static": [0]},
    "0719-01982": {"static": [0]},
    "0719-01983": {"static": [0]},
    "0719-01984": {"static": [0, 1, 2]},
    "0719-01985": {"static": [0]},
    "0719-01986": {"static": [0, 1, 2, 3]},
    "0719-01987": {"static": [0]},
    "0719-01988": {"static": [0, 1]},
    "0719-01989": {"static": [0]},
    "0719-01990": {"static": [0]},
    "0719-01991": {"static": [0]},
}


@st.cache_data(ttl=600)
def load_scan_results():
    """載入掃描結果 JSON（含每位會員的分析統計）"""
    scan_path = Path(__file__).parent / "scan_results.json"
    if scan_path.exists():
        with open(scan_path, "r") as f:
            return json.load(f)
    return []


def build_scan_lookup():
    """建立 userId -> scan record 的查詢表"""
    results = load_scan_results()
    return {r["userId"]: r for r in results}


# ── 資料快取 ──

@st.cache_data(ttl=300, show_spinner="載入會員列表...")
def load_user_list():
    return client.get_user_list()


@st.cache_data(ttl=300, show_spinner="載入會員資訊...")
def load_user_info(user_id):
    return client.get_user_info(user_id)


@st.cache_data(ttl=300, show_spinner="載入分析列表...")
def load_analysis_list(user_id, analysis_type):
    if analysis_type == "static":
        return client.get_static_analysis_list(user_id)
    elif analysis_type == "ohs":
        return client.get_ohs_analysis_list(user_id)
    else:
        return client.get_ols_analysis_list(user_id)


def load_report(user_id, analysis_type, index):
    """取得報告（不快取，因為 presigned URL 會過期且可能回傳錯誤）"""
    if analysis_type == "static":
        return client.get_static_report(user_id, index)
    elif analysis_type == "ohs":
        return client.get_ohs_report(user_id, index)
    else:
        return client.get_ols_report(user_id, index)


def df_to_csv_bytes(df):
    """DataFrame 轉 CSV bytes（含 BOM 方便 Excel 開啟）"""
    return b'\xef\xbb\xbf' + df.to_csv(index=False).encode("utf-8")


def df_to_excel_bytes(df):
    """DataFrame 轉 Excel bytes"""
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf.getvalue()


# ══════════════════════════════════════════
#  側邊欄 — 品牌 Logo + 導覽
# ══════════════════════════════════════════

st.sidebar.markdown(f"""
<div style="text-align:center; padding: 20px 0 10px 0;">
    <div style="font-size: 2rem; font-weight: 800; letter-spacing: -1px;">
        <span style="color: {MOTI_BLUE};">Moti</span><span style="color: #ffffff;">-Physio</span>
    </div>
    <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 4px; letter-spacing: 2px; text-transform: uppercase;">
        Dashboard
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

page = st.sidebar.radio("", [
    "會員總覽",
    "會員詳情",
    "分析資料視覺化",
    "群體統計分析",
    "風險警示面板",
    "報告預覽",
], label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="text-align:center; padding: 10px 0; font-size: 0.7rem; color: #6b7280;">
    Program ID: {os.getenv("PROGRAM_ID", "")}
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
#  頁面 1：會員總覽（含分析統計 + CSV 匯出）
# ══════════════════════════════════════════

if page == "會員總覽":
    st.title("會員總覽")

    users = load_user_list()
    df = pd.DataFrame(users)
    scan_lookup = build_scan_lookup()

    # 加入分析統計欄位
    df["靜態分析筆數"] = df["userId"].apply(lambda uid: len(scan_lookup.get(uid, {}).get("static", [])))
    df["有報告"] = df["userId"].apply(lambda uid: "✅" if uid in AVAILABLE_REPORTS else "")

    # 基本統計
    members_with_analysis = int((df["靜態分析筆數"] > 0).sum())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("總會員數", f"{len(df):,}")
    if "gender" in df.columns:
        col2.metric("男性", f"{len(df[df['gender'] == 0]):,}")
        col3.metric("女性", f"{len(df[df['gender'] == 1]):,}")
    col4.metric("有分析資料", f"{members_with_analysis:,}")

    st.markdown("<br>", unsafe_allow_html=True)

    # 搜尋篩選
    col_search, col_gender, col_age, col_analysis = st.columns([2, 1, 1, 1])
    with col_search:
        search = st.text_input("搜尋（User ID / 姓名）", "", placeholder="輸入關鍵字...")
    with col_gender:
        gender_filter = st.selectbox("性別篩選", ["全部", "男", "女"])
    with col_age:
        age_range = st.slider("年齡範圍", 0, 100, (0, 100))
    with col_analysis:
        analysis_filter = st.selectbox("分析資料", ["全部", "有分析", "有報告", "無分析"])

    # 篩選邏輯
    filtered = df.copy()
    if search:
        mask = filtered.apply(
            lambda r: search.lower() in str(r.get("userId", "")).lower()
            or search.lower() in str(r.get("name", "")).lower(),
            axis=1,
        )
        filtered = filtered[mask]
    if gender_filter == "男":
        filtered = filtered[filtered["gender"] == 0]
    elif gender_filter == "女":
        filtered = filtered[filtered["gender"] == 1]
    if "age" in filtered.columns:
        filtered = filtered[
            (filtered["age"] >= age_range[0]) & (filtered["age"] <= age_range[1])
        ]
    if analysis_filter == "有分析":
        filtered = filtered[filtered["靜態分析筆數"] > 0]
    elif analysis_filter == "有報告":
        filtered = filtered[filtered["有報告"] == "✅"]
    elif analysis_filter == "無分析":
        filtered = filtered[filtered["靜態分析筆數"] == 0]

    st.caption(f"顯示 {len(filtered):,} / {len(df):,} 筆")

    # 顯示表格
    display_df = filtered[["userId", "name", "age", "gender", "signupDate", "靜態分析筆數", "有報告"]].copy()
    display_df["gender"] = display_df["gender"].apply(gender_text)
    display_df["signupDate"] = display_df["signupDate"].apply(ts_to_date)
    display_df.columns = ["User ID", "姓名", "年齡", "性別", "註冊日期", "靜態分析", "有報告"]

    st.dataframe(
        display_df.reset_index(drop=True),
        use_container_width=True,
        height=500,
    )

    # ── 匯出按鈕 ──
    st.markdown("<br>", unsafe_allow_html=True)
    col_csv, col_excel, _ = st.columns([1, 1, 4])
    with col_csv:
        st.download_button(
            "下載 CSV",
            data=df_to_csv_bytes(display_df),
            file_name=f"moti_members_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    with col_excel:
        try:
            st.download_button(
                "下載 Excel",
                data=df_to_excel_bytes(display_df),
                file_name=f"moti_members_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            st.caption("（需安裝 openpyxl 套件）")

    # 年齡分佈圖
    if "age" in df.columns:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("年齡分佈")
        fig = go.Figure(data=[go.Histogram(
            x=df["age"], nbinsx=20,
            marker_color=MOTI_BLUE,
            marker_line=dict(color="#ffffff", width=1),
        )])
        fig.update_layout(
            xaxis_title="年齡", yaxis_title="人數", height=350,
            xaxis=dict(gridcolor="#e5e7eb"),
            yaxis=dict(gridcolor="#e5e7eb"),
            **PLOTLY_LAYOUT,
        )
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════
#  頁面 2：會員詳情
# ══════════════════════════════════════════

elif page == "會員詳情":
    st.title("會員詳情")

    user_id = st.text_input("輸入 User ID", placeholder="例：0719-01597")
    if not user_id:
        st.info("請輸入 User ID 開始查詢")
        st.stop()

    # 基本資料
    try:
        info = load_user_info(user_id)
    except MotiAPIError as e:
        st.error(f"查詢失敗：{e}")
        st.stop()

    st.subheader("基本資料")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("User ID", info.get("userId", ""))
    c2.metric("年齡", info.get("age", "-"))
    c3.metric("性別", gender_text(info.get("gender")))
    c4.metric("註冊日期", ts_to_date(info.get("signupDate")))

    st.markdown("<br>", unsafe_allow_html=True)

    extra = {
        "姓名": info.get("name") or "(未填)",
        "Email": info.get("email") or "(未填)",
        "電話": info.get("phoneNum") or "(未填)",
        "生日": ts_to_date(info.get("birthDay")),
        "Trainer ID": info.get("trainerId", "-"),
    }
    st.table(pd.DataFrame(extra.items(), columns=["欄位", "值"]))

    st.divider()

    # 分析記錄總覽
    st.subheader("分析記錄")
    tab_static, tab_ohs, tab_ols = st.tabs(["靜態分析", "OHS 深蹲", "OLS 單腳站立"])

    for tab, atype, label in [
        (tab_static, "static", "靜態分析"),
        (tab_ohs, "ohs", "OHS 深蹲"),
        (tab_ols, "ols", "OLS 單腳站立"),
    ]:
        with tab:
            try:
                analyses = load_analysis_list(user_id, atype)
                if not analyses:
                    st.warning(f"無{label}記錄")
                    continue
                st.success(f"共 {len(analyses)} 筆{label}記錄")
                a_df = pd.DataFrame(analyses)
                display_cols = []
                if "analysisIndex" in a_df.columns:
                    display_cols.append("analysisIndex")
                if "measurementDate" in a_df.columns:
                    a_df["measurementDate_fmt"] = a_df["measurementDate"].apply(ts_to_date)
                    display_cols.append("measurementDate_fmt")
                if "version" in a_df.columns:
                    display_cols.append("version")
                if display_cols:
                    show = a_df[display_cols].copy()
                    show.columns = [c.replace("_fmt", "").replace("analysisIndex", "Index").replace("measurementDate", "量測日期").replace("version", "版本") for c in display_cols]
                    st.dataframe(show, use_container_width=True)

                    # 匯出分析數據
                    export_df = pd.DataFrame(analyses)
                    st.download_button(
                        f"下載 {label} CSV",
                        data=df_to_csv_bytes(export_df),
                        file_name=f"moti_{user_id}_{atype}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        key=f"export_{atype}_{user_id}",
                    )
            except MotiAPIError as e:
                st.warning(f"{label}：{e}")


# ══════════════════════════════════════════
#  頁面 3：分析資料視覺化（含多筆雷達疊加）
# ══════════════════════════════════════════

elif page == "分析資料視覺化":
    st.title("分析資料視覺化")

    user_id = st.text_input("輸入 User ID", placeholder="例：0719-01597")
    if not user_id:
        st.info("請輸入 User ID 開始查詢")
        st.stop()

    try:
        analyses = load_analysis_list(user_id, "static")
    except MotiAPIError as e:
        st.error(f"查詢失敗：{e}")
        st.stop()

    if not analyses:
        st.warning("此會員無靜態分析資料")
        st.stop()

    st.success(f"共 {len(analyses)} 筆靜態分析記錄")

    # ── 雷達圖：支援多筆疊加比較 ──
    st.subheader("風險指標雷達圖")

    analysis_options = [
        f"#{i+1} — {ts_to_date(a.get('measurementDate'))}"
        for i, a in enumerate(analyses)
    ]

    if len(analyses) > 1:
        overlay_mode = st.toggle("多筆疊加比較模式", value=False)
    else:
        overlay_mode = False

    if overlay_mode:
        selected_indices = st.multiselect(
            "選擇要疊加比較的記錄（最多 6 筆）",
            range(len(analyses)),
            default=[0, len(analyses) - 1] if len(analyses) >= 2 else [0],
            format_func=lambda i: analysis_options[i],
            max_selections=6,
        )
        if not selected_indices:
            st.info("請選擇至少一筆記錄")
            st.stop()
    else:
        selected_idx = st.selectbox("選擇分析記錄", range(len(analyses)), format_func=lambda i: analysis_options[i])
        selected_indices = [selected_idx]

    # 建立雷達圖
    fig_radar = go.Figure()
    fig_bar = None

    for trace_i, sel_idx in enumerate(selected_indices):
        selected = analyses[sel_idx]
        risk_values = []
        risk_labels = []
        for key in METRIC_KEYS:
            val = selected.get(f"{key}_RiskPercent")
            if val is not None:
                risk_values.append(float(val))
                risk_labels.append(METRIC_LABELS[key])

        if not risk_values:
            continue

        color = TREND_COLORS[trace_i % len(TREND_COLORS)]
        fill_alpha = "0.12" if overlay_mode else "0.15"
        fill_color = color.replace(")", f", {fill_alpha})") if "rgba" in color else f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},{fill_alpha})"

        fig_radar.add_trace(go.Scatterpolar(
            r=risk_values + [risk_values[0]],
            theta=risk_labels + [risk_labels[0]],
            fill="toself",
            name=analysis_options[sel_idx],
            fillcolor=fill_color,
            line=dict(color=color, width=2),
            marker=dict(size=5, color=color),
        ))

        # 單選模式才顯示風險排行
        if not overlay_mode:
            risk_df = pd.DataFrame({"指標": risk_labels, "風險 %": risk_values})
            risk_df = risk_df.sort_values("風險 %", ascending=True).reset_index(drop=True)
            fig_bar = go.Figure(go.Bar(
                x=risk_df["風險 %"],
                y=risk_df["指標"],
                orientation="h",
                marker_color=[risk_color(v) for v in risk_df["風險 %"]],
                marker_line=dict(width=0),
                text=[f"{v:.1f}%" for v in risk_df["風險 %"]],
                textposition="outside",
                textfont=dict(size=11),
            ))

    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e5e7eb", linecolor="#e5e7eb"),
            angularaxis=dict(gridcolor="#e5e7eb", linecolor="#e5e7eb"),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=520,
        title="各項風險百分比（%）" + ("— 多筆疊加比較" if overlay_mode else ""),
        showlegend=overlay_mode,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
        **PLOTLY_LAYOUT,
    )

    if overlay_mode:
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        col_radar, col_bar = st.columns([1, 1])
        with col_radar:
            st.plotly_chart(fig_radar, use_container_width=True)
        with col_bar:
            if fig_bar:
                fig_bar.update_layout(
                    height=520,
                    title="風險排行",
                    xaxis=dict(title="風險 %", range=[0, 110], gridcolor="#e5e7eb"),
                    yaxis=dict(gridcolor="#e5e7eb"),
                    **PLOTLY_LAYOUT,
                )
                st.plotly_chart(fig_bar, use_container_width=True)

    # ── 趨勢圖：多筆分析比較 ──
    if len(analyses) > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("指標趨勢變化")

        selected_metrics = st.multiselect(
            "選擇要比較的指標",
            METRIC_KEYS,
            default=["roundShoulder", "thoracicKyphosis", "lumbarLordosis"],
            format_func=lambda k: METRIC_LABELS[k],
        )

        if selected_metrics:
            dates = [ts_to_date(a.get("measurementDate")) for a in analyses]

            tab_angle, tab_risk = st.tabs(["角度趨勢", "風險趨勢"])

            with tab_angle:
                fig_trend = go.Figure()
                for i, metric in enumerate(selected_metrics):
                    values = [float(a.get(f"{metric}_Angle", 0)) for a in analyses]
                    fig_trend.add_trace(go.Scatter(
                        x=dates, y=values, mode="lines+markers",
                        name=METRIC_LABELS[metric],
                        line=dict(color=TREND_COLORS[i % len(TREND_COLORS)], width=2),
                        marker=dict(size=7),
                    ))
                fig_trend.update_layout(
                    height=400, xaxis_title="量測日期", yaxis_title="角度 (°)",
                    title="角度趨勢變化",
                    xaxis=dict(gridcolor="#e5e7eb"),
                    yaxis=dict(gridcolor="#e5e7eb"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    **PLOTLY_LAYOUT,
                )
                st.plotly_chart(fig_trend, use_container_width=True)

            with tab_risk:
                fig_risk = go.Figure()
                for i, metric in enumerate(selected_metrics):
                    values = [float(a.get(f"{metric}_RiskPercent", 0)) for a in analyses]
                    fig_risk.add_trace(go.Scatter(
                        x=dates, y=values, mode="lines+markers",
                        name=METRIC_LABELS[metric],
                        line=dict(color=TREND_COLORS[i % len(TREND_COLORS)], width=2),
                        marker=dict(size=7),
                    ))
                fig_risk.update_layout(
                    height=400, xaxis_title="量測日期", yaxis_title="風險 %",
                    title="風險百分比趨勢變化",
                    yaxis=dict(range=[0, 100], gridcolor="#e5e7eb"),
                    xaxis=dict(gridcolor="#e5e7eb"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    **PLOTLY_LAYOUT,
                )
                st.plotly_chart(fig_risk, use_container_width=True)

    # ── 角度數據表 + 匯出 ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("完整數據表")
    rows = []
    for a in analyses:
        row = {"量測日期": ts_to_date(a.get("measurementDate"))}
        for key in METRIC_KEYS:
            row[f"{METRIC_LABELS[key]} (角度)"] = a.get(f"{key}_Angle", "-")
            row[f"{METRIC_LABELS[key]} (風險%)"] = a.get(f"{key}_RiskPercent", "-")
        rows.append(row)
    data_df = pd.DataFrame(rows)
    st.dataframe(data_df, use_container_width=True)

    col_csv2, col_excel2, _ = st.columns([1, 1, 4])
    with col_csv2:
        st.download_button(
            "下載 CSV",
            data=df_to_csv_bytes(data_df),
            file_name=f"moti_{user_id}_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="viz_csv",
        )
    with col_excel2:
        try:
            st.download_button(
                "下載 Excel",
                data=df_to_excel_bytes(data_df),
                file_name=f"moti_{user_id}_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="viz_excel",
            )
        except Exception:
            st.caption("（需安裝 openpyxl 套件）")


# ══════════════════════════════════════════
#  頁面 4：群體統計分析
# ══════════════════════════════════════════

elif page == "群體統計分析":
    st.title("群體統計分析")

    users = load_user_list()
    df_users = pd.DataFrame(users)
    scan_lookup = build_scan_lookup()

    # 統計卡片
    total = len(df_users)
    with_analysis = sum(1 for u in users if len(scan_lookup.get(u.get("userId", ""), {}).get("static", [])) > 0)
    with_reports = len(AVAILABLE_REPORTS)
    no_data = total - with_analysis

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("總會員", f"{total:,}")
    c2.metric("有分析資料", f"{with_analysis:,}", f"{with_analysis/total*100:.1f}%")
    c3.metric("有報告圖片", f"{with_reports:,}", f"{with_reports/total*100:.1f}%")
    c4.metric("無任何資料", f"{no_data:,}", f"{no_data/total*100:.1f}%")

    st.divider()

    # 按需載入 — 抽樣分析
    st.subheader("抽樣會員風險分析")
    st.caption("從有分析資料的會員中抽樣載入最新分析數據，進行群體風險統計。")

    # 找有分析的會員
    members_with_data = [u["userId"] for u in users if len(scan_lookup.get(u.get("userId", ""), {}).get("static", [])) > 0]

    sample_size = st.slider("抽樣人數", min_value=5, max_value=min(100, len(members_with_data)),
                             value=min(30, len(members_with_data)))

    if st.button("開始分析", type="primary"):
        import random
        sampled = random.sample(members_with_data, min(sample_size, len(members_with_data)))

        progress = st.progress(0)
        status = st.empty()
        all_risks = []

        for i, uid in enumerate(sampled):
            status.text(f"載入 {uid} ... ({i+1}/{len(sampled)})")
            progress.progress((i + 1) / len(sampled))
            try:
                analyses = load_analysis_list(uid, "static")
                if analyses:
                    latest = analyses[-1]
                    row = {"userId": uid}
                    for key in METRIC_KEYS:
                        val = latest.get(f"{key}_RiskPercent")
                        if val is not None:
                            row[METRIC_LABELS[key]] = float(val)
                    all_risks.append(row)
            except Exception:
                continue

        progress.empty()
        status.empty()

        if not all_risks:
            st.warning("無法取得足夠數據")
            st.stop()

        risk_df = pd.DataFrame(all_risks).set_index("userId")
        st.session_state["group_risk_df"] = risk_df

    # 顯示結果
    if "group_risk_df" in st.session_state:
        risk_df = st.session_state["group_risk_df"]
        st.success(f"已載入 {len(risk_df)} 位會員的風險數據")

        # 各指標平均風險
        st.subheader("各指標平均風險百分比")
        mean_risks = risk_df.mean().sort_values(ascending=False)

        fig_group = go.Figure(go.Bar(
            x=mean_risks.values,
            y=mean_risks.index,
            orientation="h",
            marker_color=[risk_color(v) for v in mean_risks.values],
            text=[f"{v:.1f}%" for v in mean_risks.values],
            textposition="outside",
        ))
        fig_group.update_layout(
            height=500,
            xaxis=dict(title="平均風險 %", range=[0, 110], gridcolor="#e5e7eb"),
            yaxis=dict(gridcolor="#e5e7eb"),
            **PLOTLY_LAYOUT,
        )
        st.plotly_chart(fig_group, use_container_width=True)

        # 風險分佈箱型圖
        st.subheader("風險分佈箱型圖")
        fig_box = go.Figure()
        for col in risk_df.columns:
            fig_box.add_trace(go.Box(
                y=risk_df[col], name=col,
                marker_color=MOTI_BLUE,
                boxmean=True,
            ))
        fig_box.update_layout(
            height=450,
            yaxis=dict(title="風險 %", range=[0, 100], gridcolor="#e5e7eb"),
            xaxis=dict(tickangle=45),
            showlegend=False,
            **PLOTLY_LAYOUT,
        )
        st.plotly_chart(fig_box, use_container_width=True)

        # 群體雷達圖
        st.subheader("群體平均風險雷達圖")
        labels = list(mean_risks.index)
        values = list(mean_risks.values)
        fig_group_radar = go.Figure()
        fig_group_radar.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            fillcolor=MOTI_BLUE_FILL,
            line=dict(color=MOTI_BLUE, width=2),
            name="群體平均",
        ))
        fig_group_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e5e7eb"),
                angularaxis=dict(gridcolor="#e5e7eb"),
                bgcolor="rgba(0,0,0,0)",
            ),
            height=500,
            title="群體平均風險指標",
            showlegend=False,
            **PLOTLY_LAYOUT,
        )
        st.plotly_chart(fig_group_radar, use_container_width=True)

        # 性別比較
        st.subheader("性別風險差異")
        user_gender = {u.get("userId"): u.get("gender") for u in users}
        risk_df["gender"] = risk_df.index.map(lambda uid: user_gender.get(uid))
        male_df = risk_df[risk_df["gender"] == 0].drop(columns=["gender"])
        female_df = risk_df[risk_df["gender"] == 1].drop(columns=["gender"])

        if len(male_df) > 0 and len(female_df) > 0:
            fig_gender = go.Figure()
            male_mean = male_df.mean()
            female_mean = female_df.mean()
            fig_gender.add_trace(go.Scatterpolar(
                r=list(male_mean.values) + [male_mean.values[0]],
                theta=list(male_mean.index) + [male_mean.index[0]],
                fill="toself", name=f"男性 (n={len(male_df)})",
                fillcolor="rgba(59,130,246,0.12)",
                line=dict(color="#3b82f6", width=2),
            ))
            fig_gender.add_trace(go.Scatterpolar(
                r=list(female_mean.values) + [female_mean.values[0]],
                theta=list(female_mean.index) + [female_mean.index[0]],
                fill="toself", name=f"女性 (n={len(female_df)})",
                fillcolor="rgba(236,72,153,0.12)",
                line=dict(color="#ec4899", width=2),
            ))
            fig_gender.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e5e7eb"),
                    angularaxis=dict(gridcolor="#e5e7eb"),
                    bgcolor="rgba(0,0,0,0)",
                ),
                height=500, title="男女風險比較",
                legend=dict(orientation="h", yanchor="bottom", y=-0.15),
                **PLOTLY_LAYOUT,
            )
            st.plotly_chart(fig_gender, use_container_width=True)
        else:
            st.info("需要同時包含男性和女性資料才能進行性別比較")

        # 清除 gender 欄位（避免影響匯出）
        if "gender" in risk_df.columns:
            risk_df = risk_df.drop(columns=["gender"])

        # 匯出
        st.divider()
        col_csv3, col_excel3, _ = st.columns([1, 1, 4])
        with col_csv3:
            st.download_button(
                "下載群體分析 CSV",
                data=df_to_csv_bytes(risk_df.reset_index()),
                file_name=f"moti_group_analysis_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="group_csv",
            )
        with col_excel3:
            try:
                st.download_button(
                    "下載群體分析 Excel",
                    data=df_to_excel_bytes(risk_df.reset_index()),
                    file_name=f"moti_group_analysis_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="group_excel",
                )
            except Exception:
                st.caption("（需安裝 openpyxl 套件）")


# ══════════════════════════════════════════
#  頁面 5：風險警示面板
# ══════════════════════════════════════════

elif page == "風險警示面板":
    st.title("風險警示面板")

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {MOTI_RED}11, {MOTI_ORANGE}11); border: 1px solid {MOTI_ORANGE}; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="font-weight: 600; color: {MOTI_DARK}; margin-bottom: 6px;">
            掃描有分析資料的會員，找出各項指標風險值超標的會員
        </div>
        <div style="font-size: 0.8rem; color: {MOTI_SUBTEXT};">
            可設定風險閾值，快速識別需要關注的會員
        </div>
    </div>
    """, unsafe_allow_html=True)

    users = load_user_list()
    scan_lookup = build_scan_lookup()
    members_with_data = [u["userId"] for u in users if len(scan_lookup.get(u.get("userId", ""), {}).get("static", [])) > 0]

    col_thresh, col_sample = st.columns(2)
    with col_thresh:
        threshold = st.slider("風險閾值 (%)", 30, 90, 60, 5)
    with col_sample:
        scan_count = st.slider("掃描人數", 10, min(200, len(members_with_data)),
                                min(50, len(members_with_data)))

    if st.button("掃描高風險會員", type="primary"):
        import random
        sampled = random.sample(members_with_data, min(scan_count, len(members_with_data)))

        progress = st.progress(0)
        status = st.empty()
        alerts = []
        user_info_map = {u["userId"]: u for u in users}

        for i, uid in enumerate(sampled):
            status.text(f"掃描 {uid} ... ({i+1}/{len(sampled)})")
            progress.progress((i + 1) / len(sampled))
            try:
                analyses = load_analysis_list(uid, "static")
                if not analyses:
                    continue
                latest = analyses[-1]
                high_risks = []
                for key in METRIC_KEYS:
                    val = latest.get(f"{key}_RiskPercent")
                    if val is not None and float(val) >= threshold:
                        high_risks.append((METRIC_LABELS[key], float(val)))

                if high_risks:
                    u_info = user_info_map.get(uid, {})
                    alerts.append({
                        "userId": uid,
                        "name": u_info.get("name", ""),
                        "age": u_info.get("age", ""),
                        "gender": gender_text(u_info.get("gender")),
                        "high_risk_count": len(high_risks),
                        "max_risk": max(r[1] for r in high_risks),
                        "max_risk_metric": max(high_risks, key=lambda x: x[1])[0],
                        "details": high_risks,
                        "date": ts_to_date(latest.get("measurementDate")),
                    })
            except Exception:
                continue

        progress.empty()
        status.empty()
        st.session_state["risk_alerts"] = alerts
        st.session_state["risk_threshold"] = threshold

    # 顯示結果
    if "risk_alerts" in st.session_state:
        alerts = st.session_state["risk_alerts"]
        threshold_used = st.session_state.get("risk_threshold", 60)

        if not alerts:
            st.success(f"未發現風險值超過 {threshold_used}% 的會員")
        else:
            # 排序：最高風險在前
            alerts.sort(key=lambda x: x["max_risk"], reverse=True)

            # 統計卡片
            c1, c2, c3 = st.columns(3)
            c1.metric("高風險會員", f"{len(alerts)} 位")
            c2.metric("最高風險值", f"{alerts[0]['max_risk']:.1f}%")
            avg_max = sum(a["max_risk"] for a in alerts) / len(alerts)
            c3.metric("平均最高風險", f"{avg_max:.1f}%")

            st.divider()

            # 高風險會員列表
            st.subheader(f"風險值 ≥ {threshold_used}% 的會員")

            alert_rows = []
            for a in alerts:
                alert_rows.append({
                    "User ID": a["userId"],
                    "姓名": a["name"],
                    "年齡": a["age"],
                    "性別": a["gender"],
                    "超標指標數": a["high_risk_count"],
                    "最高風險指標": a["max_risk_metric"],
                    "最高風險值": f"{a['max_risk']:.1f}%",
                    "最新量測": a["date"],
                })
            alert_df = pd.DataFrame(alert_rows)
            st.dataframe(alert_df, use_container_width=True, height=400)

            # 匯出
            col_csv4, col_excel4, _ = st.columns([1, 1, 4])
            with col_csv4:
                st.download_button(
                    "下載高風險會員 CSV",
                    data=df_to_csv_bytes(alert_df),
                    file_name=f"moti_high_risk_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="alert_csv",
                )

            st.divider()

            # 高風險指標分佈
            st.subheader("高風險指標出現頻率")
            metric_counts = {}
            for a in alerts:
                for metric_name, _ in a["details"]:
                    metric_counts[metric_name] = metric_counts.get(metric_name, 0) + 1

            sorted_metrics = sorted(metric_counts.items(), key=lambda x: x[1], reverse=True)
            fig_freq = go.Figure(go.Bar(
                x=[m[1] for m in sorted_metrics],
                y=[m[0] for m in sorted_metrics],
                orientation="h",
                marker_color=MOTI_RED,
                text=[str(m[1]) for m in sorted_metrics],
                textposition="outside",
            ))
            fig_freq.update_layout(
                height=450,
                xaxis=dict(title="超標會員數", gridcolor="#e5e7eb"),
                yaxis=dict(gridcolor="#e5e7eb"),
                title=f"各指標超過 {threshold_used}% 的會員人數",
                **PLOTLY_LAYOUT,
            )
            st.plotly_chart(fig_freq, use_container_width=True)

            # 詳細展開
            st.subheader("高風險會員詳情")
            for a in alerts[:20]:
                severity = "🔴" if a["max_risk"] >= 70 else "🟡"
                with st.expander(f"{severity} {a['userId']} — {a['name'] or '(未命名)'} — 最高: {a['max_risk']:.1f}%"):
                    detail_df = pd.DataFrame(a["details"], columns=["指標", "風險 %"])
                    detail_df = detail_df.sort_values("風險 %", ascending=False)
                    st.dataframe(detail_df, use_container_width=True)


# ══════════════════════════════════════════
#  頁面 6：報告預覽（含一鍵下載）
# ══════════════════════════════════════════

elif page == "報告預覽":

    st.title("報告預覽")

    # ── 有報告的會員快速選擇 ──
    available_ids = sorted(AVAILABLE_REPORTS.keys())

    st.markdown(f"""
    <div style="background: {MOTI_BLUE_LIGHT}; border: 1px solid {MOTI_BLUE}; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">
        <div style="font-weight: 600; color: {MOTI_DARK}; margin-bottom: 6px;">
            有報告圖片的會員（共 {len(available_ids)} 位）
        </div>
        <div style="font-size: 0.8rem; color: {MOTI_SUBTEXT};">
            目前僅靜態分析有報告圖片，OHS / OLS 尚無報告資料。全部 1,977 位會員中僅 1.7% 有報告。
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_pick, col_type = st.columns(2)
    with col_pick:
        pick_mode = st.radio("選擇方式", ["從有報告的會員中選擇", "手動輸入 User ID"], horizontal=True)
    with col_type:
        analysis_type = st.selectbox("分析類型", ["static", "ohs", "ols"],
                                      format_func=lambda x: {"static": "靜態分析", "ohs": "OHS 深蹲", "ols": "OLS 單腳站立"}[x])

    if pick_mode == "從有報告的會員中選擇":
        user_options = []
        for uid in available_ids:
            indices = AVAILABLE_REPORTS[uid].get("static", [])
            idx_str = ", ".join(str(i) for i in indices)
            user_options.append(f"{uid}（{len(indices)} 筆報告，index: {idx_str}）")

        selected_user_idx = st.selectbox("選擇會員", range(len(available_ids)),
                                          format_func=lambda i: user_options[i])
        user_id = available_ids[selected_user_idx]
    else:
        user_id = st.text_input("User ID", placeholder="例：0719-01683")

    if not user_id:
        st.info("請選擇或輸入 User ID")
        st.stop()

    # 提示是否有已知報告
    if user_id in AVAILABLE_REPORTS:
        known = AVAILABLE_REPORTS[user_id]
        if analysis_type in known:
            idx_list = known[analysis_type]
            st.success(f"此會員有 {len(idx_list)} 筆 {analysis_type} 報告（index: {', '.join(str(i) for i in idx_list)}）")
        else:
            st.warning(f"此會員沒有 {analysis_type} 報告，僅有靜態分析報告。")
    else:
        st.caption("此會員不在已知有報告的清單中，仍可嘗試查詢。")

    # 載入分析列表
    try:
        analyses = load_analysis_list(user_id, analysis_type)
    except MotiAPIError as e:
        st.error(f"查詢失敗：{e}")
        st.stop()

    if not analyses:
        st.warning("無分析記錄")
        st.stop()

    # 標記哪些有報告
    known_indices = AVAILABLE_REPORTS.get(user_id, {}).get(analysis_type, [])
    analysis_options = []
    for i, a in enumerate(analyses):
        idx = a.get("analysisIndex", "?")
        date = ts_to_date(a.get("measurementDate"))
        has_report = " ✅" if idx in known_indices else ""
        analysis_options.append(f"#{i+1} — {date}（index: {idx}）{has_report}")

    # 預設選第一個有報告的
    default_sel = 0
    for i, a in enumerate(analyses):
        if a.get("analysisIndex") in known_indices:
            default_sel = i
            break

    selected_idx = st.selectbox("選擇分析記錄（✅ 表示有報告）", range(len(analyses)),
                                 index=default_sel,
                                 format_func=lambda i: analysis_options[i])

    actual_index = analyses[selected_idx].get("analysisIndex", selected_idx)

    # 取報告
    if st.button("載入報告", type="primary"):
        with st.spinner(f"載入報告中（index={actual_index}）..."):
            try:
                report = load_report(user_id, analysis_type, actual_index)
            except MotiAPIError as e:
                st.error(f"取得報告失敗：{e}")
                st.info("並非所有分析記錄都有對應報告圖片，請嘗試選擇有 ✅ 標記的記錄。")
                st.stop()

        if isinstance(report, dict) and "reports" in report:
            reports = report["reports"]
        elif isinstance(report, dict):
            reports = {k: v for k, v in report.items() if isinstance(v, list)}
        else:
            st.error("未預期的回傳格式")
            st.stop()

        # 過濾掉空的分類
        reports = {k: v for k, v in reports.items() if isinstance(v, list) and len(v) > 0}

        if not reports:
            st.warning("此記錄無報告檔案，請嘗試其他記錄。")
            st.stop()

        total_files = sum(len(v) for v in reports.values())
        st.success(f"共 {total_files} 張圖片 ｜ URL 有效期：{report.get('url_expiration_seconds', 86400) // 3600} 小時")

        # 儲存到 session_state 供下載用
        st.session_state["loaded_report"] = reports
        st.session_state["loaded_report_meta"] = {
            "user_id": user_id, "analysis_type": analysis_type, "index": actual_index
        }

    # 顯示已載入的報告
    if "loaded_report" in st.session_state:
        reports = st.session_state["loaded_report"]
        meta = st.session_state.get("loaded_report_meta", {})

        # ── 一鍵下載所有圖片 ──
        st.markdown("<br>", unsafe_allow_html=True)
        all_urls = []
        for category, pages in reports.items():
            for p_item in pages:
                url = p_item.get("presigned_url", "")
                fname = p_item.get("filename", "")
                if url:
                    all_urls.append((category, fname, url))

        if all_urls:
            col_dl, col_info = st.columns([1, 3])
            with col_dl:
                if st.button("一鍵下載全部圖片", key="download_all"):
                    download_progress = st.progress(0)
                    download_status = st.empty()
                    downloaded = []

                    for i, (cat, fname, url) in enumerate(all_urls):
                        download_status.text(f"下載 {fname} ({i+1}/{len(all_urls)})")
                        download_progress.progress((i + 1) / len(all_urls))
                        try:
                            resp = req_lib.get(url, timeout=30)
                            if resp.status_code == 200:
                                downloaded.append((f"{cat}_{fname}", resp.content))
                        except Exception:
                            continue

                    download_progress.empty()
                    download_status.empty()

                    if downloaded:
                        # 建立 ZIP
                        import zipfile
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                            for fname, content in downloaded:
                                zf.writestr(fname, content)
                        zip_buf.seek(0)

                        st.download_button(
                            f"下載 ZIP（{len(downloaded)} 張）",
                            data=zip_buf.getvalue(),
                            file_name=f"moti_report_{meta.get('user_id', '')}_{meta.get('index', '')}.zip",
                            mime="application/zip",
                            key="zip_download",
                        )
                    else:
                        st.warning("下載失敗，URL 可能已過期，請重新載入報告。")

            with col_info:
                st.caption(f"共 {len(all_urls)} 張圖片可下載")

        st.divider()

        for category, pages in reports.items():
            if not isinstance(pages, list) or not pages:
                continue
            st.subheader(REPORT_CATEGORY_LABELS.get(category, category))
            cols = st.columns(min(len(pages), 2))
            for i, p_item in enumerate(pages):
                with cols[i % len(cols)]:
                    url = p_item.get("presigned_url", "")
                    filename = p_item.get("filename", f"page_{i}")
                    st.caption(filename)
                    if url:
                        st.image(url, use_container_width=True)
                    else:
                        st.warning("無 URL")
