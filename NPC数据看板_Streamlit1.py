"""
NPC数据看板
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# ----------------------
# 页面基础配置（修复：移除不兼容的theme参数）
# ----------------------
st.set_page_config(
    page_title="NPC数据看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------
# 深色玻璃态主题样式（强制深色+隐藏主题切换按钮，全版本兼容）
# ----------------------
st.markdown("""
<style>
    /* 强制全局深色背景 */
    .stApp { background-color: #081a38 !important; }
    .main-title {
        font-size: 32px; font-weight: 800; color: #FFFFFF;
        margin-bottom: 5px; text-align: center;
    }
    .subtitle {
        color: #9fd8ff; font-size: 14px; text-align: center; margin-bottom: 20px;
    }
    .section-title {
        font-size: 22px; font-weight: bold; color: #FFFFFF;
        margin: 20px 0 10px 0; border-left: 4px solid #e3f9fd; padding-left: 12px;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.07);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 14px;
        padding: 12px;
        text-align: center;
        backdrop-filter: blur(12px);
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: bold;
        color: #FFFFFF;
        margin: 5px 0;
    }
    .metric-label {
        font-size: 13px;
        color: #9fd8ff;
    }
    /* 强制侧边栏深色 */
    .css-1d391kg, .css-1wrcr25 { background-color: #0a1e3a !important; }
    /* 强制所有文字白色 */
    .stSelectbox label, .stMultiSelect label, .stMarkdown, .stSidebar .st-ax { color: #FFFFFF !important; }
    hr { border-color: rgba(255,255,255,0.12); }
    /* 核心：隐藏主题切换按钮，彻底禁止切换主题 */
    button[kind="header"] { display: none !important; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ----------------------
# 1. 数据加载与预处理
# ----------------------
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_excel("W12-销售看板数据.xlsx", sheet_name="数据源")
        
        # 基础字段
        df["年份"] = df["年"].astype(str)
        df["周次"] = "W" + df["周"].astype(str).str.zfill(2)
        df["年度周次"] = df["年份"] + "-" + df["周次"]
        
        # 数值列（按数据源实际列名）
        numeric_cols = ["GMV", "销量", "毛利润", "经营利润", "花费", 
                       "曝光量", "点击量", "单量", "广告单量", "广告销售额"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        # 派生指标
        df["客单价"] = df["GMV"] / df["销量"].replace(0, 1)
        df["毛利率"] = (df["毛利润"] / df["GMV"]).replace([np.inf, -np.inf], 0) * 100
        df["经营利润率"] = (df["经营利润"] / df["GMV"]).replace([np.inf, -np.inf], 0) * 100
        df["净利润"] = df["经营利润"] - df["花费"]
        df["净利率"] = (df["净利润"] / df["GMV"]).replace([np.inf, -np.inf], 0) * 100
        df["退款补发率"] = ((df["毛利润"] - df["经营利润"]) / df["GMV"]).replace([np.inf, -np.inf], 0) * 100
        df["ACOAS"] = (df["花费"] / df["GMV"]).replace([np.inf, -np.inf], 0) * 100
        df["ACOS"] = (df["花费"] / df["广告销售额"]).replace([np.inf, -np.inf], 0) * 100
        df["ASOAS"] = (df["广告销售额"] / df["GMV"]).replace([np.inf, -np.inf], 0) * 100
        df["CPA"] = (df["花费"] / df["广告单量"]).replace([np.inf, -np.inf], 0)
        df["点击率"] = (df["点击量"] / df["曝光量"]).replace([np.inf, -np.inf], 0) * 100
        df["转化率"] = (df["广告单量"] / df["点击量"]).replace([np.inf, -np.inf], 0) * 100
        
        # 确保系列名称列存在
        if "系列名称" not in df.columns:
            df["系列名称"] = df["类目"]  # 降级使用类目
        return df
    except Exception as e:
        st.error(f"数据加载失败：{str(e)}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ----------------------
    # 2. 侧边栏筛选器
    # ----------------------
    st.sidebar.header("🔍 筛选条件")
    
    available_years = sorted(df["年份"].unique(), reverse=True)
    selected_year = st.sidebar.selectbox("选择年份", available_years, index=0)
    
    weeks_of_year = sorted(df[df["年份"] == selected_year]["周次"].unique())
    default_week_index = len(weeks_of_year) - 1
    selected_week = st.sidebar.selectbox("选择周次", weeks_of_year, index=default_week_index)
    
    available_markets = sorted(df["销售市场"].unique())
    selected_markets = st.sidebar.multiselect("销售市场", available_markets, default=available_markets)
    
    available_platforms = sorted(df["平台"].unique())
    selected_platforms = st.sidebar.multiselect("平台", available_platforms, default=available_platforms)
    
    available_categories = sorted(df["类目"].unique())
    selected_categories = st.sidebar.multiselect("类目", available_categories, default=available_categories)
    
    available_status = sorted(df["销售状态"].unique())
    selected_status = st.sidebar.multiselect("销售状态", available_status, default=available_status)
    
    last_year = str(int(selected_year) - 1)
    
    # ----------------------
    # 3. 缓存数据过滤函数
    # ----------------------
    @st.cache_data(ttl=600)
    def get_filtered_data(year, week, markets, platforms, categories, status):
        return df[
            (df["年份"] == year) &
            (df["周次"] == week) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["类目"].isin(categories)) &
            (df["销售状态"].isin(status))
        ].copy()
    
    @st.cache_data(ttl=600)
    def get_last_year_week_data(year, week, markets, platforms, categories, status):
        return df[
            (df["年份"] == year) &
            (df["周次"] == week) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["类目"].isin(categories)) &
            (df["销售状态"].isin(status))
        ].copy()
    
    @st.cache_data(ttl=600)
    def get_last_6_weeks_data(year, week_labels, markets, platforms, categories, status):
        return df[
            (df["年份"] == year) &
            (df["周次"].isin(week_labels)) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["类目"].isin(categories)) &
            (df["销售状态"].isin(status))
        ]
    
    @st.cache_data(ttl=600)
    def get_ytd_data(year, week, markets, platforms, categories, status):
        return df[
            (df["年份"] == year) &
            (df["周次"] <= week) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["类目"].isin(categories)) &
            (df["销售状态"].isin(status))
        ]
    
    filtered_df = get_filtered_data(selected_year, selected_week, tuple(selected_markets), 
                                    tuple(selected_platforms), tuple(selected_categories), tuple(selected_status))
    last_year_week_df = get_last_year_week_data(last_year, selected_week, tuple(selected_markets), 
                                                tuple(selected_platforms), tuple(selected_categories), tuple(selected_status))
    
    current_week_num = int(selected_week.replace("W", ""))
    week_numbers = [current_week_num - i for i in range(6) if current_week_num - i >= 1]
    week_labels = ["W" + str(w).zfill(2) for w in week_numbers]
    
    last_6_weeks_df = get_last_6_weeks_data(selected_year, tuple(week_labels), tuple(selected_markets),
                                            tuple(selected_platforms), tuple(selected_categories), tuple(selected_status))
    last_year_6_weeks_df = get_last_6_weeks_data(last_year, tuple(week_labels), tuple(selected_markets),
                                                tuple(selected_platforms), tuple(selected_categories), tuple(selected_status))
    ytd_df = get_ytd_data(selected_year, selected_week, tuple(selected_markets),
                          tuple(selected_platforms), tuple(selected_categories), tuple(selected_status))
    last_year_ytd_df = get_ytd_data(last_year, selected_week, tuple(selected_markets),
                                    tuple(selected_platforms), tuple(selected_categories), tuple(selected_status))
    
    # ----------------------
    # 4. 计算各项聚合值（Week / 近6周 / YTD）
    # ----------------------
    def calc_metrics(df_group):
        total_sales = df_group["GMV"].sum()
        total_quantity = df_group["销量"].sum()
        total_profit = df_group["毛利润"].sum()
        total_operating_profit = df_group["经营利润"].sum()
        total_cost = df_group["花费"].sum()
        total_net_profit = (df_group["经营利润"] - df_group["花费"]).sum()
        
        gross_margin = total_profit / total_sales * 100 if total_sales > 0 else 0
        operating_margin = total_operating_profit / total_sales * 100 if total_sales > 0 else 0
        net_margin = total_net_profit / total_sales * 100 if total_sales > 0 else 0
        refund_rate = (total_profit - total_operating_profit) / total_sales * 100 if total_sales > 0 else 0
        acoas = total_cost / total_sales * 100 if total_sales > 0 else 0
        
        return {
            "GMV": total_sales,
            "GMV_YoY": None,
            "毛利润": total_profit,
            "毛利润_YoY": None,
            "毛利率": gross_margin,
            "毛利率_YoY": None,
            "经营利润率": operating_margin,
            "净利率": net_margin,
            "退款补发率": refund_rate,
            "ACOAS": acoas
        }
    
    # 本周
    week_metrics = calc_metrics(filtered_df)
    # 近6周
    last6_metrics = calc_metrics(last_6_weeks_df)
    # YTD
    ytd_metrics = calc_metrics(ytd_df)
    
    # 同比数据
    last_year_week_metrics = calc_metrics(last_year_week_df)
    last_year_6_metrics = calc_metrics(last_year_6_weeks_df)
    last_year_ytd_metrics = calc_metrics(last_year_ytd_df)
    
    # 计算YoY
    week_metrics["GMV_YoY"] = ((week_metrics["GMV"] - last_year_week_metrics["GMV"]) / last_year_week_metrics["GMV"] * 100) if last_year_week_metrics["GMV"] > 0 else 0
    last6_metrics["GMV_YoY"] = ((last6_metrics["GMV"] - last_year_6_metrics["GMV"]) / last_year_6_metrics["GMV"] * 100) if last_year_6_metrics["GMV"] > 0 else 0
    ytd_metrics["GMV_YoY"] = ((ytd_metrics["GMV"] - last_year_ytd_metrics["GMV"]) / last_year_ytd_metrics["GMV"] * 100) if last_year_ytd_metrics["GMV"] > 0 else 0
    
    week_metrics["毛利润_YoY"] = ((week_metrics["毛利润"] - last_year_week_metrics["毛利润"]) / last_year_week_metrics["毛利润"] * 100) if last_year_week_metrics["毛利润"] > 0 else 0
    last6_metrics["毛利润_YoY"] = ((last6_metrics["毛利润"] - last_year_6_metrics["毛利润"]) / last_year_6_metrics["毛利润"] * 100) if last_year_6_metrics["毛利润"] > 0 else 0
    ytd_metrics["毛利润_YoY"] = ((ytd_metrics["毛利润"] - last_year_ytd_metrics["毛利润"]) / last_year_ytd_metrics["毛利润"] * 100) if last_year_ytd_metrics["毛利润"] > 0 else 0
    
    week_metrics["毛利率_YoY"] = ((week_metrics["毛利率"] - last_year_week_metrics["毛利率"]) / last_year_week_metrics["毛利率"] * 100) if last_year_week_metrics["毛利率"] > 0 else 0
    last6_metrics["毛利率_YoY"] = ((last6_metrics["毛利率"] - last_year_6_metrics["毛利率"]) / last_year_6_metrics["毛利率"] * 100) if last_year_6_metrics["毛利率"] > 0 else 0
    ytd_metrics["毛利率_YoY"] = ((ytd_metrics["毛利率"] - last_year_ytd_metrics["毛利率"]) / last_year_ytd_metrics["毛利率"] * 100) if last_year_ytd_metrics["毛利率"] > 0 else 0
    
    # ----------------------
    # 5. 标题区域
    # ----------------------
    st.markdown('<div class="main-title">NPC数据统计看板</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">{selected_year}年{selected_week} · 数据更新时间：{current_time}</div>', unsafe_allow_html=True)
    st.divider()
    
    # ----------------------
    # 6. 核心指标概览（4列排版+样式优化）
    # ----------------------
    st.markdown('<div class="section-title">📊 核心指标概览</div>', unsafe_allow_html=True)

    # 定义四个列：指标名称 | 当周 | 近六周 | YTD
    col_label, col_week, col_last6, col_ytd = st.columns(4)

    # 指标顺序列表
    metric_names = [
        "GMV", "GMV YoY", "毛利润", "毛利润 YoY", "毛利率", "毛利率 YoY",
        "经营利润率", "净利率", "退款补发率", "ACOAS"
    ]

    # 数据格式化
    week_data = {
        "GMV": f"¥{week_metrics['GMV']:,.0f}",
        "GMV YoY": f"{week_metrics['GMV_YoY']:.1f}%",
        "毛利润": f"¥{week_metrics['毛利润']:,.0f}",
        "毛利润 YoY": f"{week_metrics['毛利润_YoY']:.1f}%",
        "毛利率": f"{week_metrics['毛利率']:.1f}%",
        "毛利率 YoY": f"{week_metrics['毛利率_YoY']:.1f}%",
        "经营利润率": f"{week_metrics['经营利润率']:.1f}%",
        "净利率": f"{week_metrics['净利率']:.1f}%",
        "退款补发率": f"{week_metrics['退款补发率']:.1f}%",
        "ACOAS": f"{week_metrics['ACOAS']:.1f}%"
    }

    last6_data = {
        "GMV": f"¥{last6_metrics['GMV']:,.0f}",
        "GMV YoY": f"{last6_metrics['GMV_YoY']:.1f}%",
        "毛利润": f"¥{last6_metrics['毛利润']:,.0f}",
        "毛利润 YoY": f"{last6_metrics['毛利润_YoY']:.1f}%",
        "毛利率": f"{last6_metrics['毛利率']:.1f}%",
        "毛利率 YoY": f"{last6_metrics['毛利率_YoY']:.1f}%",
        "经营利润率": f"{last6_metrics['经营利润率']:.1f}%",
        "净利率": f"{last6_metrics['净利率']:.1f}%",
        "退款补发率": f"{last6_metrics['退款补发率']:.1f}%",
        "ACOAS": f"{last6_metrics['ACOAS']:.1f}%"
    }

    ytd_data = {
        "GMV": f"¥{ytd_metrics['GMV']:,.0f}",
        "GMV YoY": f"{ytd_metrics['GMV_YoY']:.1f}%",
        "毛利润": f"¥{ytd_metrics['毛利润']:,.0f}",
        "毛利润 YoY": f"{ytd_metrics['毛利润_YoY']:.1f}%",
        "毛利率": f"{ytd_metrics['毛利率']:.1f}%",
        "毛利率 YoY": f"{ytd_metrics['毛利率_YoY']:.1f}%",
        "经营利润率": f"{ytd_metrics['经营利润率']:.1f}%",
        "净利率": f"{ytd_metrics['净利率']:.1f}%",
        "退款补发率": f"{ytd_metrics['退款补发率']:.1f}%",
        "ACOAS": f"{ytd_metrics['ACOAS']:.1f}%"
    }

    # 第一列：指标名称
    with col_label:
        st.markdown('<div class="metric-card" style="background: rgba(255,255,255,0.12); font-weight: bold;"><div style="color:#FFFFFF; font-size:20px;">指标名称</div></div>', unsafe_allow_html=True)
        for metric in metric_names:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color:#FFFFFF; font-size:18px;">{metric}</div>
            </div>
            """, unsafe_allow_html=True)

    # 第二列：当周数据
    with col_week:
        st.markdown('<div class="metric-card" style="background: rgba(255,255,255,0.12); font-weight: bold;"><div style="color:#FFFFFF; font-size:20px;">当周</div></div>', unsafe_allow_html=True)
        for metric in metric_names:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color:#e3f9fd; font-size:18px;">{week_data[metric]}</div>
            </div>
            """, unsafe_allow_html=True)

    # 第三列：近六周数据
    with col_last6:
        st.markdown('<div class="metric-card" style="background: rgba(255,255,255,0.12); font-weight: bold;"><div style="color:#FFFFFF; font-size:20px;">近六周</div></div>', unsafe_allow_html=True)
        for metric in metric_names:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color:#e3f9fd; font-size:18px;">{last6_data[metric]}</div>
            </div>
            """, unsafe_allow_html=True)

    # 第四列：YTD数据
    with col_ytd:
        st.markdown('<div class="metric-card" style="background: rgba(255,255,255,0.12); font-weight: bold;"><div style="color:#FFFFFF; font-size:20px;">YTD</div></div>', unsafe_allow_html=True)
        for metric in metric_names:
            st.markdown(f"""
            <div class="metric-card">
                <div style="color:#e3f9fd; font-size:18px;">{ytd_data[metric]}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    
    # ----------------------
    # 7. 图表配色：HTML蓝色调色板
    # ----------------------
    html_colors = ["#1e90ff", "#00bfff", "#87ceeb", "#4169e1", "#4682b4", 
                   "#5f9ea0", "#6495ed", "#6a5acd", "#7b68ee", "#8a2be2"]
    
    # 7.1 国家占比 + 平台占比
    st.markdown('<div class="section-title">🌍 市场结构</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        market_sales = filtered_df.groupby("销售市场")["GMV"].sum().reset_index()
        fig_country = px.pie(market_sales, values="GMV", names="销售市场", 
                             title=f"{selected_year}年{selected_week} 国家市场份额",
                             hole=0.4, color_discrete_sequence=html_colors,
                             template="plotly_dark")
        fig_country.update_traces(textposition="inside", textinfo="percent+label", textfont_color="white")
        fig_country.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_country, use_container_width=True)
    
    with col2:
        platform_sales = filtered_df.groupby("平台")["GMV"].sum().reset_index()
        platform_sales = platform_sales[platform_sales["GMV"] > 0]
        fig_platform = px.pie(platform_sales, values="GMV", names="平台",
                              title=f"{selected_year}年{selected_week} 平台销售额占比",
                              hole=0.4, color_discrete_sequence=html_colors,
                              template="plotly_dark")
        fig_platform.update_traces(textposition="inside", textinfo="percent+label", textfont_color="white")
        fig_platform.update_layout(height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_platform, use_container_width=True)
    
    # 7.2 产品状态 + 系列TOP10
    st.markdown('<div class="section-title">📦 产品分析</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        status_sales = filtered_df.groupby("销售状态")["GMV"].sum().reset_index()
        status_sales = status_sales.sort_values("GMV", ascending=True)
        fig_status = px.bar(status_sales, x="GMV", y="销售状态", orientation='h',
                            title="各销售状态销售额",
                            labels={"GMV": "销售额 (¥)", "销售状态": ""},
                            color="销售状态", color_discrete_sequence=html_colors,
                            template="plotly_dark")
        fig_status.update_layout(height=400, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig_status.update_traces(texttemplate="¥%{x:,.0f}", textposition="outside", textfont_color="white")
        st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        series_sales = filtered_df.groupby("系列名称")["GMV"].sum().reset_index()
        series_sales = series_sales.sort_values("GMV", ascending=False).head(10)
        series_sales = series_sales.sort_values("GMV", ascending=True)
        fig_series = px.bar(series_sales, x="GMV", y="系列名称", orientation='h',
                            title="系列销售额 TOP10",
                            labels={"GMV": "销售额 (¥)", "系列名称": ""},
                            color="系列名称", color_discrete_sequence=html_colors,
                            template="plotly_dark")
        fig_series.update_layout(height=400, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig_series.update_traces(texttemplate="¥%{x:,.0f}", textposition="outside", textfont_color="white")
        st.plotly_chart(fig_series, use_container_width=True)
    
    # 7.3 广告深度分析
    st.markdown('<div class="section-title">📢 广告效果深度分析</div>', unsafe_allow_html=True)
    
    @st.cache_data(ttl=600)
    def get_ad_trend_data(year, markets, platforms, categories, status):
        return df[
            (df["年份"] == year) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["类目"].isin(categories)) &
            (df["销售状态"].isin(status))
        ].groupby("周次").agg({
            "花费": "sum",
            "GMV": "sum",
            "广告单量": "sum",
            "曝光量": "sum",
            "点击量": "sum",
            "广告销售额": "sum"
        }).reset_index().sort_values("周次")
    
    ad_trend_df = get_ad_trend_data(selected_year, tuple(selected_markets), tuple(selected_platforms),
                                     tuple(selected_categories), tuple(selected_status))
    
    ad_trend_df["ACOS"] = (ad_trend_df["花费"] / ad_trend_df["广告销售额"] * 100).fillna(0)
    ad_trend_df["ACOAS"] = (ad_trend_df["花费"] / ad_trend_df["GMV"] * 100).fillna(0)
    ad_trend_df["ASOAS"] = (ad_trend_df["广告销售额"] / ad_trend_df["GMV"] * 100).fillna(0)
    ad_trend_df["CPC"] = (ad_trend_df["花费"] / ad_trend_df["点击量"]).fillna(0)
    ad_trend_df["CTR"] = (ad_trend_df["点击量"] / ad_trend_df["曝光量"] * 100).fillna(0)
    ad_trend_df["CR"] = (ad_trend_df["广告单量"] / ad_trend_df["点击量"] * 100).fillna(0)
    ad_trend_df["CPA"] = (ad_trend_df["花费"] / ad_trend_df["广告单量"]).fillna(0)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig_ad1 = go.Figure()
        fig_ad1.add_trace(go.Scatter(x=ad_trend_df["周次"], y=ad_trend_df["ACOS"], mode='lines+markers', name='ACOS', line=dict(color=html_colors[0])))
        fig_ad1.add_trace(go.Scatter(x=ad_trend_df["周次"], y=ad_trend_df["ACOAS"], mode='lines+markers', name='ACOAS', line=dict(color=html_colors[1], dash='dash')))
        fig_ad1.add_trace(go.Scatter(x=ad_trend_df["周次"], y=ad_trend_df["ASOAS"], mode='lines+markers', name='ASOAS', line=dict(color=html_colors[2], dash='dot')))
        fig_ad1.update_layout(title="ACOS / ACOAS / ASOAS", height=300, template="plotly_dark", 
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_ad1, use_container_width=True)
    
    with col2:
        fig_ad2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ad2.add_trace(go.Bar(x=ad_trend_df["周次"], y=ad_trend_df["曝光量"], name="曝光量", marker_color=html_colors[3]), secondary_y=False)
        fig_ad2.add_trace(go.Scatter(x=ad_trend_df["周次"], y=ad_trend_df["CPC"], mode='lines+markers', name="CPC", line=dict(color=html_colors[4])), secondary_y=True)
        fig_ad2.update_layout(title="曝光量 & CPC", height=300, template="plotly_dark", 
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig_ad2.update_xaxes(title_text="周次")
        fig_ad2.update_yaxes(title_text="曝光量", secondary_y=False)
        fig_ad2.update_yaxes(title_text="CPC (¥)", secondary_y=True)
        st.plotly_chart(fig_ad2, use_container_width=True)
    
    with col3:
        fig_ad3 = go.Figure()
        fig_ad3.add_trace(go.Scatter(x=ad_trend_df["周次"], y=ad_trend_df["CTR"], mode='lines+markers', name='CTR', line=dict(color=html_colors[5])))
        fig_ad3.add_trace(go.Scatter(x=ad_trend_df["周次"], y=ad_trend_df["CR"], mode='lines+markers', name='CR', line=dict(color=html_colors[6])))
        fig_ad3.update_layout(title="CTR & CR", height=300, template="plotly_dark",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_ad3, use_container_width=True)
    
    # 7.4 利润多Y轴趋势
    st.markdown('<div class="section-title">💰 利润与效率趋势</div>', unsafe_allow_html=True)
    
    @st.cache_data(ttl=600)
    def get_profit_trend_data(year, markets, platforms, categories, status):
        return df[
            (df["年份"] == year) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["类目"].isin(categories)) &
            (df["销售状态"].isin(status))
        ].groupby("周次").agg({
            "毛利润": "sum",
            "GMV": "sum",
            "经营利润": "sum"
        }).reset_index().sort_values("周次")
    
    profit_trend_df = get_profit_trend_data(selected_year, tuple(selected_markets), tuple(selected_platforms),
                                            tuple(selected_categories), tuple(selected_status))
    
    profit_trend_df["毛利率"] = (profit_trend_df["毛利润"] / profit_trend_df["GMV"] * 100).fillna(0)
    profit_trend_df["经营利润率"] = (profit_trend_df["经营利润"] / profit_trend_df["GMV"] * 100).fillna(0)
    
    fig_profit = make_subplots(specs=[[{"secondary_y": True}]])
    fig_profit.add_trace(go.Bar(x=profit_trend_df["周次"], y=profit_trend_df["毛利润"], name="毛利润", marker_color=html_colors[0]), secondary_y=False)
    fig_profit.add_trace(go.Scatter(x=profit_trend_df["周次"], y=profit_trend_df["毛利率"], mode='lines+markers', name="毛利率", line=dict(color=html_colors[1])), secondary_y=True)
    fig_profit.add_trace(go.Scatter(x=profit_trend_df["周次"], y=profit_trend_df["经营利润率"], mode='lines+markers', name="经营利润率", line=dict(color=html_colors[2])), secondary_y=True)
    fig_profit.update_layout(title="毛利润及利润率趋势", height=400, template="plotly_dark",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig_profit.update_xaxes(title_text="周次")
    fig_profit.update_yaxes(title_text="毛利润 (¥)", secondary_y=False)
    fig_profit.update_yaxes(title_text="百分比 (%)", secondary_y=True)
    st.plotly_chart(fig_profit, use_container_width=True)
    
    # 7.5 同比分析（全部9个指标）
    st.markdown('<div class="section-title">📈 同比分析（全部指标）</div>', unsafe_allow_html=True)
    
    metric_list = [
        ("销售额", "GMV", "sum"),
        ("客单价", "客单价", "mean"),
        ("毛利润率", "毛利率", "mean"),
        ("CTR", "点击率", "mean"),
        ("CR", "转化率", "mean"),
        ("ASOAS", "ASOAS", "mean"),
        ("广告花费", "花费", "sum"),
        ("广告销售额", "广告销售额", "sum"),
        ("CPA", "CPA", "mean")
    ]
    
    @st.cache_data(ttl=600)
    def get_weekly_agg(year, agg_col, agg_func, markets, platforms, categories, status):
        if agg_func == "sum":
            return df[
                (df["年份"] == year) &
                (df["销售市场"].isin(markets)) &
                (df["平台"].isin(platforms)) &
                (df["类目"].isin(categories)) &
                (df["销售状态"].isin(status))
            ].groupby("周次")[agg_col].sum().reset_index()
        else:
            return df[
                (df["年份"] == year) &
                (df["销售市场"].isin(markets)) &
                (df["平台"].isin(platforms)) &
                (df["类目"].isin(categories)) &
                (df["销售状态"].isin(status))
            ].groupby("周次")[agg_col].mean().reset_index()
    
    rows = [metric_list[i:i+2] for i in range(0, len(metric_list), 2)]
    for row in rows:
        cols = st.columns(2)
        for idx, col in enumerate(cols):
            if idx < len(row):
                metric_name, agg_col, agg_func = row[idx]
                
                current_df = get_weekly_agg(selected_year, agg_col, agg_func, tuple(selected_markets),
                                            tuple(selected_platforms), tuple(selected_categories), tuple(selected_status))
                last_df = get_weekly_agg(last_year, agg_col, agg_func, tuple(selected_markets),
                                         tuple(selected_platforms), tuple(selected_categories), tuple(selected_status))
                
                yoy_df = pd.merge(current_df, last_df, on="周次", how="outer", suffixes=("_current", "_last")).fillna(0)
                yoy_df["yoy"] = ((yoy_df[f"{agg_col}_current"] - yoy_df[f"{agg_col}_last"]) / yoy_df[f"{agg_col}_last"].replace(0, 1)) * 100
                yoy_df["mom_current"] = yoy_df[f"{agg_col}_current"].pct_change() * 100
                yoy_df["mom_last"] = yoy_df[f"{agg_col}_last"].pct_change() * 100
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(go.Bar(x=yoy_df["周次"], y=yoy_df[f"{agg_col}_current"], name=f"{selected_year}年", marker_color=html_colors[0]), secondary_y=False)
                fig.add_trace(go.Bar(x=yoy_df["周次"], y=yoy_df[f"{agg_col}_last"], name=f"{last_year}年", marker_color=html_colors[2]), secondary_y=False)
                fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["yoy"], mode='markers', name="同比增长率",
                                         marker=dict(color='red', size=8, symbol='triangle-up')), secondary_y=True)
                fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["mom_current"], mode='markers', name="今年环比",
                                         marker=dict(color='orange', size=6, symbol='circle')), secondary_y=True)
                fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["mom_last"], mode='markers', name="去年环比",
                                         marker=dict(color='green', size=6, symbol='diamond')), secondary_y=True)
                
                fig.update_layout(title=metric_name, height=350, template="plotly_dark",
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                fig.update_xaxes(title_text="周次")
                fig.update_yaxes(title_text=metric_name, secondary_y=False)
                fig.update_yaxes(title_text="变化率 (%)", secondary_y=True)
                
                with col:
                    st.plotly_chart(fig, use_container_width=True)
    
    # ----------------------
    # 8. 数据明细表
    # ----------------------
    st.divider()
    st.markdown('<div class="section-title">📋 详细数据报表</div>', unsafe_allow_html=True)
    
    summary_table = filtered_df.groupby(["销售市场", "平台", "类目", "销售状态"]).agg({
        "GMV": ["sum", "mean"],
        "销量": "sum",
        "毛利润": "sum",
        "经营利润": "sum",
        "花费": "sum",
        "客单价": "mean",
        "毛利率": "mean",
        "ACOAS": "mean"
    }).round(2)
    
    summary_table.columns = [
        "总销售额", "平均销售额", "总销量", "总毛利润", "总经营利润", 
        "总花费", "平均客单价", "平均毛利率(%)", "平均ACOAS(%)"
    ]
    summary_table = summary_table.reset_index()
    
    format_dict = {
        "总销售额": "{:,.2f}",
        "平均销售额": "{:,.2f}",
        "总销量": "{:,.0f}",
        "总毛利润": "{:,.2f}",
        "总经营利润": "{:,.2f}",
        "总花费": "{:,.2f}",
        "平均客单价": "{:,.2f}",
        "平均毛利率(%)": "{:.2f}",
        "平均ACOAS(%)": "{:.2f}"
    }
    
    st.dataframe(
        summary_table.style.format(format_dict),
        use_container_width=True,
        height=400
    )
    
    # ----------------------
    # 9. 底部
    # ----------------------
    st.markdown("""
    <div style="text-align: center; margin-top: 50px; color: #9fd8ff; font-size: 12px;">
        © 2025 NPC数据看板
    </div>
    """, unsafe_allow_html=True)

else:
    st.error("❌ 数据加载失败，请确保 W12-销售看板数据.xlsx 文件存在且工作表名为“数据源”。")