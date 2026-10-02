import streamlit as st
import pandas as pd
import folium
import json
import math
from streamlit_folium import st_folium
import os

# Manually load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")
                except ValueError:
                    pass

try:
    from src import database
except ImportError:
    st.error("Error: Could not import database module. Please ensure 'src/database.py' exists.")
    st.stop()

# Configure the Streamlit page
st.set_page_config(
    page_title="台灣即時氣象地圖",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS — full-bleed dark layout
st.markdown("""
<style>
    .block-container {
        padding-top: 0.3rem;
        padding-bottom: 0rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    footer { visibility: hidden; }
    .stApp { background: #0b1120; }
    /* Make sidebar toggle button more visible */
    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="stSidebarExpandButton"] {
        background: rgba(56, 189, 248, 0.85) !important;
        border-radius: 8px !important;
        color: white !important;
        width: 40px !important;
        height: 40px !important;
    }
</style>
""", unsafe_allow_html=True)

# Mapping regions to approximate coordinates
COORDINATES = {
    "臺北市": [25.032969, 121.565418], "新北市": [25.011982, 121.464670],
    "桃園市": [24.993628, 121.300979], "臺中市": [24.147735, 120.673648],
    "臺南市": [22.999728, 120.227027], "高雄市": [22.627278, 120.301435],
    "基隆市": [25.127603, 121.739183], "新竹縣": [24.838322, 121.017725],
    "新竹市": [24.813828, 120.967479], "苗栗縣": [24.560158, 120.821427],
    "彰化縣": [24.051796, 120.516135], "南投縣": [23.960823, 120.971864],
    "雲林縣": [23.709203, 120.431337], "嘉義縣": [23.451842, 120.255461],
    "嘉義市": [23.480075, 120.449111], "屏東縣": [22.551976, 120.548760],
    "宜蘭縣": [24.702107, 121.737750], "花蓮縣": [23.976991, 121.604399],
    "臺東縣": [22.768499, 121.144415], "澎湖縣": [23.571089, 119.564177],
    "金門縣": [24.432715, 118.318465], "連江縣": [26.155581, 119.932970],
}

# Temperature color scale (same nice one from before)
TEMP_COLORS = ["#2c7bb6", "#5aa2cf", "#abd9e9", "#7fcdbb", "#d9ef8b", "#fee08b", "#fdae61", "#f46d43", "#d73027"]
TEMP_VMIN, TEMP_VMAX = 5, 36

def interpolate_color(val, colors=TEMP_COLORS, vmin=TEMP_VMIN, vmax=TEMP_VMAX):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "#333333"
    ratio = max(0.0, min(1.0, (val - vmin) / (vmax - vmin)))
    idx = ratio * (len(colors) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(colors) - 1)
    t = idx - lo
    c_lo = colors[lo].lstrip('#')
    c_hi = colors[hi].lstrip('#')
    r = int(int(c_lo[0:2], 16) * (1 - t) + int(c_hi[0:2], 16) * t)
    g = int(int(c_lo[2:4], 16) * (1 - t) + int(c_hi[2:4], 16) * t)
    b = int(int(c_lo[4:6], 16) * (1 - t) + int(c_hi[4:6], 16) * t)
    return f"#{r:02x}{g:02x}{b:02x}"

# Data kind config: chart settings + map choropleth settings
DATA_KINDS = {
    "🌡️ 氣溫 (°C)": {
        "cols": ["minT", "maxT"], "colors": ["#0055ff", "#ff5500"], "ylabel": "°C",
        "map_col": "Temperature",
        "map_colors": ["#2c7bb6", "#5aa2cf", "#abd9e9", "#7fcdbb", "#d9ef8b", "#fee08b", "#fdae61", "#f46d43", "#d73027"],
        "map_vmin": 5, "map_vmax": 36,
        "map_ticks": [5, 10, 15, 20, 24, 28, 32, 36],
        "map_label": lambda row: f"{row.get('Temperature', 0):.0f}°",
        "legend_title": "氣溫 (°C)",
    },
    "🌧️ 雨量 (mm)": {
        "cols": ["rainfall"], "colors": ["#2171b5"], "ylabel": "mm",
        "map_col": "rainfall",
        "map_colors": ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
        "map_vmin": 0, "map_vmax": 80,
        "map_ticks": [0, 1, 10, 30, 50, 80],
        "map_label": lambda row: f"{row.get('rainfall', 0):.0f}mm",
        "legend_title": "雨量 (mm)",
    },
    "💧 濕度 (%)": {
        "cols": ["humidity"], "colors": ["#238443"], "ylabel": "%",
        "map_col": "humidity",
        "map_colors": ["#ffffd9", "#c2e699", "#78c679", "#238443", "#004529"],
        "map_vmin": 30, "map_vmax": 100,
        "map_ticks": [30, 50, 60, 70, 80, 90, 100],
        "map_label": lambda row: f"{row.get('humidity', 0):.0f}%",
        "legend_title": "濕度 (%)",
    },
    "💨 風速 (m/s)": {
        "cols": ["wind_speed"], "colors": ["#7b3294"], "ylabel": "m/s",
        "map_col": "wind_speed",
        "map_colors": ["#f2f0f7", "#cbc9e2", "#9e9ac8", "#756bb1", "#54278f"],
        "map_vmin": 0, "map_vmax": 15,
        "map_ticks": [0, 2, 5, 8, 10, 15],
        "map_label": lambda row: f"{row.get('wind_speed', 0):.1f}",
        "legend_title": "風速 (m/s)",
    },
    "🌡️ 體感溫度 (°C)": {
        "cols": ["temp_c"], "colors": ["#d73027"], "ylabel": "°C",
        "map_col": "temp_c",
        "map_colors": ["#313695", "#4575b4", "#74add1", "#abd9e9", "#fee090", "#fdae61", "#f46d43", "#d73027", "#a50026"],
        "map_vmin": 5, "map_vmax": 40,
        "map_ticks": [5, 10, 15, 20, 25, 30, 35, 40],
        "map_label": lambda row: f"{row.get('temp_c', 0):.0f}°",
        "legend_title": "體感溫度 (°C)",
    },
    "📊 氣壓 (hPa)": {
        "cols": ["pressure"], "colors": ["#636363"], "ylabel": "hPa",
        "map_col": "pressure",
        "map_colors": ["#fee5d9", "#fcbba1", "#fc9272", "#fb6a4a", "#cb181d"],
        "map_vmin": 990, "map_vmax": 1030,
        "map_ticks": [990, 1000, 1010, 1020, 1030],
        "map_label": lambda row: f"{row.get('pressure', 0):.0f}",
        "legend_title": "氣壓 (hPa)",
    },
}

# Load regions from SQLite database
try:
    regions = database.get_all_regions()
except Exception as e:
    st.error(f"Database Connection Error: {e}")
    st.stop()

if not regions:
    st.warning("The database is currently empty. Please run `fetch_weather.py` and `parse_weather.py`.")
    st.stop()

# ---- Cached data loaders (prevent re-querying on every interaction) ----
@st.cache_data(ttl=300)  # refresh every 5 minutes
def load_latest_map_data():
    conn = database.get_connection()
    map_query = """
    SELECT * 
    FROM TemperatureForecasts 
    WHERE dataDate = (SELECT MAX(dataDate) FROM TemperatureForecasts)
    """
    df = pd.read_sql_query(map_query, conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def load_region_history(region_name):
    return database.get_forecast_by_region(region_name)

@st.cache_data(ttl=3600)
def load_geojson():
    with open("data/taiwan.geojson", "r", encoding="utf-8") as f:
        return json.load(f)

# ==================== LAYOUT ====================
if "active_region" not in st.session_state:
    st.session_state.active_region = None
if "data_kind" not in st.session_state:
    st.session_state.data_kind = list(DATA_KINDS.keys())[0]

# Right sidebar controls
with st.sidebar:
    st.markdown("### ⛅ 台灣即時氣象地圖")
    st.markdown("---")
    
    # Map style
    st.markdown("##### 🗺️ 底圖模式")
    base_map = st.radio("底圖", ["深色", "淺色", "街道圖"], index=0, horizontal=True, label_visibility="collapsed")
    
    st.markdown("---")
    
    # Region selector
    st.markdown("##### 📍 選擇地區")
    selected_region = st.selectbox("地區", [""] + list(COORDINATES.keys()), label_visibility="collapsed")
    if selected_region:
        st.session_state.active_region = selected_region

# ==================== MAIN CONTENT ====================
try:
    # Get the latest data (cached, refreshes every 5 min)
    df_map = load_latest_map_data()

    if not df_map.empty:
        # Prepare map data
        geo_mapping = {
            '臺北市': '台北市', '新北市': '台北縣', '桃園市': '桃園縣', '臺中市': '台中市',
            '臺南市': '台南市', '高雄市': '高雄市', '基隆市': '基隆市', '新竹縣': '新竹縣',
            '新竹市': '新竹市', '苗栗縣': '苗栗縣', '彰化縣': '彰化縣', '南投縣': '南投縣',
            '雲林縣': '雲林縣', '嘉義縣': '嘉義縣', '嘉義市': '嘉義市', '屏東縣': '屏東縣',
            '宜蘭縣': '宜蘭縣', '花蓮縣': '花蓮縣', '臺東縣': '台東縣', '澎湖縣': '澎湖縣',
            '金門縣': '金門縣', '連江縣': '連江縣'
        }
        df_map['matchName'] = df_map['regionName'].map(geo_mapping)
        df_map['Temperature'] = (df_map['minT'] + df_map['maxT']) / 2

        # Load GeoJSON (cached)
        geojson_data = load_geojson()

        # Build value lookup for choropleth
        value_lookup = {}
        for _, row in df_map.iterrows():
            mn = row.get("matchName")
            if mn and pd.notna(row.get("Temperature")):
                value_lookup[mn] = row["Temperature"]

        def style_function(feature):
            county = feature["properties"]["COUNTYNAME"]
            val = value_lookup.get(county)
            color = interpolate_color(val) if val is not None else "#333333"
            return {
                "fillColor": color,
                "color": "rgba(255,255,255,0.3)",
                "weight": 1,
                "fillOpacity": 0.65,
            }

        # Base tile
        map_api_key = os.getenv("MAP_API_KEY", "")
        if base_map == "深色":
            tile_url = f"https://{{s}}.basemaps.cartocdn.com/rastertiles/dark_all/{{z}}/{{x}}/{{y}}.png?key={map_api_key}" if map_api_key else "CartoDB dark_matter"
            tile_attr = "Map data © CARTO" if map_api_key else ""
        elif base_map == "淺色":
            tile_url = f"https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}.png?key={map_api_key}" if map_api_key else "CartoDB positron"
            tile_attr = "Map data © CARTO" if map_api_key else ""
        else:
            tile_url = "OpenStreetMap"
            tile_attr = ""

        m = folium.Map(location=[23.6978, 120.9605], zoom_start=7.5, tiles=tile_url, attr=tile_attr)

        # Only show choropleth + labels when a region is selected
        has_active = st.session_state.active_region is not None
        kind_cfg = DATA_KINDS[st.session_state.data_kind]

        if has_active:
            # Build value lookup for the SELECTED data kind
            map_col_name = kind_cfg["map_col"]
            value_lookup = {}
            for _, row in df_map.iterrows():
                mn = row.get("matchName")
                val = row.get(map_col_name)
                if mn and pd.notna(val):
                    value_lookup[mn] = val

            map_colors = kind_cfg["map_colors"]
            map_vmin = kind_cfg["map_vmin"]
            map_vmax = kind_cfg["map_vmax"]

            def style_function(feature):
                county = feature["properties"]["COUNTYNAME"]
                val = value_lookup.get(county)
                color = interpolate_color(val, map_colors, map_vmin, map_vmax) if val is not None else "#333333"
                return {
                    "fillColor": color,
                    "color": "rgba(255,255,255,0.3)",
                    "weight": 1,
                    "fillOpacity": 0.65,
                }

            # Choropleth layer
            folium.GeoJson(
                geojson_data,
                style_function=style_function,
                tooltip=folium.GeoJsonTooltip(fields=["COUNTYNAME"], aliases=[""], style="font-size:13px; font-weight:bold;"),
            ).add_to(m)

            # Value labels on each region for the selected data kind
            label_fn = kind_cfg["map_label"]
            for _, row in df_map.iterrows():
                region = row["regionName"]
                coords = COORDINATES.get(region)
                val = row.get(map_col_name)
                if coords and pd.notna(val):
                    label_text = label_fn(row)
                    # Pick a contrasting label color from the scale
                    label_hex = interpolate_color(val, map_colors, map_vmin, map_vmax)

                    icon_html = f'''
                    <div style="
                        font-size: 13px; font-weight: bold; color: {label_hex};
                        text-shadow: 0 0 5px rgba(0,0,0,0.9), 0 0 3px rgba(0,0,0,0.9), 0 0 8px rgba(0,0,0,0.7);
                        white-space: nowrap; pointer-events: auto;
                    ">{label_text}</div>
                    '''

                    folium.Marker(
                        location=coords,
                        icon=folium.DivIcon(html=icon_html, icon_size=(60, 20), icon_anchor=(30, 10)),
                        tooltip=region,
                    ).add_to(m)
        else:
            # Clean map: just add subtle markers for click detection
            for _, row in df_map.iterrows():
                region = row["regionName"]
                coords = COORDINATES.get(region)
                if coords:
                    folium.CircleMarker(
                        location=coords,
                        radius=6,
                        color="rgba(255,255,255,0.5)",
                        weight=1,
                        fill=True,
                        fill_color="rgba(56,189,248,0.6)",
                        fill_opacity=0.6,
                        tooltip=region,
                    ).add_to(m)

        # Layout: map full-width or map + detail panel
        if has_active:
            map_col, detail_col = st.columns([3, 2])
        else:
            map_col, detail_col = st.columns([1, 0.001])

        with map_col:
            map_data = st_folium(m, width='stretch', height=850, returned_objects=["last_object_clicked_tooltip"])

            # Update active region from map click (only if actually changed)
            if map_data and map_data.get("last_object_clicked_tooltip"):
                clicked = map_data["last_object_clicked_tooltip"]
                if clicked != st.session_state.active_region:
                    st.session_state.active_region = clicked
                    st.rerun()

        # ==================== RIGHT DETAIL PANEL ====================
        active = st.session_state.active_region
        if active and has_active:
            with detail_col:
                # Header
                st.markdown(f"### 📍 {active}")

                # Current summary from latest data
                region_latest = df_map[df_map["regionName"] == active]
                if not region_latest.empty:
                    r = region_latest.iloc[0]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("🌡️ 氣溫", f"{r['minT']}–{r['maxT']}°C")
                    c2.metric("🌧️ 雨量", f"{r.get('rainfall', '—')} mm")
                    c3.metric("💧 濕度", f"{r.get('humidity', '—')}%")
                    c4, c5, c6 = st.columns(3)
                    c4.metric("💨 風速", f"{r.get('wind_speed', '—')} m/s")
                    c5.metric("📊 氣壓", f"{r.get('pressure', '—')} hPa")
                    c6.metric("🌡️ 體感", f"{r.get('temp_c', '—')}°C")

                st.markdown("---")

                # Data kind selector for the chart AND map
                data_kind = st.selectbox(
                    "選擇資料類型",
                    list(DATA_KINDS.keys()),
                    index=list(DATA_KINDS.keys()).index(st.session_state.data_kind),
                )
                # If data kind changed, update and rerun to re-color the map
                if data_kind != st.session_state.data_kind:
                    st.session_state.data_kind = data_kind
                    st.rerun()

                kind_cfg = DATA_KINDS[data_kind]

                # Get historical data for this region (cached)
                df_history = load_region_history(active)

                if not df_history.empty:
                    df_history["dataDate"] = pd.to_datetime(df_history["dataDate"])
                    df_history = df_history.sort_values("dataDate").tail(7)

                    # Prepare chart data
                    chart_cols = kind_cfg["cols"]
                    available_cols = [c for c in chart_cols if c in df_history.columns]

                    if available_cols:
                        df_chart = df_history.set_index("dataDate")[available_cols].dropna(how="all")

                        if not df_chart.empty:
                            # Rename columns for display
                            rename_map = {
                                "minT": "最低溫", "maxT": "最高溫",
                                "rainfall": "雨量", "humidity": "濕度",
                                "wind_speed": "風速", "temp_c": "體感溫度",
                                "pressure": "氣壓"
                            }
                            df_chart = df_chart.rename(columns=rename_map)
                            display_colors = kind_cfg["colors"][:len(df_chart.columns)]

                            st.line_chart(df_chart, color=display_colors, height=350)

                            if len(df_chart) == 1:
                                st.caption("⚠️ 目前僅有 1 天的資料，更多天數的資料會隨每日抓取自動累積。")
                        else:
                            st.info("此類型暫無資料。")
                    else:
                        st.info("此類型暫無資料。")
                else:
                    st.info(f"找不到 {active} 的歷史資料。")

                # Close button
                if st.button("✕ 關閉面板", use_container_width=True):
                    st.session_state.active_region = None
                    st.rerun()

        # Bottom legend bar (only when choropleth is shown, matches selected data kind)
        if has_active:
            ticks = kind_cfg["map_ticks"]
            colors_css = ", ".join(kind_cfg["map_colors"])
            tick_labels = "".join(
                f'<span style="flex:1; text-align:center; font-size:12px; color:#ddd; font-weight:600;">{t}</span>'
                for t in ticks
            )
            legend_html = f'''
            <div style="
                background: rgba(15, 23, 42, 0.92);
                border-radius: 12px;
                padding: 14px 24px 10px;
                margin: 8px auto;
                max-width: 600px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.5);
                border: 1px solid rgba(255,255,255,0.1);
            ">
                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="font-size:13px; font-weight:700; color:#e2e8f0; white-space:nowrap;">{kind_cfg["legend_title"]}</span>
                    <div style="flex:1;">
                        <div style="
                            height: 14px;
                            border-radius: 7px;
                            background: linear-gradient(to right, {colors_css});
                            border: 1px solid rgba(255,255,255,0.2);
                        "></div>
                        <div style="display:flex; justify-content:space-between; margin-top:4px;">
                            {tick_labels}
                        </div>
                    </div>
                </div>
            </div>
            '''
            st.markdown(legend_html, unsafe_allow_html=True)

    else:
        st.info("Not enough data to generate the map.")

except Exception as e:
    st.error(f"Error rendering map: {e}")
