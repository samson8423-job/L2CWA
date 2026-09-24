import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import logging
from datetime import datetime
import math
import os
import importlib
from dotenv import load_dotenv

from fetch_weather import fetch_airbox_data, fetch_epa_data, fetch_weather_data, fetch_cwa_7day_forecast
from parse_weather import parse_airbox_data, parse_weather_data, generate_24h_history, get_station_region, parse_cwa_7day_forecast

import database as database_module

_required_database_functions = (
    "init_db",
    "insert_air_stations",
    "get_air_stations",
    "get_station_history",
    "update_station_regions",
    "insert_7day_forecasts",
    "get_7day_forecasts",
    "get_station_ids_needing_7day_forecasts",
)
if any(not hasattr(database_module, name) for name in _required_database_functions):
    database_module = importlib.reload(database_module)

from database import (
    init_db,
    insert_air_stations,
    get_air_stations,
    get_station_history,
    update_station_regions,
    insert_7day_forecasts,
    get_7day_forecasts,
    get_station_ids_needing_7day_forecasts,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FORECAST_REGION_KEYWORDS = {
    '北部地區': '臺北市',
    '中部地區': '臺中市',
    '南部地區': '高雄市',
    '東北部地區': '宜蘭縣',
    '東部地區': '花蓮縣',
    '東南部地區': '臺東縣',
    '外島地區': '澎湖縣',
}


def sync_station_forecasts(stations):
    """抓取並將測站未來七日預報寫入資料庫；UI 選站時只讀資料庫。"""
    cwa_forecast = fetch_cwa_7day_forecast()
    forecast_rows = []
    for station in stations:
        station_id = str(station['station_id'])
        station_forecasts = parse_cwa_7day_forecast(
            cwa_forecast,
            station_id,
            str(station.get('name', '')),
        )
        if not station_forecasts:
            fallback_keyword = FORECAST_REGION_KEYWORDS.get(station.get('region'), '')
            if fallback_keyword:
                station_forecasts = parse_cwa_7day_forecast(
                    cwa_forecast,
                    station_id,
                    fallback_keyword,
                )
        forecast_rows.extend(station_forecasts)
    return insert_7day_forecasts(forecast_rows)

# 初始化 SQLite 資料庫
init_db()

st.set_page_config(
    page_title="CWA 天氣預報網站",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定義 CSS 實現 EdiGreen 空氣盒子介面風格
st.markdown("""
<style>
    /* 調整主要版面邊界，營造滿版地圖體驗 */
    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 0.5rem;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
        max-width: 100% !important;
    }

    /* 側邊欄樣式調整 */
    [data-testid="stSidebar"] {
        background-color: #f7f9fa;
        border-right: 1px solid #e2e8f0;
    }
    
    /* EdiGreen 側邊欄按鈕風格 */
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
        cursor: pointer;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .admin-btn:hover {
        background: #5b78a5;
    }
    
    /* 側邊欄標籤文字 */
    .filter-label {
        font-size: 13px;
        font-weight: 600;
        color: #4a5568;
        margin-top: 10px;
        margin-bottom: 4px;
    }
    
    /* 浮動圖例控制項 */
    .legend-scale-bar {
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.95);
        padding: 5px 10px;
        border-radius: 4px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        font-size: 12px;
        gap: 3px;
    }
    
    .legend-type-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 8px 12px;
        border-radius: 4px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        font-size: 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    /* 首次載入期間固定顯示遮罩，直到地圖與下方資料都完成渲染 */
    div[data-testid="stStatusWidget"] {
        position: fixed !important;
        inset: 0 !important;
        z-index: 99999 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100vw !important;
        height: 100vh !important;
        background: rgba(15, 23, 42, 0.62) !important;
        backdrop-filter: blur(3px);
        box-sizing: border-box !important;
    }

    div[data-testid="stStatusWidget"] > details {
        padding: 28px 36px !important;
        border-radius: 14px !important;
        background: #fff !important;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.24) !important;
        color: #2c3e50 !important;
    }
</style>
""", unsafe_allow_html=True)

# 遮罩放在資料讀取與地圖建立之前，首次執行完成後才移除。
is_initial_page_load = not st.session_state.get("_initial_page_loaded", False)
loading_overlay = st.empty()
if is_initial_page_load:
    loading_overlay.status("頁面載入中，正在準備站點資料與地圖…", expanded=True)

# 檢查資料庫是否有測站，若無或少於 150 站則自動同步抓取
existing_stations = get_air_stations(include_offline=True)
if not existing_stations or len(existing_stations) < 150:
    try:
        with st.spinner("正在初始化資料，下載全台空氣品質觀測資料…", show_time=True):
            air_raw = fetch_airbox_data()
            epa_raw = fetch_epa_data()
            parsed = parse_airbox_data(air_raw, epa_raw)
            insert_air_stations(parsed)
            existing_stations = get_air_stations(include_offline=True)
    except Exception as e:
        st.error(f"初始資料取得失敗: {e}")
        logger.error(f"初始資料取得失敗: {e}")

# 每次啟動時修正舊版快取站點的分區，東北／東南不必等手動同步才出現。
if existing_stations:
    station_regions = [
        (
            str(station['station_id']),
            get_station_region(station.get('name', ''), station.get('lat', 0), station.get('lon', 0)),
        )
        for station in existing_stations
    ]
    update_station_regions(station_regions)
    existing_stations = get_air_stations(include_offline=True)

    # 快取缺資料時每個 session 僅自動同步一次；正常選站只讀 DB，不觸發 API。
    missing_forecast_ids = set(get_station_ids_needing_7day_forecasts(
        [str(station['station_id']) for station in existing_stations]
    ))
    forecast_bootstrap_key = "_forecast_bootstrap_attempted_date"
    today_key = datetime.now().date().isoformat()
    if missing_forecast_ids and st.session_state.get(forecast_bootstrap_key) != today_key:
        st.session_state[forecast_bootstrap_key] = today_key
        try:
            stations_to_sync = [
                station for station in existing_stations
                if str(station['station_id']) in missing_forecast_ids
            ]
            forecast_count = sync_station_forecasts(stations_to_sync)
            if forecast_count == 0:
                st.warning(
                    "初次載入未取得七日預報資料。請確認 CWA API Key 與 API 回應；"
                    "資料不會在每次切換站點時重抓。"
                )
        except Exception as e:
            logger.error(f"初始七日預報同步失敗: {e}")
            st.warning(f"初次載入七日預報同步失敗：{e}")

# ==================== 側邊欄 (Sidebar) ====================
with st.sidebar:
    # 頂部 Logo 與標題
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
            <div style="background: #25a374; border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; color: white; font-size: 22px; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.15);">
                ☁️
            </div>
            <div>
                <div style="color: #25a374; font-size: 13px; font-weight: bold; line-height: 1;">EdiGreen</div>
                <div style="color: #2c3e50; font-size: 21px; font-weight: 900; line-height: 1.2;">CWA 天氣預報網站</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # st.markdown('<div class="admin-btn">管理者登入 ▾</div>', unsafe_allow_html=True)
    
    # language = st.selectbox("語言設定", ["繁體中文", "English"], label_visibility="collapsed")
    
    with st.expander("偵測站點顯示 ▾", expanded=True):
        st.markdown('<div class="filter-label">懸浮微粒子標準 ⓘ</div>', unsafe_allow_html=True)
        aqi_std = st.radio("標準", ["TW", "UK AQI"], horizontal=True, label_visibility="collapsed")
        
        st.markdown('<div class="filter-label">偵測站點 ⓘ</div>', unsafe_allow_html=True)
        station_filter_mode = st.radio("站點模式", ["Station", "ADF"], horizontal=True, label_visibility="collapsed")
        
        st.markdown('<div class="filter-label">地區選擇 ⓘ</div>', unsafe_allow_html=True)
        station_type_filter = st.selectbox(
            "地區", 
            ["全台", "北部", "中部", "南部", "東部", "東北", "東南", "外島"],
            label_visibility="collapsed"
        )
        
        col_wind, col_off = st.columns(2)
        with col_wind:
            show_wind = st.toggle("風力線 ⓘ", value=False)
        with col_off:
            show_offline = st.toggle("顯示離線裝置 ⓘ", value=True)
            
    st.markdown("---")
    if st.button("🔄 更新即時監測資料", use_container_width=True):
        with st.spinner("正在同步全台空氣盒子與氣象資料..."):
            try:
                air_raw = fetch_airbox_data()
                epa_raw = fetch_epa_data()
                parsed = parse_airbox_data(air_raw, epa_raw)
                count = insert_air_stations(parsed)
                forecast_count = sync_station_forecasts(
                    get_air_stations(include_offline=True)
                )
                st.success(
                    f"成功更新 {count} 個測站即時資訊，並寫入 {forecast_count} 筆七日預報資料。"
                )
                if forecast_count == 0:
                    st.warning("七日預報未取得資料，請確認 CWA_API_KEY 與預報 API 狀態。")
                st.rerun()
            except Exception as e:
                st.error(f"更新失敗: {e}")

# ==================== 主地圖繪製與資料整合 ====================
# 地區篩選映射：用戶輸入 -> 數據庫地區值
region_mapping = {
    "全台": None,  # 全部地區
    "北部": "北部地區",
    "中部": "中部地區",
    "南部": "南部地區",
    "東部": "東部地區",
    "東北": "東北部地區",
    "東南": "東南部地區",
    "外島": "外島地區"
}

selected_region = region_mapping.get(station_type_filter)

stations = get_air_stations(
    region=selected_region, 
    include_offline=show_offline
)

# 依 PM2.5 決定標籤顏色 (完美還原 EdiGreen 六級色階)
def get_pm25_color(val):
    if val < 15:
        return "#00E400"  # 綠色 <15
    elif val <= 35:
        return "#FFFF00"  # 黃色 35
    elif val <= 54:
        return "#FF7E00"  # 橘色 54
    elif val <= 150:
        return "#FF0000"  # 紅色 150
    elif val <= 250:
        return "#8F3F97"  # 紫色 250
    else:
        return "#7E0023"  # 褐紅色 >251

# 建立 HTML/SVG 時序趨勢圖表，精準還原圖片中的 Popup 視窗
def create_popup_html(stn, history):
    pm25 = stn.get('pm25', 0.0)
    temp = stn.get('temperature', 0.0)
    hum = stn.get('humidity', 0.0)
    name = stn.get('name', '未命名站點')
    lat = stn.get('lat', 0.0)
    lon = stn.get('lon', 0.0)
    updated = stn.get('updated_at', '')
    
    # 提取時序數據（若無時序則自動生成）
    if not history:
        history = generate_24h_history(pm25, temp, hum, is_aaa2=(stn.get('station_id') == 'AAA2'))
        
    pm_vals = [h['pm25'] for h in history]
    temp_vals = [h['temperature'] for h in history]
    hum_vals = [h['humidity'] for h in history]
    
    # 提取 7 個 4 小時區間的時間標籤 (例如：19, 23, 03, 07, 11, 15, 19)
    tick_indices = [0, 4, 8, 12, 16, 20, 23]
    def extract_hour(h):
        t_str = str(h.get('time') or h.get('record_time') or '00:00')
        return t_str.split(":")[0]
    time_labels = [extract_hour(history[min(idx, len(history)-1)]) for idx in tick_indices]
    
    # ---------------- 1. PM2.5 折線圖 SVG ----------------
    # 繪圖區域寬 288 (x: 28 ~ 316), 高 48 (y: 16 ~ 64)
    max_pm = max(pm_vals) if pm_vals else 0
    top_pm_label = int(math.ceil(max_pm)) if max_pm > 1 else 1
    
    svg_pm_pts = []
    svg_pm_dots = ""
    for idx, p in enumerate(pm_vals):
        x = 28 + idx * (288.0 / max(len(pm_vals)-1, 1))
        # 若 max_pm 為 0 則落在基準底線 y = 60
        y = 60 - (p / max(top_pm_label, 1)) * 44
        svg_pm_pts.append(f"{x:.1f},{y:.1f}")
        svg_pm_dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#00bcd4" />'
        
    pm_polyline = " ".join(svg_pm_pts)
    
    # 時間軸刻度標籤 SVG
    pm_time_labels_svg = ""
    for i, t_lbl in enumerate(time_labels):
        tx = 28 + i * (288.0 / 6)
        pm_time_labels_svg += f'<text x="{tx:.1f}" y="73" font-size="8.5" fill="#757575" text-anchor="middle">{t_lbl}</text>'

    # ---------------- 2. 溫度與濕度雙面積圖 SVG ----------------
    # 溫度刻度：30 ~ 33（或動態包覆範圍）
    t_min = math.floor(min(temp_vals)) if temp_vals else 30
    t_max = math.ceil(max(temp_vals)) if temp_vals else 33
    if t_max - t_min < 3:
        t_max = t_min + 3
    t_step = (t_max - t_min) / 3.0
    t_labels = [int(round(t_max - i * t_step)) for i in range(4)]
    
    # 濕度刻度：40 ~ 70（或動態包覆範圍）
    h_min = int(min(hum_vals) // 10 * 10) if hum_vals else 40
    h_max = int(math.ceil(max(hum_vals) / 10.0) * 10) if hum_vals else 70
    if h_max - h_min < 30:
        h_max = h_min + 30
    h_step = (h_max - h_min) / 3.0
    h_labels = [int(round(h_max - i * h_step)) for i in range(4)]
    
    # 計算面積路徑與點位 (y: 16 ~ 68, 基準底線 y = 68)
    temp_pts = []
    temp_dots = ""
    for idx, t in enumerate(temp_vals):
        x = 28 + idx * (288.0 / max(len(temp_vals)-1, 1))
        y = 68 - ((t - t_min) / max(t_max - t_min, 1)) * 50
        temp_pts.append((x, y))
        temp_dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#00bcd4" />'
        
    hum_pts = []
    hum_dots = ""
    for idx, h in enumerate(hum_vals):
        x = 28 + idx * (288.0 / max(len(hum_vals)-1, 1))
        y = 68 - ((h - h_min) / max(h_max - h_min, 1)) * 50
        hum_pts.append((x, y))
        hum_dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#00bcd4" />'
        
    temp_poly = f"28,68 " + " ".join([f"{x:.1f},{y:.1f}" for x, y in temp_pts]) + f" 316,68"
    hum_poly = f"28,68 " + " ".join([f"{x:.1f},{y:.1f}" for x, y in hum_pts]) + f" 316,68"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; width: 345px; padding: 4px; color: #333;">
        <!-- 標題欄：站點名稱與經緯度 -->
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px;">
            <span style="color: #0090d0; font-size: 16px; font-weight: bold;">{name}</span>
            <span style="color: #0090d0; font-size: 13px; font-weight: 500;">{lat:.3f}°N / {lon:.3f}°E</span>
        </div>
        
        <!-- 即時數值欄 -->
        <div style="font-size: 11.5px; line-height: 1.45; color: #444; margin-bottom: 6px;">
            <div>Pm2.5 : <b>{pm25}</b> µg/m³</div>
            <div>溫度 : <b>{temp:.2f}°C</b>, 濕度 : <b>{hum:.0f}%</b></div>
        </div>
        
        <!-- PM2.5 趨勢圖 -->
        <div style="font-size: 10.5px; color: #666; margin-bottom: 1px;">Pm2.5</div>
        <svg width="340" height="76" style="background: #ffffff; border: 1px solid #ebebeb; border-radius: 3px;">
            <!-- 網格線 -->
            <line x1="28" y1="16" x2="316" y2="16" stroke="#f2f2f2" stroke-width="1" />
            <line x1="28" y1="38" x2="316" y2="38" stroke="#f2f2f2" stroke-width="1" />
            <line x1="28" y1="60" x2="316" y2="60" stroke="#e0e0e0" stroke-width="1" />
            
            <!-- Y 軸標籤 -->
            <text x="18" y="19" font-size="8.5" fill="#757575" text-anchor="middle">{top_pm_label}</text>
            <text x="18" y="63" font-size="8.5" fill="#757575" text-anchor="middle">0</text>
            
            <!-- PM2.5 曲線與資料點 -->
            <polyline fill="none" stroke="#00bcd4" stroke-width="1.6" points="{pm_polyline}" />
            {svg_pm_dots}
            
            <!-- X 軸時間刻度 -->
            {pm_time_labels_svg}
        </svg>
        
        <!-- 溫度與濕度趨勢圖 -->
        <div style="display: flex; justify-content: space-between; font-size: 10.5px; color: #666; margin-top: 5px; margin-bottom: 1px; padding: 0 4px;">
            <span>溫度</span>
            <span style="margin-right: 20px;">濕度</span>
        </div>
        <svg width="340" height="82" style="background: #ffffff; border: 1px solid #ebebeb; border-radius: 3px;">
            <!-- 水平網格線 (4 階) -->
            <line x1="28" y1="16" x2="316" y2="16" stroke="#f0f0f0" stroke-width="1" />
            <line x1="28" y1="33" x2="316" y2="33" stroke="#f0f0f0" stroke-width="1" />
            <line x1="28" y1="50" x2="316" y2="50" stroke="#f0f0f0" stroke-width="1" />
            <line x1="28" y1="68" x2="316" y2="68" stroke="#e0e0e0" stroke-width="1" />
            
            <!-- 左 Y 軸 (溫度) -->
            <text x="16" y="19" font-size="8" fill="#757575" text-anchor="middle">{t_labels[0]}</text>
            <text x="16" y="36" font-size="8" fill="#757575" text-anchor="middle">{t_labels[1]}</text>
            <text x="16" y="53" font-size="8" fill="#757575" text-anchor="middle">{t_labels[2]}</text>
            <text x="16" y="70" font-size="8" fill="#757575" text-anchor="middle">{t_labels[3]}</text>
            
            <!-- 右 Y 軸 (濕度) -->
            <text x="328" y="19" font-size="8" fill="#757575" text-anchor="middle">{h_labels[0]}</text>
            <text x="328" y="36" font-size="8" fill="#757575" text-anchor="middle">{h_labels[1]}</text>
            <text x="328" y="53" font-size="8" fill="#757575" text-anchor="middle">{h_labels[2]}</text>
            <text x="328" y="70" font-size="8" fill="#757575" text-anchor="middle">{h_labels[3]}</text>
            
            <!-- 濕度青藍色面積與數據點 -->
            <polygon points="{hum_poly}" fill="rgba(77, 208, 225, 0.65)" stroke="#00acc1" stroke-width="1" />
            {hum_dots}
            
            <!-- 溫度黃色面積與數據點 -->
            <polygon points="{temp_poly}" fill="rgba(255, 214, 0, 0.65)" stroke="#ffa000" stroke-width="1" />
            {temp_dots}
        </svg>
        
        <!-- 底部更新時間 -->
        <div style="font-size: 9.5px; color: #888; margin-top: 4px; text-align: left;">
            最後更新時間: {updated}
        </div>
    </div>
    """
    return html

# 維持原本底圖網址設定，CARTO_API_KEY 為選用。
load_dotenv()
carto_api_key = os.getenv("CARTO_API_KEY")
if carto_api_key:
    tile_url = f"https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png?key={carto_api_key}"
else:
    tile_url = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"

# 建立 Folium 地圖，鎖定台灣全島
m = folium.Map(
    location=[23.85, 120.95],
    zoom_start=8,
    tiles=None,
    prefer_canvas=True
)

folium.TileLayer(
    tiles=tile_url,
    attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    name='CartoDB Positron',
    subdomains='abcd',
    max_zoom=19
).add_to(m)

# streamlit-folium 的地圖顯示在 iframe 中；主頁面的 Streamlit CSS 無法套用進去。
# 在 Folium 文件本身縮小 attribution，減少遮擋但保留底圖所需的來源資訊。
m.get_root().header.add_child(folium.Element("""
<style>
    .leaflet-control-attribution {
        padding: 2px 5px !important;
        border-radius: 3px 0 0 0;
        background: rgba(255, 255, 255, 0.68) !important;
        color: #64748b !important;
        font-size: 8px !important;
        line-height: 1.2 !important;
    }
    .leaflet-control-attribution a {
        color: #64748b !important;
        text-decoration: none !important;
    }
</style>
"""))

# 統計各類別數量以呈現在右下角圖例
type_counts = {
    "空氣盒子觀測點": 0,
    "環保署觀測站": 0,
    "資料異於周圍環境": 0,
    "機器需檢修": 0,
    "開放資料觀測站": 0
}

# 繪製各測站標記
for stn in stations:
    pm25 = stn['pm25']
    color = get_pm25_color(pm25)
    stype = stn.get('station_type', '空氣盒子觀測點')
    if stype in type_counts:
        type_counts[stype] += 1
        
    history = get_station_history(stn['station_id'])
    
    # 彈出視窗
    popup_content = create_popup_html(stn, history)
    iframe = folium.IFrame(popup_content, width=360, height=295)
    popup = folium.Popup(iframe, max_width=380)
    
    display_num = int(round(pm25))
    text_color = '#333' if color in ['#FFFF00', '#00E400', '#FFD700'] else '#fff'
    
    # 依站點類別採用不同標記圖示
    if stn['station_id'] == 'AAA2':
        # 截圖中的焦點目標 AAA2：紅色精緻定位圖標
        red_pin_html = """
        <div style="position: relative; width: 30px; height: 42px; margin-left: -15px; margin-top: -42px;">
            <svg viewBox="0 0 24 36" width="30" height="42" style="filter: drop-shadow(0 2px 5px rgba(0,0,0,0.45));">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24c0-6.63-5.37-12-12-12z" fill="#e53935" stroke="#ffffff" stroke-width="1.8"/>
                <circle cx="12" cy="12" r="5" fill="#ffffff"/>
                <circle cx="12" cy="12" r="2.8" fill="#e53935"/>
            </svg>
        </div>
        """
        folium.Marker(
            location=[stn['lat'], stn['lon']],
            popup=popup,
            tooltip=f"★ {stn['name']} | PM2.5: {pm25} | 溫: {stn['temperature']}°C 濕: {stn['humidity']}%",
            icon=folium.DivIcon(html=red_pin_html, icon_size=(30, 42), icon_anchor=(15, 42))
        ).add_to(m)
    elif stype == '環保署觀測站':
        # 環保署觀測站：菱形徽章帶 PM2.5 數值
        diamond_html = f"""
        <div style="
            width: 19px; height: 19px;
            background-color: {color};
            border: 1.5px solid white;
            transform: rotate(45deg);
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.35);
        ">
            <div style="
                transform: rotate(-45deg);
                font-size: 9.5px; font-weight: bold;
                color: {text_color};
            ">{display_num}</div>
        </div>
        """
        folium.Marker(
            location=[stn['lat'], stn['lon']],
            popup=popup,
            tooltip=f"🏛️ {stn['name']} (環保署) | PM2.5: {pm25}",
            icon=folium.DivIcon(html=diamond_html, icon_size=(20, 20), icon_anchor=(10, 10))
        ).add_to(m)
    elif stype == '機器需檢修':
        # 離線/需檢修：灰色/警示邊框圓形
        cone_html = f"""
        <div style="
            width: 22px; height: 22px;
            border-radius: 50%;
            background-color: #9e9e9e;
            border: 2px dashed #ff9800;
            display: flex; align-items: center; justify-content: center;
            font-size: 10px; font-weight: bold;
            color: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        ">
            {display_num}
        </div>
        """
        folium.Marker(
            location=[stn['lat'], stn['lon']],
            popup=popup,
            tooltip=f"🚧 {stn['name']} (需檢修) | PM2.5: {pm25}",
            icon=folium.DivIcon(html=cone_html, icon_size=(22, 22), icon_anchor=(11, 11))
        ).add_to(m)
    else:
        # 空氣盒子觀測點與開放觀測站：圓形微粒徽章
        circle_html = f"""
        <div style="
            width: 22px; height: 22px;
            border-radius: 50%;
            background-color: {color};
            border: 1.6px solid white;
            display: flex; align-items: center; justify-content: center;
            font-size: 10px; font-weight: bold;
            color: {text_color};
            box-shadow: 0 1px 3px rgba(0,0,0,0.35);
        ">
            {display_num}
        </div>
        """
        folium.Marker(
            location=[stn['lat'], stn['lon']],
            popup=popup,
            tooltip=f"{stn['name']} | PM2.5: {pm25} | 溫: {stn['temperature']}°C 濕: {stn['humidity']}%",
            icon=folium.DivIcon(html=circle_html, icon_size=(22, 22), icon_anchor=(11, 11))
        ).add_to(m)

# 若啟用風力線，繪製全台及海域動態風向風速流線
if show_wind:
    wind_group = folium.FeatureGroup(name="風力線")
    
    wind_paths = [
        # 台灣海峽強風軸 (強東北風 7~10 m/s)
        ([(25.8, 120.8), (25.0, 120.3), (24.2, 119.8), (23.4, 119.4), (22.5, 119.1)], "東北風 8.5 m/s (5級)"),
        ([(25.6, 121.2), (24.8, 120.6), (24.0, 120.1), (23.1, 119.8), (22.2, 119.5)], "東北風 7.8 m/s (4級)"),
        ([(25.3, 121.5), (24.5, 120.9), (23.8, 120.4), (23.0, 120.1), (22.0, 119.9)], "東北風 6.5 m/s (4級)"),
        ([(25.0, 121.8), (24.3, 121.2), (23.6, 120.7), (22.8, 120.3), (21.9, 120.2)], "北北東風 5.5 m/s (3級)"),
        ([(26.0, 120.2), (25.2, 119.7), (24.4, 119.2), (23.5, 118.8), (22.6, 118.5)], "東北風 9.0 m/s (5級)"),
        ([(25.4, 120.5), (24.6, 120.0), (23.7, 119.6), (22.8, 119.2), (22.0, 118.9)], "東北風 8.0 m/s (4級)"),
        
        # 北部沿海與都會區 (東北風 4~6 m/s)
        ([(25.3, 122.2), (25.1, 121.8), (25.0, 121.4), (24.9, 121.0)], "東北東風 4.8 m/s (3級)"),
        ([(25.4, 121.9), (25.2, 121.5), (25.0, 121.2), (24.8, 120.8)], "東北風 5.2 m/s (3級)"),
        ([(25.2, 121.6), (25.0, 121.3), (24.8, 121.0), (24.6, 120.7)], "東北風 4.5 m/s (3級)"),
        ([(25.0, 121.4), (24.8, 121.1), (24.6, 120.8), (24.4, 120.5)], "東北風 4.0 m/s (3級)"),
        
        # 中部平原 (微風 2~4 m/s)
        ([(24.4, 120.8), (24.1, 120.6), (23.8, 120.4), (23.4, 120.3)], "北北東風 3.2 m/s (2級)"),
        ([(24.2, 120.7), (23.9, 120.5), (23.5, 120.3), (23.1, 120.2)], "偏北風 2.8 m/s (2級)"),
        ([(24.0, 120.6), (23.7, 120.4), (23.3, 120.2), (22.9, 120.2)], "北北西風 2.5 m/s (2級)"),
        
        # 南部與高屏平原 (輕風 2~3 m/s)
        ([(23.4, 120.4), (23.0, 120.3), (22.7, 120.3), (22.4, 120.3)], "西北風 2.2 m/s (2級)"),
        ([(23.2, 120.3), (22.8, 120.2), (22.5, 120.2), (22.2, 120.3)], "偏北風 2.6 m/s (2級)"),
        ([(22.9, 120.3), (22.6, 120.3), (22.3, 120.4), (22.0, 120.5)], "西北西風 3.0 m/s (2級)"),
        
        # 恆春半島與巴士海峽 (強勁落山風 8~12 m/s)
        ([(22.4, 120.7), (22.1, 120.6), (21.8, 120.5), (21.5, 120.4)], "東北風 10.5 m/s (5級)"),
        ([(22.2, 120.8), (21.9, 120.7), (21.6, 120.6), (21.3, 120.5)], "東北東風 11.2 m/s (6級)"),
        ([(22.0, 120.9), (21.7, 120.8), (21.4, 120.7), (21.1, 120.6)], "東風 9.8 m/s (5級)"),
        
        # 東部沿海與太平洋 (東北季風 5~8 m/s)
        ([(24.8, 122.2), (24.2, 122.0), (23.6, 121.8), (23.0, 121.6), (22.4, 121.4)], "東北風 6.8 m/s (4級)"),
        ([(24.5, 122.0), (23.9, 121.8), (23.3, 121.6), (22.7, 121.4), (22.1, 121.2)], "東北風 7.2 m/s (4級)"),
        ([(24.2, 121.8), (23.7, 121.6), (23.2, 121.4), (22.6, 121.2), (22.0, 121.1)], "北北東風 5.8 m/s (3級)"),
        ([(23.8, 121.6), (23.3, 121.4), (22.8, 121.3), (22.3, 121.1), (21.8, 121.0)], "東北風 6.2 m/s (4級)")
    ]
    
    for pts, info in wind_paths:
        folium.PolyLine(
            locations=pts,
            color="#00acc1",
            weight=2.6,
            opacity=0.8,
            dash_array="6, 9",
            tooltip=f"🍃 風向風速: {info}"
        ).add_to(wind_group)
        
        mid_idx = len(pts) // 2
        p1 = pts[mid_idx]
        p2 = pts[mid_idx + 1] if mid_idx + 1 < len(pts) else pts[mid_idx]
        dlat = p2[0] - p1[0]
        dlon = p2[1] - p1[1]
        angle = math.degrees(math.atan2(dlon, dlat))
        
        arrow_html = f"""
        <div style="
            transform: rotate({angle:.0f}deg);
            color: #00838f;
            font-size: 14px;
            font-weight: 900;
            line-height: 1;
            text-shadow: 0 0 3px rgba(255,255,255,0.9);
            pointer-events: none;
        ">
            ➤
        </div>
        """
        folium.Marker(
            location=[(p1[0] + p2[0])/2, (p1[1] + p2[1])/2],
            icon=folium.DivIcon(html=arrow_html, icon_size=(16, 16), icon_anchor=(8, 8))
        ).add_to(wind_group)
        
    wind_group.add_to(m)

# 顯示滿版台灣地圖；點擊測站標記時，回傳標記座標與 tooltip。
map_result = st_folium(
    m,
    width="100%",
    height=660,
    key="station_map",
    returned_objects=[
        "last_object_clicked",
        "last_object_clicked_count",
        "last_object_clicked_tooltip",
    ],
)

last_click_count = map_result.get("last_object_clicked_count")
last_clicked = map_result.get("last_object_clicked")
if (
    last_click_count is not None
    and last_click_count != st.session_state.get("_last_station_map_click_count")
):
    st.session_state["_last_station_map_click_count"] = last_click_count
    if last_clicked and stations:
        clicked_lat = last_clicked.get("lat")
        clicked_lon = last_clicked.get("lng", last_clicked.get("lon"))
        if clicked_lat is not None and clicked_lon is not None:
            def get_coordinate_error(station):
                return (
                    (float(station["lat"]) - float(clicked_lat)) ** 2
                    + (float(station["lon"]) - float(clicked_lon)) ** 2
                ) ** 0.5

            nearest_error = min(get_coordinate_error(station) for station in stations)
            tooltip_text = str(map_result.get("last_object_clicked_tooltip") or "")
            nearest_candidates = [
                station for station in stations
                if get_coordinate_error(station) <= nearest_error + 1e-8
            ]
            nearest_station = next(
                (station for station in nearest_candidates if station["name"] in tooltip_text),
                nearest_candidates[0],
            )
            coordinate_error = get_coordinate_error(nearest_station)
            if coordinate_error <= 0.002:
                st.session_state["_selected_station_id"] = str(nearest_station["station_id"])

# 地圖底部雙側圖例列（左下角 PM2.5 色階、右下角站點類別圖例）
col_leg_left, col_leg_right = st.columns([1.1, 1.2])

with col_leg_left:
    st.markdown("""
    <div style="display: flex; align-items: center; background: #ffffff; padding: 6px 12px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.12); font-size: 12px; gap: 3px; width: fit-content;">
        <span style="background: #00E400; color: white; padding: 3px 9px; font-weight: bold; border-radius: 2px;">&lt;15</span>
        <span style="background: #FFFF00; color: #333; padding: 3px 9px; font-weight: bold; border-radius: 2px;">35</span>
        <span style="background: #FF7E00; color: white; padding: 3px 9px; font-weight: bold; border-radius: 2px;">54</span>
        <span style="background: #FF0000; color: white; padding: 3px 9px; font-weight: bold; border-radius: 2px;">150</span>
        <span style="background: #8F3F97; color: white; padding: 3px 9px; font-weight: bold; border-radius: 2px;">250</span>
        <span style="background: #7E0023; color: white; padding: 3px 9px; font-weight: bold; border-radius: 2px;">&gt;251</span>
        <span style="color: #666; font-size: 11px; margin-left: 6px; font-weight: 500;">(µg/m³)</span>
    </div>
    """, unsafe_allow_html=True)

with col_leg_right:
    c_ab = type_counts.get("空氣盒子觀測點", 0)
    c_epa = type_counts.get("環保署觀測站", 0)
    c_diff = type_counts.get("資料異於周圍環境", 0)
    c_rep = type_counts.get("機器需檢修", 0)
    c_open = type_counts.get("開放資料觀測站", 0)
    
    st.markdown(f"""
    <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 14px; background: #ffffff; padding: 6px 14px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.12); font-size: 11.5px; align-items: center;">
        <div style="display: flex; align-items: center; gap: 4px;">
            <span style="color: #00bcd4; font-size: 14px;">⬡</span>
            <span style="background: #25a374; color: white; border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: bold;">{c_ab}</span>
            <span>空氣盒子觀測點</span>
        </div>
        <div style="display: flex; align-items: center; gap: 4px;">
            <span style="color: #009688; font-size: 14px;">🏛️</span>
            <span style="background: #25a374; color: white; border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: bold;">{c_epa}</span>
            <span>環保署觀測站</span>
        </div>
        <div style="display: flex; align-items: center; gap: 4px;">
            <span style="color: #795548; font-size: 14px;">🏠</span>
            <span style="background: #25a374; color: white; border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: bold;">{c_diff}</span>
            <span>資料異於周圍環境</span>
        </div>
        <div style="display: flex; align-items: center; gap: 4px;">
            <span style="color: #ff9800; font-size: 14px;">🚧</span>
            <span style="background: #25a374; color: white; border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: bold;">{c_rep}</span>
            <span>機器需檢修</span>
        </div>
        <div style="display: flex; align-items: center; gap: 4px;">
            <span style="color: #03a9f4; font-size: 14px;">🚢</span>
            <span style="background: #25a374; color: white; border-radius: 3px; padding: 1px 5px; font-size: 10px; font-weight: bold;">{c_open}</span>
            <span>開放資料觀測站</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 站點快速檢視展開面板
with st.expander("📊 站點即時詳細指標、24 小時時序與未來 7 日天氣", expanded=True):
    selected_station_id = st.session_state.get("_selected_station_id")
    selected_stn = next(
        (station for station in stations if str(station["station_id"]) == selected_station_id),
        stations[0] if stations else None,
    )
    if selected_stn:
        st.session_state["_selected_station_id"] = str(selected_stn["station_id"])
        st.caption("點擊地圖上的站點標記，即可切換此處顯示的站點資料。")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("站點名稱", selected_stn['name'], selected_stn.get('station_type', '觀測點'))
        col_m2.metric("PM2.5 濃度", f"{selected_stn['pm25']} µg/m³")
        col_m3.metric("即時溫度", f"{selected_stn['temperature']:.2f} °C")
        col_m4.metric("相對濕度", f"{selected_stn['humidity']:.0f} %")
        
        hist = get_station_history(selected_stn['station_id'])
        if hist:
            df_hist = pd.DataFrame(hist)
            t_col = 'time' if 'time' in df_hist.columns else 'record_time'
            df_hist['hour'] = df_hist[t_col].apply(lambda x: str(x).split(":")[0] if ":" in str(x) else str(x))
            
            c_ch1, c_ch2 = st.columns(2)
            with c_ch1:
                st.markdown("**Pm2.5 過去 24 小時時序**")
                st.line_chart(df_hist.set_index('hour')[['pm25']], color="#00bcd4")
            with c_ch2:
                st.markdown("**溫度 (°C) 與 濕度 (%) 時序**")
                st.area_chart(df_hist.set_index('hour')[['temperature', 'humidity']])

        st.markdown("#### 未來 7 日天氣預報")
        forecasts = get_7day_forecasts(selected_stn['station_id'])
        if forecasts:
            forecast_df = pd.DataFrame(forecasts).rename(columns={
                'forecast_date': '日期',
                'weekday': '星期',
                'weather': '天氣',
                'min_temp': '最低溫 (°C)',
                'max_temp': '最高溫 (°C)',
                'humidity': '相對濕度 (%)',
                'pop': '降雨機率 (%)',
                'description': '天氣描述',
            })
            for column in ['最低溫 (°C)', '最高溫 (°C)']:
                forecast_df[column] = forecast_df[column].replace(-999, '—')
            for column in ['相對濕度 (%)', '降雨機率 (%)']:
                forecast_df[column] = forecast_df[column].replace(-1, '—')
            st.dataframe(
                forecast_df[[
                    '日期', '星期', '天氣', '最低溫 (°C)', '最高溫 (°C)',
                    '相對濕度 (%)', '降雨機率 (%)', '天氣描述',
                ]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("資料庫目前沒有此站點的七日預報，請按側邊欄「更新即時監測資料」同步。")
                
        st.caption(f"座標: `{selected_stn['lat']:.3f}°N / {selected_stn['lon']:.3f}°E` ｜ 最後更新時間: {selected_stn['updated_at']}")
    else:
        st.info("目前篩選條件沒有可顯示的測站。")

if is_initial_page_load:
    loading_overlay.empty()
    st.session_state["_initial_page_loaded"] = True

