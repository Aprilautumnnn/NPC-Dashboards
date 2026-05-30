"""
NPC数据看板 
"""
import streamlit as st
import pandas as pd
from pandas.api.types import CategoricalDtype
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import glob

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
        # 查找所有符合模式的数据文件
        data_files = sorted(glob.glob("NPC销售看板数据*.xlsx"))
        
        if not data_files:
            st.error("未找到任何数据文件，请确保存在 NPC销售看板数据*.xlsx 文件")
            return pd.DataFrame()
        
        all_data = []
        
        for file_path in data_files:
            try:
                df_year = pd.read_excel(file_path, sheet_name="数据源")
                
                # 基础字段
                df_year["年份"] = df_year["年"].astype(str)
                df_year["周次"] = "W" + df_year["周"].astype(str).str.zfill(2)
                df_year["年度周次"] = df_year["年份"] + "-" + df_year["周次"]
                
                # 数值列
                numeric_cols = ["GMV", "销量", "毛利润", "经营利润", "花费", 
                               "曝光量", "点击量", "单量", "广告单量", "广告销售额"]
                for col in numeric_cols:
                    if col in df_year.columns:
                        df_year[col] = pd.to_numeric(df_year[col], errors="coerce").fillna(0)
                
                # 派生指标
                df_year["客单价"] = df_year["GMV"] / df_year["销量"].replace(0, 1)
                df_year["毛利率"] = (df_year["毛利润"] / df_year["GMV"]).replace([np.inf, -np.inf], 0) * 100
                df_year["经营利润率"] = (df_year["经营利润"] / df_year["GMV"]).replace([np.inf, -np.inf], 0) * 100
                df_year["净利润"] = df_year["经营利润"] - df_year["花费"]
                df_year["净利率"] = (df_year["净利润"] / df_year["GMV"]).replace([np.inf, -np.inf], 0) * 100
                df_year["退款补发率"] = ((df_year["毛利润"] - df_year["经营利润"]) / df_year["GMV"]).replace([np.inf, -np.inf], 0) * 100
                df_year["ACOAS"] = (df_year["花费"] / df_year["GMV"]).replace([np.inf, -np.inf], 0) * 100
                df_year["ACOS"] = (df_year["花费"] / df_year["广告销售额"]).replace([np.inf, -np.inf], 0) * 100
                df_year["ASOAS"] = (df_year["广告销售额"] / df_year["GMV"]).replace([np.inf, -np.inf], 0) * 100
                df_year["CPA"] = (df_year["花费"] / df_year["广告单量"]).replace([np.inf, -np.inf], 0)
                df_year["点击率"] = (df_year["点击量"] / df_year["曝光量"]).replace([np.inf, -np.inf], 0) * 100
                df_year["转化率"] = (df_year["广告单量"] / df_year["点击量"]).replace([np.inf, -np.inf], 0) * 100
                
                # 确保系列名称列存在
                if "系列名称" not in df_year.columns:
                    df_year["系列名称"] = df_year["类目"]
                
                all_data.append(df_year)
            except Exception as e:
                st.warning(f"加载文件 {file_path} 时出错：{str(e)}")
        
        # 合并所有数据
        if not all_data:
            st.error("所有数据文件加载失败")
            return pd.DataFrame()
        
        df = pd.concat(all_data, ignore_index=True)
        return df
    except Exception as e:
        st.error(f"数据加载失败：{str(e)}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ----------------------
    # 2. 侧边栏筛选器（排除2024年，仅用于同比计算）
    # ----------------------
    st.sidebar.header("🔍 筛选条件")
    
    # 修正：排除 "2024" 年，仅用于计算
    available_years = sorted([y for y in df["年份"].unique() if y != "2024"], reverse=True)
    if not available_years:  # 若没有非2024年份，则回退显示所有年份（避免空选项）
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
    # 检查去年数据是否存在，用于后续容错
    has_last_year_data = (df["年份"] == last_year).any()
    
    # ----------------------
    # 3. 缓存数据过滤函数
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
        if not has_last_year_data:
            return pd.DataFrame()
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
        if not has_last_year_data:
            return pd.DataFrame()
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
        if not has_last_year_data:
            return pd.DataFrame()
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
    
    # 获取去年数据（如果存在）
    last_year_week_df = pd.DataFrame()
    last_year_6_weeks_df = pd.DataFrame()
    last_year_ytd_df = pd.DataFrame()
    if has_last_year_data:
        last_year_week_df = get_last_year_week_data(last_year, selected_week, tuple(selected_markets), 
                                                    tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
        current_week_num = int(selected_week.replace("W", ""))
        week_numbers = [current_week_num - i for i in range(6) if current_week_num - i >= 1]
        week_labels = ["W" + str(w).zfill(2) for w in week_numbers]
        last_year_6_weeks_df = get_last_6_weeks_data(last_year, tuple(week_labels), tuple(selected_markets),
                                                    tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
        last_year_ytd_df = get_ytd_data(last_year, selected_week, tuple(selected_markets),
                                        tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    
    # 今年数据（始终存在）
    current_week_num = int(selected_week.replace("W", ""))
    week_numbers = [current_week_num - i for i in range(6) if current_week_num - i >= 1]
    week_labels = ["W" + str(w).zfill(2) for w in week_numbers]
    last_6_weeks_df = get_last_6_weeks_data(selected_year, tuple(week_labels), tuple(selected_markets),
                                            tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    ytd_df = get_ytd_data(selected_year, selected_week, tuple(selected_markets),
                          tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
    
    # ----------------------
    # 4. 计算各项聚合值及 YoY
    # ----------------------
    def calc_metrics(df_group):
        if df_group.empty:
            return {"GMV": 0, "毛利润": 0, "毛利率": 0, "经营利润率": 0, "净利率": 0, "退款补发率": 0, "ACOAS": 0}
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
    
    last_year_week_metrics = calc_metrics(last_year_week_df) if has_last_year_data else week_metrics.copy()
    last_year_6_metrics = calc_metrics(last_year_6_weeks_df) if has_last_year_data else last6_metrics.copy()
    last_year_ytd_metrics = calc_metrics(last_year_ytd_df) if has_last_year_data else ytd_metrics.copy()
    
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
    # 6. 核心指标概览
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
    # 7. 图表配色
    # ----------------------
    html_colors = ["#1e90ff", "#00bfff", "#87ceeb", "#4169e1", "#4682b4", 
                   "#5f9ea0", "#6495ed", "#6a5acd", "#7b68ee", "#8a2be2"]
    
    # 7.1 市场结构
    st.markdown('<div class="section-title">🌍 市场结构</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        market_sales = filtered_df.groupby("销售市场")["GMV"].sum().reset_index()
        fig_country = px.pie(market_sales, values="GMV", names="销售市场", 
                             title=f"{selected_year}年{selected_week} 国家市场份额",
                             hole=0.4, color_discrete_sequence=html_colors,
                             template="plotly_dark")
        fig_country.update_traces(textposition="inside", textinfo="percent+label", textfont_color="white")
        fig_country.update_layout(height=320, margin=dict(l=10, r=10, t=35, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_country, use_container_width=True)
    
    with col2:
        platform_sales = filtered_df.groupby("平台")["GMV"].sum().reset_index()
        platform_sales = platform_sales[platform_sales["GMV"] > 0]
        fig_platform = px.pie(platform_sales, values="GMV", names="平台",
                              title=f"{selected_year}年{selected_week} 平台销售额占比",
                              hole=0.4, color_discrete_sequence=html_colors,
                              template="plotly_dark")
        fig_platform.update_traces(textposition="inside", textinfo="percent+label", textfont_color="white")
        fig_platform.update_layout(height=320, margin=dict(l=10, r=10, t=35, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_platform, use_container_width=True)
    
    with col3:
        platform_quantity = filtered_df.groupby("平台")["销量"].sum().reset_index()
        platform_quantity = platform_quantity[platform_quantity["销量"] > 0]
        fig_platform_qty = px.pie(platform_quantity, values="销量", names="平台",
                                  title=f"{selected_year}年{selected_week} 平台销量占比",
                                  hole=0.4, color_discrete_sequence=html_colors,
                                  template="plotly_dark")
        fig_platform_qty.update_traces(textposition="inside", textinfo="percent+label", textfont_color="white")
        fig_platform_qty.update_layout(height=320, margin=dict(l=10, r=10, t=35, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_platform_qty, use_container_width=True)
    
    # 7.2 产品分析
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
        
        fig_ad1 = go.Figure()
        fig_ad1.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["ACOS"], mode='lines+markers', name='ACOS',
                                     hovertemplate='%{y:.1f}%<extra></extra>'))
        fig_ad1.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["ACOAS"], mode='lines+markers', name='ACOAS',
                                     line=dict(dash='dash'), hovertemplate='%{y:.1f}%<extra></extra>'))
        fig_ad1.add_trace(go.Scatter(x=ad_trend_df["年度周次"], y=ad_trend_df["ASOAS"], mode='lines+markers', name='ASOAS',
                                     line=dict(dash='dot'), hovertemplate='%{y:.1f}%<extra></extra>'))
        fig_ad1.update_layout(title="ACOS / ACOAS / ASOAS", height=400, template="plotly_dark",
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_ad1, use_container_width=True)
    
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
    
    # 7.5 同比分析（全部指标）
    st.markdown('<div class="section-title">📈 同比分析（全部指标）</div>', unsafe_allow_html=True)
    
    # 若无去年数据，显示提示
    if not has_last_year_data:
        st.info("当前数据源中无去年（{}年）数据，同比分析不可用。".format(last_year))
    else:
        metric_list = [
            ("销售额", "GMV", "sum", "currency"),
            ("客单价", "客单价", "mean", "currency"),
            ("毛利润率", "毛利率", "mean", "percent"),
            ("曝光量&CPC", None, None, None),
            ("广告花费", "花费", "sum", "currency"),
            ("广告销售额", "广告销售额", "sum", "currency"),
            ("ASOAS", "ASOAS", "mean", "percent"),
            ("CPA", "CPA", "mean", "currency"),
            ("CTR&CR", None, None, None)
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

        def compute_yoy_mom(yoy_df, current_col, last_col):
            yoy_df = yoy_df.copy()
            yoy_df["yoy"] = np.nan
            yoy_df["mom_current"] = np.nan
            
            # 1. 同比：需要当前年和去年数据都存在且非0
            valid_mask = (
                yoy_df[current_col].notna() &
                yoy_df[last_col].notna() &
                (yoy_df[current_col] != 0) &
                (yoy_df[last_col] != 0)
            )
            if valid_mask.any():
                yoy_df.loc[valid_mask, "yoy"] = ((
                    yoy_df.loc[valid_mask, current_col] - yoy_df.loc[valid_mask, last_col]
                ) / yoy_df.loc[valid_mask, last_col]) * 100
            
            # 2. 环比：只依赖当前年数据，与去年无关
            yoy_df["mom_current"] = yoy_df[current_col].pct_change(fill_method=None) * 100
            
            return yoy_df

        def sort_weeks_categorical(df, week_col="周次"):
            """将周次列转换为有序分类并排序，确保 W01 → W52 顺序"""
            week_order = [f"W{i:02d}" for i in range(1, 53)]
            cat_type = CategoricalDtype(categories=week_order, ordered=True)
            df[week_col] = df[week_col].astype(cat_type)
            return df.sort_values(week_col).reset_index(drop=True)

        rows = [metric_list[i:i+2] for i in range(0, len(metric_list), 2)]
        for row in rows:
            cols = st.columns(2)
            for idx, col in enumerate(cols):
                if idx < len(row):
                    metric_name, agg_col, agg_func, unit_type = row[idx]
                    
                    if metric_name == "曝光量&CPC":
                        current_exposure = get_weekly_agg(selected_year, "曝光量", "sum", tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                        last_exposure = get_weekly_agg(last_year, "曝光量", "sum", tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                        
                        def get_weekly_cpc(year):
                            filtered_df = df[
                                (df["年份"] == year) &
                                (df["销售市场"].isin(selected_markets)) &
                                (df["平台"].isin(selected_platforms)) &
                                (df["店铺"].isin(selected_shops)) &
                                (df["类目"].isin(selected_categories))
                            ]
                            grouped = filtered_df.groupby("周次", as_index=False).agg(
                                花费_sum=("花费", "sum"),
                                点击量_sum=("点击量", "sum")
                            )
                            if grouped.empty:
                                return pd.DataFrame(columns=["周次", "CPC"])
                            grouped["CPC"] = grouped.apply(
                                lambda row: row["花费_sum"] / row["点击量_sum"] if row["点击量_sum"] != 0 else 0,
                                axis=1
                            )
                            return grouped[["周次", "CPC"]]
                        
                        current_cpc = get_weekly_cpc(selected_year)
                        last_cpc = get_weekly_cpc(last_year)
                        
                        yoy_df = pd.merge(current_exposure, last_exposure, on="周次", how="outer", suffixes=("_current", "_last"))
                        yoy_df = sort_weeks_categorical(yoy_df)
                        yoy_df = compute_yoy_mom(yoy_df, "曝光量_current", "曝光量_last")
                        yoy_df = pd.merge(yoy_df, current_cpc.rename(columns={"CPC": "CPC_current"}), on="周次", how="left")
                        yoy_df = pd.merge(yoy_df, last_cpc.rename(columns={"CPC": "CPC_last"}), on="周次", how="left")
                        
                        if yoy_df.empty:
                            with col:
                                st.info(f"{metric_name}：无可显示周次")
                            continue
                        
                        fig = make_subplots(specs=[[{"secondary_y": True}]])
                        
                        # 分别处理去年和当前年数据，避免NaN干扰
                        last_valid = yoy_df[yoy_df["曝光量_last"].notna()].copy()
                        current_valid = yoy_df[yoy_df["曝光量_current"].notna()].copy()
                        
                        if not last_valid.empty:
                            text_last = [f"{int(v):,}" for v in last_valid["曝光量_last"]]
                            fig.add_trace(go.Bar(x=last_valid["周次"], y=last_valid["曝光量_last"], name=f"{last_year}年", marker_color=html_colors[2], text=text_last, textposition="outside"), secondary_y=False)
                        
                        if not current_valid.empty:
                            text_current = [f"{int(v):,}" for v in current_valid["曝光量_current"]]
                            fig.add_trace(go.Bar(x=current_valid["周次"], y=current_valid["曝光量_current"], name=f"{selected_year}年", marker_color=html_colors[0], text=text_current, textposition="outside"), secondary_y=False)
                        
                        # CPC线图保留完整数据
                        cpc_valid = yoy_df[yoy_df["CPC_current"].notna()].copy()
                        if not cpc_valid.empty:
                            fig.add_trace(go.Scatter(x=cpc_valid["周次"], y=cpc_valid["CPC_current"], mode='lines+markers', name="CPC",
                                                     line=dict(color=html_colors[1]), hovertemplate='%{y:.2f} ¥<extra></extra>'), secondary_y=False)
                        
                        cpc_last_valid = yoy_df[yoy_df["CPC_last"].notna()].copy()
                        if not cpc_last_valid.empty:
                            fig.add_trace(go.Scatter(x=cpc_last_valid["周次"], y=cpc_last_valid["CPC_last"], mode='lines+markers', name="CPC (去年)",
                                                     line=dict(color=html_colors[3]), hovertemplate='%{y:.2f} ¥<extra></extra>'), secondary_y=False)
                        if yoy_df["yoy"].notna().any():
                            fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["yoy"], mode='markers', name="同比增长率",
                                                     marker=dict(color='red', size=8, symbol='triangle-up'), texttemplate='%{y:.1f}%', textposition="top center",
                                                     hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                        fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["mom_current"], mode='markers', name="今年环比",
                                                 marker=dict(color='orange', size=6, symbol='circle'), texttemplate='%{y:.1f}%', textposition="top center",
                                                 hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                        
                        fig.update_layout(title=metric_name, height=350, template="plotly_dark",
                                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        fig.update_xaxes(title_text="周次", categoryorder="array", categoryarray=[str(x) for x in yoy_df["周次"]])
                        fig.update_yaxes(title_text="曝光量 / CPC (¥)", secondary_y=False)
                        fig.update_yaxes(title_text="变化率 (%)", secondary_y=True)
                        
                    elif metric_name == "CTR&CR":
                        current_ctr = get_weekly_agg(selected_year, "点击率", "mean", tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                        last_ctr = get_weekly_agg(last_year, "点击率", "mean", tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                        current_cr = get_weekly_agg(selected_year, "转化率", "mean", tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                        last_cr = get_weekly_agg(last_year, "转化率", "mean", tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                        
                        yoy_df = pd.merge(current_ctr, last_ctr, on="周次", how="outer", suffixes=("_current", "_last"))
                        yoy_df = sort_weeks_categorical(yoy_df)
                        yoy_df = compute_yoy_mom(yoy_df, "点击率_current", "点击率_last")
                        yoy_df = pd.merge(yoy_df, current_cr.rename(columns={"转化率": "CR_current"}), on="周次", how="left")
                        yoy_df = pd.merge(yoy_df, last_cr.rename(columns={"转化率": "CR_last"}), on="周次", how="left")
                        
                        if yoy_df.empty:
                            with col:
                                st.info(f"{metric_name}：无可显示周次")
                            continue
                        
                        fig = make_subplots(specs=[[{"secondary_y": True}]])
                        
                        # 分别处理去年和当前年数据
                        ctr_last_valid = yoy_df[yoy_df["点击率_last"].notna()].copy()
                        if not ctr_last_valid.empty:
                            fig.add_trace(go.Scatter(x=ctr_last_valid["周次"], y=ctr_last_valid["点击率_last"], mode='lines+markers', name=f"{last_year}年 CTR",
                                                     line=dict(color=html_colors[2]), hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=False)
                        
                        ctr_current_valid = yoy_df[yoy_df["点击率_current"].notna()].copy()
                        if not ctr_current_valid.empty:
                            fig.add_trace(go.Scatter(x=ctr_current_valid["周次"], y=ctr_current_valid["点击率_current"], mode='lines+markers', name=f"{selected_year}年 CTR",
                                                     line=dict(color=html_colors[0]), hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=False)
                        
                        cr_last_valid = yoy_df[yoy_df["CR_last"].notna()].copy()
                        if not cr_last_valid.empty:
                            fig.add_trace(go.Scatter(x=cr_last_valid["周次"], y=cr_last_valid["CR_last"], mode='lines+markers', name=f"{last_year}年 CR",
                                                     line=dict(color=html_colors[3]), hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=False)
                        
                        cr_current_valid = yoy_df[yoy_df["CR_current"].notna()].copy()
                        if not cr_current_valid.empty:
                            fig.add_trace(go.Scatter(x=cr_current_valid["周次"], y=cr_current_valid["CR_current"], mode='lines+markers', name=f"{selected_year}年 CR",
                                                     line=dict(color=html_colors[1]), hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=False)
                        if yoy_df["yoy"].notna().any():
                            fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["yoy"], mode='markers', name="CTR同比增长率",
                                                     marker=dict(color='red', size=8, symbol='triangle-up'), texttemplate='%{y:.1f}%', textposition="top center",
                                                     hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                        fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["mom_current"], mode='markers', name="CTR今年环比",
                                                 marker=dict(color='orange', size=6, symbol='circle'), texttemplate='%{y:.1f}%', textposition="top center",
                                                 hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                        
                        fig.update_layout(title=metric_name, height=350, template="plotly_dark",
                                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        fig.update_xaxes(title_text="周次", categoryorder="array", categoryarray=[str(x) for x in yoy_df["周次"]])
                        fig.update_yaxes(title_text="百分比 (%)", secondary_y=False)
                        fig.update_yaxes(title_text="变化率 (%)", secondary_y=True)
                        
                    else:
                        current_df = get_weekly_agg(selected_year, agg_col, agg_func, tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                        last_df = get_weekly_agg(last_year, agg_col, agg_func, tuple(selected_markets), tuple(selected_platforms), tuple(selected_shops), tuple(selected_categories))
                        
                        yoy_df = pd.merge(current_df, last_df, on="周次", how="outer", suffixes=("_current", "_last"))
                        yoy_df = sort_weeks_categorical(yoy_df)
                        yoy_df = compute_yoy_mom(yoy_df, f"{agg_col}_current", f"{agg_col}_last")

                        if yoy_df.empty:
                            with col:
                                st.info(f"{metric_name}：无可显示周次")
                            continue

                        if unit_type == "currency":
                            y_title = f"{metric_name} (¥)"
                            text_current = [f"¥{v:,.0f}" if pd.notna(v) else "" for v in yoy_df[f"{agg_col}_current"]]
                            text_last = [f"¥{v:,.0f}" if pd.notna(v) else "" for v in yoy_df[f"{agg_col}_last"]]
                            hovertemplate = "¥%{y:,.0f}<extra></extra>"
                        else:
                            y_title = f"{metric_name} (%)"
                            text_current = [f"{v:.1f}%" if pd.notna(v) else "" for v in yoy_df[f"{agg_col}_current"]]
                            text_last = [f"{v:.1f}%" if pd.notna(v) else "" for v in yoy_df[f"{agg_col}_last"]]
                            hovertemplate = "%{y:.1f}%<extra></extra>"
                        
                        fig = make_subplots(specs=[[{"secondary_y": True}]])
                        if metric_name in ["销售额", "客单价", "广告花费", "广告销售额"]:
                            # Bar图：分别处理去年和当前年数据
                            last_valid = yoy_df[yoy_df[f"{agg_col}_last"].notna()].copy()
                            if not last_valid.empty:
                                if unit_type == "currency":
                                    text_last_valid = [f"¥{v:,.0f}" for v in last_valid[f"{agg_col}_last"]]
                                else:
                                    text_last_valid = [f"{v:.1f}%" for v in last_valid[f"{agg_col}_last"]]
                                fig.add_trace(go.Bar(x=last_valid["周次"], y=last_valid[f"{agg_col}_last"], name=f"{last_year}年", marker_color=html_colors[2], text=text_last_valid, textposition="outside"), secondary_y=False)
                            
                            current_valid = yoy_df[yoy_df[f"{agg_col}_current"].notna()].copy()
                            if not current_valid.empty:
                                if unit_type == "currency":
                                    text_current_valid = [f"¥{v:,.0f}" for v in current_valid[f"{agg_col}_current"]]
                                else:
                                    text_current_valid = [f"{v:.1f}%" for v in current_valid[f"{agg_col}_current"]]
                                fig.add_trace(go.Bar(x=current_valid["周次"], y=current_valid[f"{agg_col}_current"], name=f"{selected_year}年", marker_color=html_colors[0], text=text_current_valid, textposition="outside"), secondary_y=False)
                        else:
                            # Scatter图：分别处理去年和当前年数据
                            last_valid = yoy_df[yoy_df[f"{agg_col}_last"].notna()].copy()
                            if not last_valid.empty:
                                fig.add_trace(go.Scatter(x=last_valid["周次"], y=last_valid[f"{agg_col}_last"], mode='lines+markers', name=f"{last_year}年", line=dict(color=html_colors[2]), hovertemplate=hovertemplate), secondary_y=False)
                            
                            current_valid = yoy_df[yoy_df[f"{agg_col}_current"].notna()].copy()
                            if not current_valid.empty:
                                fig.add_trace(go.Scatter(x=current_valid["周次"], y=current_valid[f"{agg_col}_current"], mode='lines+markers', name=f"{selected_year}年", line=dict(color=html_colors[0]), hovertemplate=hovertemplate), secondary_y=False)
                        
                        if yoy_df["yoy"].notna().any():
                            fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["yoy"], mode='markers', name="同比增长率",
                                                     marker=dict(color='red', size=8, symbol='triangle-up'), texttemplate='%{y:.1f}%', textposition="top center",
                                                     hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                        fig.add_trace(go.Scatter(x=yoy_df["周次"], y=yoy_df["mom_current"], mode='markers', name="今年环比",
                                                 marker=dict(color='orange', size=6, symbol='circle'), texttemplate='%{y:.1f}%', textposition="top center",
                                                 hovertemplate='%{y:.1f}%<extra></extra>'), secondary_y=True)
                        
                        fig.update_layout(title=metric_name, height=350, template="plotly_dark",
                                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        fig.update_xaxes(title_text="周次", categoryorder="array", categoryarray=[str(x) for x in yoy_df["周次"]])
                        fig.update_yaxes(title_text=y_title, secondary_y=False)
                        fig.update_yaxes(title_text="变化率 (%)", secondary_y=True)
                    
                    with col:
                        st.plotly_chart(fig, use_container_width=True)
    
    # ----------------------
    # 8. 详细数据表（按系列）
    # ----------------------
    st.divider()
    st.markdown('<div class="section-title">📋 详细数据报表（系列维度）</div>', unsafe_allow_html=True)
    
    series_gmv_order = filtered_df.groupby("系列名称")["GMV"].sum().sort_values(ascending=False)
    all_series_sorted = series_gmv_order.index.tolist()
    
    detail_metric_keys = [
        ("GMV", "GMV", True),
        ("客单价", "客单价", True),
        ("毛利润", "毛利润", True),
        ("毛利率", "毛利率", False),
        ("经营利润率", "经营利润率", False),
        ("净利率", "净利率", False),
        ("退款补发率", "退款补发率", False)
    ]
    
    def get_series_metrics_weighted(series_name, df_group, last_df_group):
        if df_group.empty or last_df_group.empty:
            # 若去年数据不存在，则YoY显示为空
            pass
        series_current = df_group[df_group["系列名称"] == series_name]
        series_last = last_df_group[last_df_group["系列名称"] == series_name] if not last_df_group.empty else pd.DataFrame()
        
        result = {}
        for label, col, is_currency in detail_metric_keys:
            if col in ["GMV", "毛利润"]:
                cur_val = series_current[col].sum()
                last_val = series_last[col].sum() if not series_last.empty else 0
            elif col == "客单价":
                cur_gmv = series_current["GMV"].sum()
                cur_qty = series_current["销量"].sum()
                cur_val = (cur_gmv / cur_qty) if cur_qty != 0 else 0
                
                last_gmv = series_last["GMV"].sum() if not series_last.empty else 0
                last_qty = series_last["销量"].sum() if not series_last.empty else 0
                last_val = (last_gmv / last_qty) if last_qty != 0 else 0
            else:
                cur_gmv = series_current["GMV"].sum()
                cur_profit = series_current["毛利润"].sum()
                cur_operating = series_current["经营利润"].sum()
                cur_cost = series_current["花费"].sum()
                last_gmv = series_last["GMV"].sum() if not series_last.empty else 0
                last_profit = series_last["毛利润"].sum() if not series_last.empty else 0
                last_operating = series_last["经营利润"].sum() if not series_last.empty else 0
                last_cost = series_last["花费"].sum() if not series_last.empty else 0
                
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
            
            if last_val != 0:
                yoy = ((cur_val - last_val) / last_val) * 100
            else:
                yoy = 100 if cur_val > 0 else (-100 if cur_val < 0 else 0)
            result[label] = (cur_val, yoy, is_currency)
        return result
    
    time_frames = [
        ("当周", filtered_df, last_year_week_df if has_last_year_data else pd.DataFrame()),
        ("近六周", last_6_weeks_df, last_year_6_weeks_df if has_last_year_data else pd.DataFrame()),
        ("YTD", ytd_df, last_year_ytd_df if has_last_year_data else pd.DataFrame())
    ]
    
    data_dict = {}
    for series in all_series_sorted:
        row = {}
        for time_label, df_cur, df_last in time_frames:
            metrics = get_series_metrics_weighted(series, df_cur, df_last)
            for metric_label, (value, yoy, is_currency) in metrics.items():
                col_name = f"{time_label}_{metric_label}"
                row[col_name] = value
                if yoy == 0:
                    yoy_str = ""
                elif yoy > 0:
                    yoy_str = f"({yoy:.1f}% ↑)"
                else:
                    yoy_str = f"({yoy:.1f}% ↓)"
                row[f"{col_name}_YoY"] = yoy_str
        data_dict[series] = row
    
    detail_df = pd.DataFrame.from_dict(data_dict, orient='index')
    detail_df.index.name = "系列名称"
    
    default_sort_col = "当周_GMV"
    if default_sort_col in detail_df.columns:
        detail_df = detail_df.sort_values(by=default_sort_col, ascending=False)
    
    column_config = {}
    for col in detail_df.columns:
        if col.endswith("_YoY"):
            column_config[col] = st.column_config.TextColumn()
        else:
            if "GMV" in col or "毛利润" in col or "客单价" in col:
                column_config[col] = st.column_config.NumberColumn(format="¥%.0f", help="货币单位：元")
            else:
                column_config[col] = st.column_config.NumberColumn(format="%.1f%%", help="百分比")
    
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
    st.error("❌ 数据加载失败，请确保 NPC销售看板数据.xlsx 文件存在且工作表名为“数据源”。")