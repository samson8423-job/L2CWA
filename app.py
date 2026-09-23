import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import logging
from datetime import datetime
import json

from fetch_weather import fetch_airbox_data, fetch_weather_data
from parse_weather import parse_airbox_data, parse_weather_data
from database import init_db, insert_air_stations, get_air_stations, get_station_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化資料庫
init_db()

st.set_page_config(
    page_title="EdiGreen 空氣盒子 | 台灣微型氣象與空氣品質監測",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定義 CSS 實現 EdiGreen 空氣盒子介面風格
st.markdown("""
<style>
    /* 隱藏預設多餘邊界 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* 側邊欄樣式調整 */
    [data-testid="stSidebar"] {
        background-color: #f7f9fa;
        border-right: 1px solid #e2e8f0;
    }
    
    /* 模擬 EdiGreen 側邊欄按鈕風格 */
    .admin-btn {
        background: #6c89b7;
        color: white !important;
        text-align: center;
        padding: 8px 12px;
        border-radius: 4px;
        font-weight: 500;
        margin-bottom: 12px;
        display: block;
        text-decoration: none;
    }
    
    /* 側邊欄標籤文字 */
    .filter-label {
        font-size: 13px;
        font-weight: 600;
        color: #4a5568;
        margin-top: 10px;
        margin-bottom: 4px;
    }
    
    /* 地圖浮動圖例卡片 */
    .legend-container {
        position: fixed;
        bottom: 25px;
        left: 350px;
        z-index: 999;
        background: rgba(255, 255, 255, 0.95);
        padding: 6px 12px;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        gap: 2px;
        font-size: 11px;
    }
    
    .legend-box {
        padding: 2px 8px;
        color: white;
        font-weight: bold;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# 檢查資料庫是否有測站，沒有則自動同步抓取
existing_stations = get_air_stations(include_offline=True)
if not existing_stations:
    with st.spinner("正在初始化空氣盒子與氣象觀測站資料..."):
        try:
            air_raw = fetch_airbox_data()
            parsed = parse_airbox_data(air_raw)
            insert_air_stations(parsed)
            existing_stations = get_air_stations(include_offline=True)
        except Exception as e:
            logger.error(f"初始資料取得失敗: {e}")

# ==================== 側邊欄 (Sidebar) ====================
with st.sidebar:
    # 頂部 Logo 與標題
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            <div style="background: #25a374; border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; color: white; font-size: 22px; font-weight: bold;">
                ☁️
            </div>
            <div>
                <div style="color: #25a374; font-size: 13px; font-weight: bold; line-height: 1;">EdiGreen</div>
                <div style="color: #2c3e50; font-size: 20px; font-weight: 900; line-height: 1.2;">空氣盒子</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="admin-btn">管理者登入 ▾</div>', unsafe_allow_html=True)
    
    language = st.selectbox("語言設定", ["繁體中文", "English"], label_visibility="collapsed")
    
    with st.expander("偵測站點顯示", expanded=True):
        st.markdown('<div class="filter-label">懸浮微粒子標準 ⓘ</div>', unsafe_allow_html=True)
        aqi_std = st.radio("標準", ["TW", "UK AQI"], horizontal=True, label_visibility="collapsed")
        
        st.markdown('<div class="filter-label">偵測站點 ⓘ</div>', unsafe_allow_html=True)
        station_filter_mode = st.radio("站點模式", ["Station", "ADF"], horizontal=True, label_visibility="collapsed")
        
        st.markdown('<div class="filter-label">站點類別篩選</div>', unsafe_allow_html=True)
        station_type_filter = st.selectbox(
            "站點類別", 
            ["All", "空氣盒子觀測點", "環保署觀測站", "開放資料觀測站", "資料異於周圍環境", "機器需檢修"],
            label_visibility="collapsed"
        )
        
        col_wind, col_off = st.columns(2)
        with col_wind:
            show_wind = st.toggle("風力線 ⓘ", value=False)
        with col_off:
            show_offline = st.toggle("顯示離線 ⓘ", value=True)
            
    with st.expander("工具 ▾", expanded=False):
        st.write("• 地圖圖層切換")
        st.write("• 歷史軌跡重播")
        st.write("• CSV 數據匯出")
        
    st.markdown("---")
    if st.button("🔄 更新即時監測資料", use_container_width=True):
        with st.spinner("正在同步最新空氣盒子與氣象資料..."):
            try:
                air_raw = fetch_airbox_data()
                parsed = parse_airbox_data(air_raw)
                count = insert_air_stations(parsed)
                st.success(f"成功更新 {count} 個測站即時資訊！")
                st.rerun()
            except Exception as e:
                st.error(f"更新失敗: {e}")

# ==================== 主地圖繪製與資料整合 ====================
stations = get_air_stations(
    station_type=station_type_filter, 
    include_offline=show_offline
)

# 依 PM2.5 決定標籤顏色
def get_pm25_color(val):
    if val < 15:
        return "#00E400"  # 綠色
    elif val <= 35:
        return "#FFD700"  # 金黃色
    elif val <= 54:
        return "#FF7E00"  # 橘色
    elif val <= 150:
        return "#FF0000"  # 紅色
    elif val <= 250:
        return "#8F3F97"  # 紫色
    else:
        return "#7E0023"  # 褐紅色

# 建立 HTML/SVG 時序趨勢圖表，嵌入 Folium 彈出視窗
def create_popup_html(stn, history):
    pm25 = stn.get('pm25', 0)
    temp = stn.get('temperature', 0)
    hum = stn.get('humidity', 0)
    name = stn.get('name', '未命名站點')
    lat = stn.get('lat', 0)
    lon = stn.get('lon', 0)
    updated = stn.get('updated_at', '')
    
    # 準備 SVG 點位
    times = [h['time'].split(":")[0] for h in history]
    pm_vals = [h['pm25'] for h in history]
    temp_vals = [h['temperature'] for h in history]
    hum_vals = [h['humidity'] for h in history]
    
    # PM2.5 折線 SVG (寬 320, 高 80)
    max_pm = max(max(pm_vals) if pm_vals else 1, 10)
    svg_pm_pts = []
    svg_pm_dots = ""
    for idx, p in enumerate(pm_vals):
        x = 20 + idx * (280 / max(len(pm_vals)-1, 1))
        y = 65 - (p / max_pm) * 50
        svg_pm_pts.append(f"{x:.1f},{y:.1f}")
        svg_pm_dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="#00bcd4" />'
        
    pm_polyline = " ".join(svg_pm_pts)
    
    # 溫濕度雙面積圖 SVG (寬 320, 高 90)
    # 溫度：黃色面積，濕度：青藍色面積
    min_t, max_t = min(temp_vals) - 1 if temp_vals else 20, max(temp_vals) + 1 if temp_vals else 35
    min_h, max_h = 30, 80
    
    temp_pts = []
    for idx, t in enumerate(temp_vals):
        x = 20 + idx * (280 / max(len(temp_vals)-1, 1))
        y = 75 - ((t - min_t) / max(max_t - min_t, 1)) * 55
        temp_pts.append((x, y))
        
    hum_pts = []
    for idx, h in enumerate(hum_vals):
        x = 20 + idx * (280 / max(len(hum_vals)-1, 1))
        y = 75 - ((h - min_h) / max(max_h - min_h, 1)) * 55
        hum_pts.append((x, y))
        
    # 構建溫度多邊形 (黃色)
    temp_poly = f"20,75 " + " ".join([f"{x:.1f},{y:.1f}" for x, y in temp_pts]) + f" 300,75"
    # 構建濕度多邊形 (青色)
    hum_poly = f"20,75 " + " ".join([f"{x:.1f},{y:.1f}" for x, y in hum_pts]) + f" 300,75"

    html = f"""
    <div style="font-family: Arial, sans-serif; width: 330px; padding: 4px; color: #333;">
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <div style="color: #0288d1; font-size: 16px; font-weight: bold;">{name}</div>
            <div style="color: #0288d1; font-size: 13px;">{lat:.3f}°N / {lon:.3f}°E</div>
        </div>
        <div style="font-size: 12px; margin-top: 4px; color: #555;">
            Pm2.5 : <b>{pm25}</b> μg/m³<br>
            溫度 : <b>{temp:.2f}°C</b>，濕度 : <b>{hum:.0f}%</b>
        </div>
        
        <!-- PM2.5 趨勢圖 -->
        <div style="margin-top: 8px; font-size: 11px; color: #777;">Pm2.5</div>
        <svg width="320" height="75" style="background: #fafafa; border: 1px solid #eee; border-radius: 3px;">
            <!-- 網格線 -->
            <line x1="20" y1="20" x2="300" y2="20" stroke="#f0f0f0" stroke-width="1" />
            <line x1="20" y1="45" x2="300" y2="45" stroke="#f0f0f0" stroke-width="1" />
            <line x1="20" y1="65" x2="300" y2="65" stroke="#ccc" stroke-width="1" />
            
            <polyline fill="none" stroke="#00bcd4" stroke-width="1.8" points="{pm_polyline}" />
            {svg_pm_dots}
            <text x="22" y="73" font-size="9" fill="#999">00</text>
            <text x="155" y="73" font-size="9" fill="#999">12</text>
            <text x="290" y="73" font-size="9" fill="#999">23</text>
        </svg>
        
        <!-- 溫度與濕度雙時序面積圖 -->
        <div style="display: flex; justify-content: space-between; margin-top: 6px; font-size: 11px; color: #777;">
            <span>溫度 (°C)</span>
            <span>濕度 (%)</span>
        </div>
        <svg width="320" height="80" style="background: #fafafa; border: 1px solid #eee; border-radius: 3px;">
            <polygon points="{hum_poly}" fill="rgba(0, 188, 212, 0.45)" stroke="#0097a7" stroke-width="1" />
            <polygon points="{temp_poly}" fill="rgba(255, 193, 7, 0.65)" stroke="#ffa000" stroke-width="1" />
            <line x1="20" y1="75" x2="300" y2="75" stroke="#ccc" stroke-width="1" />
        </svg>
        
        <div style="font-size: 10px; color: #999; margin-top: 6px; text-align: left;">
            最後更新時間: {updated}
        </div>
    </div>
    """
    return html

# 建立 Folium 地圖，鎖定台灣本島
m = folium.Map(
    location=[23.85, 120.95],
    zoom_start=8,
    tiles="cartodbpositron",  # 乾淨淺色地圖圖磚，完美貼合範例圖片
    prefer_canvas=True
)

# 繪製各測站標記
for stn in stations:
    pm25 = stn['pm25']
    color = get_pm25_color(pm25)
    history = get_station_history(stn['station_id'])
    
    # 彈出視窗
    popup_content = create_popup_html(stn, history)
    iframe = folium.IFrame(popup_content, width=340, height=270)
    popup = folium.Popup(iframe, max_width=360)
    
    # 自訂圓形標記帶數值（如截圖中的綠色/黃色圓圈徽章）
    display_num = int(round(pm25))
    icon_html = f"""
    <div style="
        background-color: {color};
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: {'#333' if color in ['#FFD700', '#00E400'] else '#fff'};
        font-size: 10px;
        font-weight: bold;
        border: 1.5px solid white;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    ">
        {display_num}
    </div>
    """
    
    # 如果是目標站點 AAA2，特別使用醒目的圖示標記
    if stn['station_id'] == 'AAA2':
        folium.Marker(
            location=[stn['lat'], stn['lon']],
            popup=popup,
            tooltip=f"{stn['name']} (點擊檢視詳細時序)",
            icon=folium.Icon(color="red", icon="cloud")
        ).add_to(m)
    else:
        folium.Marker(
            location=[stn['lat'], stn['lon']],
            popup=popup,
            tooltip=f"{stn['name']} | PM2.5: {pm25} | 溫: {stn['temperature']}°C 濕: {stn['humidity']}%",
            icon=folium.DivIcon(html=icon_html, icon_size=(22, 22), icon_anchor=(11, 11))
        ).add_to(m)

# 渲染滿版地圖
map_col, info_col = st.columns([3.6, 1.4])

with map_col:
    # 顯示全幅台灣地圖
    map_data = st_folium(m, width="100%", height=660, returned_objects=["last_clicked"])
    
    # 地圖下方的圖例說明條（還原左下角與右下角配置）
    col_leg_left, col_leg_right = st.columns([1.2, 1])
    
    with col_leg_left:
        st.markdown("""
        <div style="display: flex; align-items: center; background: #fff; padding: 6px 12px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); font-size: 12px; gap: 4px;">
            <span style="background: #00E400; color: white; padding: 2px 8px; font-weight: bold; border-radius: 2px;">&lt;15</span>
            <span style="background: #FFD700; color: #333; padding: 2px 8px; font-weight: bold; border-radius: 2px;">35</span>
            <span style="background: #FF7E00; color: white; padding: 2px 8px; font-weight: bold; border-radius: 2px;">54</span>
            <span style="background: #FF0000; color: white; padding: 2px 8px; font-weight: bold; border-radius: 2px;">150</span>
            <span style="background: #8F3F97; color: white; padding: 2px 8px; font-weight: bold; border-radius: 2px;">250</span>
            <span style="background: #7E0023; color: white; padding: 2px 8px; font-weight: bold; border-radius: 2px;">&gt;251</span>
            <span style="color: #666; font-size: 11px; margin-left: 6px;">(μg/m³)</span>
        </div>
        """, unsafe_allow_html=True)
        
    with col_leg_right:
        st.markdown("""
        <div style="background: #fff; padding: 6px 10px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); font-size: 11px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
            <div>🟢 空氣盒子觀測點</div>
            <div>🏛️ 環保署觀測站</div>
            <div>🏠 資料異於周圍環境</div>
            <div>🚧 機器需檢修</div>
            <div>🚢 開放資料觀測站</div>
        </div>
        """, unsafe_allow_html=True)

with info_col:
    st.subheader("📊 站點即時與時序指標")
    st.caption("點擊地圖標記或自下方選單選取檢視站點")
    
    stn_options = [s['name'] for s in stations]
    selected_name = st.selectbox("選取站點詳細檢視", stn_options, index=0 if stn_options else None)
    
    selected_stn = next((s for s in stations if s['name'] == selected_name), None)
    
    if selected_stn:
        st.markdown(f"### **{selected_stn['name']}**")
        st.markdown(f"📍 **經緯度**: `{selected_stn['lat']:.3f}°N / {selected_stn['lon']:.3f}°E`")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("PM2.5", f"{selected_stn['pm25']} μg/m³")
        c2.metric("溫度", f"{selected_stn['temperature']:.1f}°C")
        c3.metric("相對濕度", f"{selected_stn['humidity']:.0f}%")
        
        hist = get_station_history(selected_stn['station_id'])
        if hist:
            df_hist = pd.DataFrame(hist)
            df_hist['hour'] = df_hist['record_time'].apply(lambda x: x.split(":")[0] if ":" in x else x)
            
            st.markdown("##### **PM2.5 過去 24 小時時序**")
            st.line_chart(df_hist.set_index('hour')[['pm25']], color="#00bcd4")
            
            st.markdown("##### **溫度 (°C) 與 濕度 (%) 時序**")
            st.area_chart(df_hist.set_index('hour')[['temperature', 'humidity']])
            
        st.caption(f"最後更新時間：{selected_stn['updated_at']}")
