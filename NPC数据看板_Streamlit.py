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
# 页面基础配置
# ----------------------
st.set_page_config(
    page_title="NPC数据看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------
# 深色玻璃态主题样式
# ----------------------
st.markdown("""
<style>
    .stApp { background-color: #081a38; }
    .main-title {
        font-size: 32px; font-weight: 800; color: #FFFFFF;
        margin-bottom: 5px; text-align: center;
    }
    .subtitle {
        color: #9fd8ff; font-size: 14px; text-align: center; margin-bottom: 20px;
    }
    .section-title {
        font-size: 22px; font-weight: bold; color: #FFFFFF;
        margin: 20px 0 10px 0; border-left: 4px solid #1e90ff; padding-left: 12px;
    }
    .css-1d391kg, .css-1wrcr25 { background-color: #0a1e3a !important; }
    .stSelectbox label, .stMultiSelect label, .stMarkdown, .stSidebar .st-ax { color: #FFFFFF !important; }
    hr { border-color: rgba(255,255,255,0.12); }
    /* 详细表样式 - 白色字体、居中对齐 */
    .stDataFrame {
        background-color: #081a38;
    }
    .stDataFrame table {
        width: 100%;
        border-collapse: collapse;
    }
    .stDataFrame th, .stDataFrame td {
        border: 1px solid rgba(255,255,255,0.2);
        padding: 8px 6px;
        vertical-align: middle;
        color: #FFFFFF !important;
    }
    /* 表头居中对齐 */
    .stDataFrame th {
        background: rgba(255,255,255,0.1);
        font-weight: bold;
        color: #9fd8ff !important;
        text-align: center !important;
    }
    /* 数据单元格居中对齐 */
    .stDataFrame td {
        text-align: center !important;
    }
    .stDataFrame tr:hover td {
        background: rgba(255,255,255,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ----------------------
# 1. 数据加载与预处理
# ----------------------
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_excel("W14-销售看板数据.xlsx", sheet_name="数据源")
        
        # 基础字段
        df["年份"] = df["年"].astype(str)
        df["周次"] = "W" + df["周"].astype(str).str.zfill(2)
        df["年度周次"] = df["年份"] + "-" + df["周次"]
        
        # 数值列
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
            df["系列名称"] = df["类目"]
        return df
    except Exception as e:
        st.error(f"数据加载失败：{str(e)}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ----------------------
    # 2. 侧边栏筛选器（增加店铺，删除销售状态）
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
    
    available_shops = sorted(df["店铺"].unique())
    selected_shops = st.sidebar.multiselect("店铺", available_shops, default=available_shops)
    
    available_categories = sorted(df["类目"].unique())
    selected_categories = st.sidebar.multiselect("类目", available_categories, default=available_categories)
    
    last_year = str(int(selected_year) - 1)
    
    # ----------------------
    # 3. 缓存数据过滤函数（全局，不含销售状态，含店铺）
    # ----------------------
    @st.cache_data(ttl=600)
    def get_filtered_data(year, week, markets, platforms, shops, categories):
        return df[
            (df["年份"] == year) &
            (df["周次"] == week) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["店铺"].isin(shops)) &
            (df["类目"].isin(categories))
        ].copy()
    
    @st.cache_data(ttl=600)
    def get_last_year_week_data(year, week, markets, platforms, shops, categories):
        return df[
            (df["年份"] == year) &
            (df["周次"] == week) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["店铺"].isin(shops)) &
            (df["类目"].isin(categories))
        ].copy()
    
    @st.cache_data(ttl=600)
    def get_last_6_weeks_data(year, week_labels, markets, platforms, shops, categories):
        return df[
            (df["年份"] == year) &
            (df["周次"].isin(week_labels)) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["店铺"].isin(shops)) &
            (df["类目"].isin(categories))
        ]
    
    @st.cache_data(ttl=600)
    def get_ytd_data(year, week, markets, platforms, shops, categories):
        return df[
            (df["年份"] == year) &
            (df["周次"] <= week) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["店铺"].isin(shops)) &
            (df["类目"].isin(categories))
        ]
    
    filtered_df = get_filtered_data(selected_year, selected_week, tuple(selected_markets), 
                                    tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    last_year_week_df = get_last_year_week_data(last_year, selected_week, tuple(selected_markets), 
                                                tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    
    current_week_num = int(selected_week.replace("W", ""))
    week_numbers = [current_week_num - i for i in range(6) if current_week_num - i >= 1]
    week_labels = ["W" + str(w).zfill(2) for w in week_numbers]
    
    last_6_weeks_df = get_last_6_weeks_data(selected_year, tuple(week_labels), tuple(selected_markets),
                                            tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    last_year_6_weeks_df = get_last_6_weeks_data(last_year, tuple(week_labels), tuple(selected_markets),
                                                tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    ytd_df = get_ytd_data(selected_year, selected_week, tuple(selected_markets),
                          tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    last_year_ytd_df = get_ytd_data(last_year, selected_week, tuple(selected_markets),
                                    tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    
    # ----------------------
    # 4. 计算各项聚合值（Week / 近6周 / YTD）及 YoY
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
            "毛利润": total_profit,
            "毛利率": gross_margin,
            "经营利润率": operating_margin,
            "净利率": net_margin,
            "退款补发率": refund_rate,
            "ACOAS": acoas
        }
    
    week_metrics = calc_metrics(filtered_df)
    last6_metrics = calc_metrics(last_6_weeks_df)
    ytd_metrics = calc_metrics(ytd_df)
    
    # 去年同周期指标
    last_year_week_metrics = calc_metrics(last_year_week_df)
    last_year_6_metrics = calc_metrics(last_year_6_weeks_df)
    last_year_ytd_metrics = calc_metrics(last_year_ytd_df)
    
    # 添加 YoY 到各指标字典
    def add_yoy(cur, last):
        result = cur.copy()
        for key in ["GMV", "毛利润", "毛利率", "经营利润率", "净利率", "退款补发率", "ACOAS"]:
            yoy_key = f"{key}_YoY"
            cur_val = cur[key]
            last_val = last[key]
            if last_val != 0:
                result[yoy_key] = ((cur_val - last_val) / last_val) * 100
            else:
                result[yoy_key] = 100 if cur_val > 0 else (-100 if cur_val < 0 else 0)
        return result
    
    week_metrics_with_yoy = add_yoy(week_metrics, last_year_week_metrics)
    last6_metrics_with_yoy = add_yoy(last6_metrics, last_year_6_metrics)
    ytd_metrics_with_yoy = add_yoy(ytd_metrics, last_year_ytd_metrics)
    
    # ----------------------
    # 5. 标题区域
    # ----------------------
    st.markdown('<div class="main-title">NPC数据统计看板</div>', unsafe_allow_html=True)
    st.divider()
    
    # ----------------------
    # 6. 核心指标概览（HTML表格，严格对齐）
    # ----------------------
    st.markdown('<div class="section-title">📊 核心指标概览</div>', unsafe_allow_html=True)
    
    def format_metric_value(value, yoy, is_currency=False):
        if is_currency:
            val_str = f"¥{value:,.0f}"
        else:
            val_str = f"{value:.1f}%"
        if yoy == 0:
            yoy_str = ""
        elif yoy > 0:
            yoy_str = f"(YoY {yoy:.1f}% ↑)"
        else:
            yoy_str = f"(YoY {yoy:.1f}% ↓)"
        return f"{val_str}<br>{yoy_str}" if yoy_str else val_str
    
    metric_keys = [
        ("GMV", "GMV", "GMV_YoY", True),
        ("毛利润", "毛利润", "毛利润_YoY", True),
        ("毛利率", "毛利率", "毛利率_YoY", False),
        ("经营利润率", "经营利润率", "经营利润率_YoY", False),
        ("净利率", "净利率", "净利率_YoY", False),
        ("退款补发率", "退款补发率", "退款补发率_YoY", False),
        ("ACOAS", "ACOAS", "ACOAS_YoY", False)
    ]
    
    time_metrics = [week_metrics_with_yoy, last6_metrics_with_yoy, ytd_metrics_with_yoy]
    time_labels = ["当周", "近六周", "YTD"]
    
    html_table = """
    <style>
        .core-table {
            width: 100%;
            border-collapse: collapse;
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 14px;
            backdrop-filter: blur(12px);
            margin-bottom: 20px;
        }
        .core-table th, .core-table td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.10);
            vertical-align: middle;
        }
        .core-table th {
            background: rgba(255, 255, 255, 0.05);
            font-size: 18px;
            font-weight: bold;
            color: #FFFFFF;
        }
        .core-table td {
            font-size: 18px;
            color: #FFFFFF;
        }
        .metric-label {
            font-weight: bold;
            color: #9fd8ff;
        }
        .metric-value {
            font-size: 22px;
            font-weight: bold;
            line-height: 1.4;
        }
    </style>
    <table class="core-table">
        <thead>
            <tr><th>指标名称</th><th>当周</th><th>近六周</th><th>YTD</th></tr>
        </thead>
        <tbody>
    """
    for label, val_key, yoy_key, is_currency in metric_keys:
        html_table += "<tr>"
        html_table += f'<td class="metric-label">{label}</td>'
        for metrics in time_metrics:
            value = metrics[val_key]
            yoy = metrics.get(yoy_key, 0)
            cell = format_metric_value(value, yoy, is_currency)
            html_table += f'<td class="metric-value">{cell}</td>'
        html_table += "</tr>"
    html_table += "</tbody></table>"
    st.markdown(html_table, unsafe_allow_html=True)
    st.divider()
    
    # ----------------------
    # 7. 图表配色：HTML蓝色调色板
    # ----------------------
    html_colors = ["#1e90ff", "#00bfff", "#87ceeb", "#4169e1", "#4682b4", 
                   "#5f9ea0", "#6495ed", "#6a5acd", "#7b68ee", "#8a2be2"]
    
    # 7.1 市场结构
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
    
    # 7.2 产品分析
    st.markdown('<div class="section-title">📦 产品分析</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # 销售状态柱状图（保留原样，不加YoY）
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
    
    # 7.3 广告深度分析（独立筛选：平台、店铺、年份、周次、销售市场，忽略类目）
    st.markdown('<div class="section-title">📢 广告效果深度分析</div>', unsafe_allow_html=True)
    
    @st.cache_data(ttl=600)
    def get_ad_trend_data(year, week, markets, platforms, shops):
        return df[
            (df["年份"] == year) &
            (df["周次"] == week) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["店铺"].isin(shops))
        ].groupby("年度周次").agg({
            "花费": "sum",
            "GMV": "sum",
            "广告单量": "sum",
            "曝光量": "sum",
            "点击量": "sum",
            "广告销售额": "sum"
        }).reset_index().sort_values("年度周次")
    
    all_weeks_in_year = sorted(df[df["年份"] == selected_year]["周次"].unique())
    ad_trend_df_list = []
    for w in all_weeks_in_year:
        temp = get_ad_trend_data(selected_year, w, tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops))
        ad_trend_df_list.append(temp)
    ad_trend_df = pd.concat(ad_trend_df_list, ignore_index=True) if ad_trend_df_list else pd.DataFrame()
    
    if not ad_trend_df.empty:
        ad_trend_df["ACOS"] = (ad_trend_df["花费"] / ad_trend_df["广告销售额"] * 100).fillna(0)
        ad_trend_df["ACOAS"] = (ad_trend_df["花费"] / ad_trend_df["GMV"] * 100).fillna(0)
        ad_trend_df["ASOAS"] = (ad_trend_df["广告销售额"] / ad_trend_df["GMV"] * 100).fillna(0)
        ad_trend_df["CPC"] = (ad_trend_df["花费"] / ad_trend_df["点击量"]).fillna(0)
        ad_trend_df["CTR"] = (ad_trend_df["点击量"] / ad_trend_df["曝光量"] * 100).fillna(0)
        ad_trend_df["CR"] = (ad_trend_df["广告单量"] / ad_trend_df["点击量"] * 100).fillna(0)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            fig_ad1 = go.Figure()
            fig_ad1.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["ACOS"], mode='lines+markers', name='ACOS',
                                         hovertemplate='%{y:.1f}%<extra></extra>'))
            fig_ad1.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["ACOAS"], mode='lines+markers', name='ACOAS',
                                         line=dict(dash='dash'), hovertemplate='%{y:.1f}%<extra></extra>'))
            fig_ad1.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["ASOAS"], mode='lines+markers', name='ASOAS',
                                         line=dict(dash='dot'), hovertemplate='%{y:.1f}%<extra></extra>'))
            fig_ad1.update_layout(title="ACOS / ACOAS / ASOAS", height=300, template="plotly_dark",
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_ad1, use_container_width=True)
        
        with col2:
            fig_ad2 = make_subplots(specs=[[{"secondary_y": True}]])
            fig_ad2.add_trace(go.Bar(x=ad_trend_df["年度周次"], y=ad_trend_df["曝光量"], name="曝光量", marker_color=html_colors[3]), secondary_y=False)
            fig_ad2.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["CPC"], mode='lines+markers', name="CPC",
                                         line=dict(color=html_colors[4]), hovertemplate='%{y:.2f} ¥<extra></extra>'), secondary_y=True)
            fig_ad2.update_layout(title="曝光量 & CPC", height=300, template="plotly_dark",
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            fig_ad2.update_xaxes(title_text="年度周次")
            fig_ad2.update_yaxes(title_text="曝光量", secondary_y=False)
            fig_ad2.update_yaxes(title_text="CPC (¥)", secondary_y=True)
            st.plotly_chart(fig_ad2, use_container_width=True)
        
        with col3:
            fig_ad3 = go.Figure()
            fig_ad3.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["CTR"], mode='lines+markers', name='CTR',
                                         hovertemplate='%{y:.2f}%<extra></extra>'))
            fig_ad3.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["CR"], mode='lines+markers', name='CR',
                                         hovertemplate='%{y:.2f}%<extra></extra>'))
            fig_ad3.update_layout(title="CTR & CR", height=300, template="plotly_dark",
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_ad3, use_container_width=True)
    
    # 7.4 利润与退补情况
    st.markdown('<div class="section-title">💰 利润与退补情况</div>', unsafe_allow_html=True)
    
    @st.cache_data(ttl=600)
    def get_profit_trend_data(year, markets, platforms, shops, categories):
        return df[
            (df["年份"] == year) &
            (df["销售市场"].isin(markets)) &
            (df["平台"].isin(platforms)) &
            (df["店铺"].isin(shops)) &
            (df["类目"].isin(categories))
        ].groupby("周次").agg({
            "毛利润": "sum",
            "GMV": "sum",
            "经营利润": "sum",
            "花费": "sum"
        }).reset_index().sort_values("周次")
    
    profit_trend_df = get_profit_trend_data(selected_year, tuple(selected_markets), tuple(selected_platforms),
                                            tuple(selected_shops), tuple(selected_categories))
    profit_trend_df["毛利率"] = (profit_trend_df["毛利润"] / profit_trend_df["GMV"] * 100).fillna(0)
    profit_trend_df["退款补发率"] = ((profit_trend_df["毛利润"] - profit_trend_df["经营利润"]) / profit_trend_df["GMV"] * 100).fillna(0)
    
    fig_profit = make_subplots(specs=[[{"secondary_y": True}]])
    fig_profit.add_trace(go.Bar(x=profit_trend_df["周次"], y=profit_trend_df["毛利润"], name="毛利润", marker_color=html_colors[0]), secondary_y=False)
    fig_profit.add_trace(go.Scatter(x=profit_trend_df["周次"], y=profit_trend_df["毛利率"], mode='lines+markers', name="毛利率",
                                   line=dict(color=html_colors[1]), hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
    fig_profit.add_trace(go.Scatter(x=profit_trend_df["周次"], y=profit_trend_df["退款补发率"], mode='lines+markers', name="退款补发率",
                                   line=dict(color=html_colors[2]), hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
    fig_profit.update_layout(title="毛利润及利润率趋势", height=400, template="plotly_dark",
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    fig_profit.update_xaxes(title_text="周次")
    fig_profit.update_yaxes(title_text="毛利润 (¥)", secondary_y=False)
    fig_profit.update_yaxes(title_text="百分比 (%)", secondary_y=True)
    st.plotly_chart(fig_profit, use_container_width=True)
    
    # 7.5 同比分析（全部指标，柱状图手动添加百分号）
    st.markdown('<div class="section-title">📈 同比分析（全部指标）</div>', unsafe_allow_html=True)
    
    # 指标配置：名称、聚合列、聚合方式、显示单位
    metric_list = [
        ("销售额", "GMV", "sum", "currency"),
        ("客单价", "客单价", "mean", "currency"),
        ("毛利润率", "毛利率", "mean", "percent"),
        ("CTR", "点击率", "mean", "percent"),
        ("CR", "转化率", "mean", "percent"),
        ("ASOAS", "ASOAS", "mean", "percent"),
        ("广告花费", "花费", "sum", "currency"),
        ("广告销售额", "广告销售额", "sum", "currency"),
        ("CPA", "CPA", "mean", "currency")
    ]
    
    @st.cache_data(ttl=600)
    def get_weekly_agg(year, agg_col, agg_func, markets, platforms, shops, categories):
        if agg_func == "sum":
            return df[
                (df["年份"] == year) &
                (df["销售市场"].isin(markets)) &
                (df["平台"].isin(platforms)) &
                (df["店铺"].isin(shops)) &
                (df["类目"].isin(categories))
            ].groupby("周次")[agg_col].sum().reset_index()
        else:
            return df[
                (df["年份"] == year) &
                (df["销售市场"].isin(markets)) &
                (df["平台"].isin(platforms)) &
                (df["店铺"].isin(shops)) &
                (df["类目"].isin(categories))
            ].groupby("周次")[agg_col].mean().reset_index()
    
    rows = [metric_list[i:i+2] for i in range(0, len(metric_list), 2)]
    for row in rows:
        cols = st.columns(2)
        for idx, col in enumerate(cols):
            if idx < len(row):
                metric_name, agg_col, agg_func, unit_type = row[idx]
                
                current_df = get_weekly_agg(selected_year, agg_col, agg_func, tuple(selected_markets),
                                            tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                last_df = get_weekly_agg(last_year, agg_col, agg_func, tuple(selected_markets),
                                         tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                
                yoy_df = pd.merge(current_df, last_df, on="周次", how="outer", suffixes=("_current", "_last")).fillna(0)
                yoy_df["yoy"] = ((yoy_df[f"{agg_col}_current"] - yoy_df[f"{agg_col}_last"]) / yoy_df[f"{agg_col}_last"].replace(0, 1)) * 100
                yoy_df["mom_current"] = yoy_df[f"{agg_col}_current"].pct_change() * 100
                yoy_df["mom_last"] = yoy_df[f"{agg_col}_last"].pct_change() * 100
                
                # 根据单位类型设置文本模板和Y轴标题
                if unit_type == "currency":
                    y_title = f"{metric_name} (¥)"
                    # 货币指标：手动构造带¥的文本
                    text_current = [f"¥{v:,.0f}" for v in yoy_df[f"{agg_col}_current"]]
                    text_last = [f"¥{v:,.0f}" for v in yoy_df[f"{agg_col}_last"]]
                    hovertemplate = "¥%{y:,.0f}<extra></extra>"
                else:
                    y_title = f"{metric_name} (%)"
                    # 百分比指标：手动构造带%的文本
                    text_current = [f"{v:.1f}%" for v in yoy_df[f"{agg_col}_current"]]
                    text_last = [f"{v:.1f}%" for v in yoy_df[f"{agg_col}_last"]]
                    hovertemplate = "%{y:.1f}%<extra></extra>"
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                # 去年在前
                fig.add_trace(go.Bar(x=yoy_df["周次"], y=yoy_df[f"{agg_col}_last"], name=f"{last_year}年", marker_color=html_colors[2],
                                     text=text_last, textposition="outside"), secondary_y=False)
                fig.add_trace(go.Bar(x=yoy_df["周次"], y=yoy_df[f"{agg_col}_current"], name=f"{selected_year}年", marker_color=html_colors[0],
                                     text=text_current, textposition="outside"), secondary_y=False)
                fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["yoy"], mode='markers', name="同比增长率",
                                         marker=dict(color='red', size=8, symbol='triangle-up'),
                                         texttemplate='%{y:.1f}%', textposition="top center",
                                         hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["mom_current"], mode='markers', name="今年环比",
                                         marker=dict(color='orange', size=6, symbol='circle'),
                                         texttemplate='%{y:.1f}%', textposition="top center",
                                         hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["mom_last"], mode='markers', name="去年环比",
                                         marker=dict(color='green', size=6, symbol='diamond'),
                                         texttemplate='%{y:.1f}%', textposition="top center",
                                         hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                
                fig.update_layout(title=metric_name, height=350, template="plotly_dark",
                                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                fig.update_xaxes(title_text="周次")
                fig.update_yaxes(title_text=y_title, secondary_y=False)
                fig.update_yaxes(title_text="变化率 (%)", secondary_y=True)
                
                with col:
                    st.plotly_chart(fig, use_container_width=True)
    
    # ----------------------
    # 8. 详细数据表（按系列，白色字体、居中对齐）
    # ----------------------
    st.divider()
    st.markdown('<div class="section-title">📋 详细数据报表（系列维度）</div>', unsafe_allow_html=True)
    
    # 获取所有系列（按当周GMV降序排序）
    series_gmv_order = filtered_df.groupby("系列名称")["GMV"].sum().sort_values(ascending=False)
    all_series_sorted = series_gmv_order.index.tolist()
    
    # 定义需要展示的指标
    detail_metric_keys = [
        ("GMV", "GMV", True),
        ("毛利润", "毛利润", True),
        ("毛利率", "毛利率", False),
        ("经营利润率", "经营利润率", False),
        ("净利率", "净利率", False),
        ("退款补发率", "退款补发率", False)
    ]
    
    # 辅助函数：获取某个系列在特定时间范围的聚合值（加权平均）
    def get_series_metrics_weighted(series_name, df_group, last_df_group):
        series_current = df_group[df_group["系列名称"] == series_name]
        series_last = last_df_group[last_df_group["系列名称"] == series_name]
        
        result = {}
        for label, col, is_currency in detail_metric_keys:
            if col in ["GMV", "毛利润"]:
                cur_val = series_current[col].sum()
                last_val = series_last[col].sum()
            else:
                cur_gmv = series_current["GMV"].sum()
                cur_profit = series_current["毛利润"].sum()
                cur_operating = series_current["经营利润"].sum()
                cur_cost = series_current["花费"].sum()
                last_gmv = series_last["GMV"].sum()
                last_profit = series_last["毛利润"].sum()
                last_operating = series_last["经营利润"].sum()
                last_cost = series_last["花费"].sum()
                
                if col == "毛利率":
                    cur_val = (cur_profit / cur_gmv * 100) if cur_gmv != 0 else 0
                    last_val = (last_profit / last_gmv * 100) if last_gmv != 0 else 0
                elif col == "经营利润率":
                    cur_val = (cur_operating / cur_gmv * 100) if cur_gmv != 0 else 0
                    last_val = (last_operating / last_gmv * 100) if last_gmv != 0 else 0
                elif col == "净利率":
                    cur_net = cur_operating - cur_cost
                    last_net = last_operating - last_cost
                    cur_val = (cur_net / cur_gmv * 100) if cur_gmv != 0 else 0
                    last_val = (last_net / last_gmv * 100) if last_gmv != 0 else 0
                elif col == "退款补发率":
                    cur_val = ((cur_profit - cur_operating) / cur_gmv * 100) if cur_gmv != 0 else 0
                    last_val = ((last_profit - last_operating) / last_gmv * 100) if last_gmv != 0 else 0
                else:
                    cur_val = 0
                    last_val = 0
            
            yoy = ((cur_val - last_val) / last_val * 100) if last_val != 0 else (100 if cur_val > 0 else (-100 if cur_val < 0 else 0))
            result[label] = (cur_val, yoy, is_currency)
        return result
    
    # 准备三个时间维度的数据框
    time_frames = [
        ("当周", filtered_df, last_year_week_df),
        ("近六周", last_6_weeks_df, last_year_6_weeks_df),
        ("YTD", ytd_df, last_year_ytd_df)
    ]
    
    # 构建数据字典：行索引=系列名称，列名扁平化
    data_dict = {}
    for series in all_series_sorted:
        row = {}
        for time_label, df_cur, df_last in time_frames:
            metrics = get_series_metrics_weighted(series, df_cur, df_last)
            for metric_label, (value, yoy, is_currency) in metrics.items():
                # 数值列：列名如 "当周_GMV"
                col_name = f"{time_label}_{metric_label}"
                row[col_name] = value
                # YoY 列：列名如 "当周_GMV_YoY"
                if yoy == 0:
                    yoy_str = ""
                elif yoy > 0:
                    yoy_str = f"({yoy:.1f}% ↑)"
                else:
                    yoy_str = f"({yoy:.1f}% ↓)"
                row[f"{col_name}_YoY"] = yoy_str
        data_dict[series] = row
    
    # 转换为 DataFrame
    detail_df = pd.DataFrame.from_dict(data_dict, orient='index')
    detail_df.index.name = "系列名称"
    
    # 默认按当周 GMV 降序排列
    default_sort_col = "当周_GMV"
    if default_sort_col in detail_df.columns:
        detail_df = detail_df.sort_values(by=default_sort_col, ascending=False)
    
    # 配置列格式化（为数值列设置货币/百分比格式）
    column_config = {}
    for col in detail_df.columns:
        if col.endswith("_YoY"):
            # YoY 列保持文本格式
            column_config[col] = st.column_config.TextColumn()
        else:
            # 判断是否为货币指标（包含 GMV 或 毛利润）
            if "GMV" in col or "毛利润" in col:
                column_config[col] = st.column_config.NumberColumn(
                    format="¥%.0f",
                    help="货币单位：元"
                )
            else:
                column_config[col] = st.column_config.NumberColumn(
                    format="%.1f%%",
                    help="百分比"
                )
    
    # 显示数据表（支持列排序，默认已排序）
    st.dataframe(
        detail_df,
        column_config=column_config,
        use_container_width=True,
        height=500
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
    st.error("❌ 数据加载失败，请确保 W14-销售看板数据.xlsx 文件存在且工作表名为“数据源”。")