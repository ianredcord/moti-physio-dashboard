#!/usr/bin/env python3
"""Moti-Physio Web Dashboard — Streamlit App"""

import os
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
    # 優先用 Streamlit Secrets（線上部署），其次用 .env（本地開發）
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


def risk_color(v):
    """風險值對應顏色"""
    if v >= 70:
        return MOTI_RED
    elif v >= 40:
        return MOTI_ORANGE
    return MOTI_GREEN


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
    "報告預覽",
], label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="text-align:center; padding: 10px 0; font-size: 0.7rem; color: #6b7280;">
    Program ID: {os.getenv("PROGRAM_ID", "")}
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════
#  頁面 1：會員總覽
# ══════════════════════════════════════════

if page == "會員總覽":
    st.title("會員總覽")

    users = load_user_list()
    df = pd.DataFrame(users)

    # 基本統計
    col1, col2, col3 = st.columns(3)
    col1.metric("總會員數", f"{len(df):,}")
    if "gender" in df.columns:
        col2.metric("男性", f"{len(df[df['gender'] == 0]):,}")
        col3.metric("女性", f"{len(df[df['gender'] == 1]):,}")

    st.markdown("<br>", unsafe_allow_html=True)

    # 搜尋篩選
    col_search, col_gender, col_age = st.columns([2, 1, 1])
    with col_search:
        search = st.text_input("搜尋（User ID / 姓名）", "", placeholder="輸入關鍵字...")
    with col_gender:
        gender_filter = st.selectbox("性別篩選", ["全部", "男", "女"])
    with col_age:
        age_range = st.slider("年齡範圍", 0, 100, (0, 100))

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

    st.caption(f"顯示 {len(filtered):,} / {len(df):,} 筆")

    # 顯示表格
    display_df = filtered[["userId", "name", "age", "gender", "signupDate"]].copy()
    display_df["gender"] = display_df["gender"].apply(gender_text)
    display_df["signupDate"] = display_df["signupDate"].apply(ts_to_date)
    display_df.columns = ["User ID", "姓名", "年齡", "性別", "註冊日期"]

    st.dataframe(
        display_df.reset_index(drop=True),
        use_container_width=True,
        height=500,
    )

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
            except MotiAPIError as e:
                st.warning(f"{label}：{e}")


# ══════════════════════════════════════════
#  頁面 3：分析資料視覺化
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

    # ── 雷達圖：選擇一筆分析 ──
    st.subheader("風險指標雷達圖")

    analysis_options = [
        f"#{i+1} — {ts_to_date(a.get('measurementDate'))}"
        for i, a in enumerate(analyses)
    ]

    selected_idx = st.selectbox("選擇分析記錄", range(len(analyses)), format_func=lambda i: analysis_options[i])
    selected = analyses[selected_idx]

    # 取風險百分比
    risk_values = []
    risk_labels = []
    for key in METRIC_KEYS:
        val = selected.get(f"{key}_RiskPercent")
        if val is not None:
            risk_values.append(float(val))
            risk_labels.append(METRIC_LABELS[key])

    if risk_values:
        col_radar, col_bar = st.columns([1, 1])

        with col_radar:
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=risk_values + [risk_values[0]],
                theta=risk_labels + [risk_labels[0]],
                fill="toself",
                name=analysis_options[selected_idx],
                fillcolor=MOTI_BLUE_FILL,
                line=dict(color=MOTI_BLUE, width=2),
                marker=dict(size=5, color=MOTI_BLUE),
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e5e7eb", linecolor="#e5e7eb"),
                    angularaxis=dict(gridcolor="#e5e7eb", linecolor="#e5e7eb"),
                    bgcolor="rgba(0,0,0,0)",
                ),
                height=480,
                title="各項風險百分比（%）",
                showlegend=False,
                **PLOTLY_LAYOUT,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_bar:
            # 風險排行
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
            fig_bar.update_layout(
                height=480,
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

        trend_colors = [MOTI_BLUE, MOTI_RED, MOTI_GREEN, MOTI_ORANGE,
                        "#8b5cf6", "#ec4899", "#14b8a6", "#f97316",
                        "#6366f1", "#84cc16", "#06b6d4", "#e11d48",
                        "#a855f7", "#22d3ee"]

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
                        line=dict(color=trend_colors[i % len(trend_colors)], width=2),
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
                        line=dict(color=trend_colors[i % len(trend_colors)], width=2),
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

    # ── 角度數據表 ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("完整數據表")
    rows = []
    for a in analyses:
        row = {"量測日期": ts_to_date(a.get("measurementDate"))}
        for key in METRIC_KEYS:
            row[f"{METRIC_LABELS[key]} (角度)"] = a.get(f"{key}_Angle", "-")
            row[f"{METRIC_LABELS[key]} (風險%)"] = a.get(f"{key}_RiskPercent", "-")
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ══════════════════════════════════════════
#  頁面 4：報告預覽
# ══════════════════════════════════════════

elif page == "報告預覽":

    # 掃描結果：有報告的會員清單
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
        # 建立選項：顯示每位會員有哪些 index
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

        for category, pages in reports.items():
            if not isinstance(pages, list) or not pages:
                continue
            st.subheader(REPORT_CATEGORY_LABELS.get(category, category))
            cols = st.columns(min(len(pages), 2))
            for i, p in enumerate(pages):
                with cols[i % len(cols)]:
                    url = p.get("presigned_url", "")
                    filename = p.get("filename", f"page_{i}")
                    st.caption(filename)
                    if url:
                        st.image(url, use_container_width=True)
                    else:
                        st.warning("無 URL")
