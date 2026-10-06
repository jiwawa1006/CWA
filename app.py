import json
import os
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from branca.element import Element
from streamlit_folium import st_folium

# Load settings from the project-root .env file.
APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")

st.set_page_config(
    page_title="台灣即時氣象地圖",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    /* ── Hide Streamlit chrome (header / toolbar / footer) ── */
    #MainMenu,
    header[data-testid="stHeader"],
    footer,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    /* ── Remove all page padding so map is edge-to-edge ── */
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"] {
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    .block-container {
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
    div.st-key-map_controls {
        position: absolute;
        top: 1rem;
        left: 1rem;
        z-index: 1000;
        width: 330px;
        padding: 0.8rem;
        background: rgba(15, 23, 42, 0.97) !important;
        border: 1px solid #475569;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
        /* zero-height so it doesn't push the map down */
        height: 0;
        overflow: visible;
    }

    div.st-key-map_controls,
    div.st-key-map_controls p,
    div.st-key-map_controls label,
    div.st-key-map_controls h3 {
        color: #f8fafc !important;
    }

    div.st-key-map_controls [data-baseweb="select"] > div {
        background: #1e293b;
        color: #f8fafc;
        border-color: #64748b;
    }

    /* Region details overlay – right side of the map */
    div.st-key-region_details {
        position: absolute;
        top: 2rem;
        right: 2rem;
        z-index: 1000;
        width: 340px;
        max-height: calc(100vh - 5rem);
        overflow-y: auto;
        padding: 0;
        background: transparent !important;
        border: none;
        box-shadow: none;
        /* zero-height so it doesn't push the map down */
        height: 0;
        overflow: visible;
        scrollbar-width: thin;
    }

    /* The inner border box lives on the child div, not the wrapper */
    div.st-key-region_details > div {
        padding: 0.85rem 1rem;
        background: rgba(15, 23, 42, 0.97) !important;
        border: 1px solid #475569;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
        max-height: calc(100vh - 5rem);
        overflow-y: auto;
        scrollbar-width: thin;
    }

    div.st-key-region_details,
    div.st-key-region_details p,
    div.st-key-region_details label,
    div.st-key-region_details h2,
    div.st-key-region_details h3,
    div.st-key-region_details caption,
    div.st-key-region_details [data-testid="stMetricValue"],
    div.st-key-region_details [data-testid="stMetricLabel"] {
        color: #f8fafc !important;
    }

    div.st-key-region_details hr {
        border-color: #475569 !important;
    }

    div.st-key-region_details [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 8px;
        padding: 6px 8px;
    }
</style>
""", unsafe_allow_html=True)

try:
    from src import database
    from src.fetch_weather import fetch_weather_data
    from src.parse_weather import parse_weather_data
except ImportError as e:
    st.error(f"無法載入資料庫模組：{e}")
    st.stop()


def _bootstrap_db():
    """Initialize the DB and fetch data from CWA if the table is empty."""
    database.init_db()
    if database.is_empty():
        with st.spinner("首次啟動：正在從 CWA 取得即時氣象資料，請稍候…"):
            ok = fetch_weather_data()
            if not ok:
                st.error(
                    "無法從中央氣象署 API 取得資料。"
                    "請確認 CWA_API_KEY 已在 Streamlit Secrets 中設定。"
                )
                st.stop()
            df = parse_weather_data()
            if df is None or df.empty:
                st.error("資料解析失敗，請檢查 API 回傳內容。")
                st.stop()
            database.insert_observations(df)


_bootstrap_db()


# Approximate county/city centers, used to place value labels.
COORDINATES = {
    "臺北市": [25.032969, 121.565418],
    "新北市": [25.011982, 121.464670],
    "桃園市": [24.993628, 121.300979],
    "臺中市": [24.147735, 120.673648],
    "臺南市": [22.999728, 120.227027],
    "高雄市": [22.627278, 120.301435],
    "基隆市": [25.127603, 121.739183],
    "新竹縣": [24.838322, 121.017725],
    "新竹市": [24.813828, 120.967479],
    "苗栗縣": [24.560158, 120.821427],
    "彰化縣": [24.051796, 120.516135],
    "南投縣": [23.960823, 120.971864],
    "雲林縣": [23.709203, 120.431337],
    "嘉義縣": [23.451842, 120.255461],
    "嘉義市": [23.480075, 120.449111],
    "屏東縣": [22.551976, 120.548760],
    "宜蘭縣": [24.702107, 121.737750],
    "花蓮縣": [23.976991, 121.604399],
    "臺東縣": [22.768499, 121.144415],
    "澎湖縣": [23.571089, 119.564177],
    "金門縣": [24.432715, 118.318465],
    "連江縣": [26.155581, 119.932970],
}

# The GeoJSON county names differ slightly from CWA's names.
GEO_MAPPING = {
    "臺北市": "台北市",
    "新北市": "台北縣",
    "桃園市": "桃園縣",
    "臺中市": "台中市",
    "臺南市": "台南市",
    "高雄市": "高雄市",
    "基隆市": "基隆市",
    "新竹縣": "新竹縣",
    "新竹市": "新竹市",
    "苗栗縣": "苗栗縣",
    "彰化縣": "彰化縣",
    "南投縣": "南投縣",
    "雲林縣": "雲林縣",
    "嘉義縣": "嘉義縣",
    "嘉義市": "嘉義市",
    "屏東縣": "屏東縣",
    "宜蘭縣": "宜蘭縣",
    "花蓮縣": "花蓮縣",
    "臺東縣": "台東縣",
    "澎湖縣": "澎湖縣",
    "金門縣": "金門縣",
    "連江縣": "連江縣",
}

GEO_TO_REGION = {geo_name: region for region, geo_name in GEO_MAPPING.items()}

MISSING_COLOR = "#cbd5e1"

WEATHER_ELEMENTS = {
    "🌡️ 氣溫 (°C)": {
        "chart_cols": ["temp_min", "temp_max"],
        "chart_names": ["今日最低溫", "今日最高溫"],
        "chart_colors": ["#2563eb", "#ea580c"],
        "map_col": "temp_c",
        "map_colors": [
            "#2c7bb6", "#5aa2cf", "#abd9e9", "#7fcdbb", "#d9ef8b",
            "#fee08b", "#fdae61", "#f46d43", "#d73027",
        ],
        "map_vmin": 0,
        "map_vmax": 40,
        "map_ticks": [0, 5, 10, 15, 20, 25, 30, 35, 40],
        "format": lambda value: f"{value:.0f}°",
        "legend_title": "氣溫 (°C)",
    },
    "🌧️ 降雨量 (mm)": {
        "chart_cols": ["rainfall"],
        "chart_names": ["降雨量"],
        "chart_colors": ["#2171b5"],
        "map_col": "rainfall",
        "map_colors": ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
        "map_vmin": 0,
        "map_vmax": 50,
        "map_ticks": [0, 1, 5, 10, 20, 50],
        "format": lambda value: f"{value:.1f} mm",
        "legend_title": "降雨量 (mm)",
    },
    "💧 濕度 (%)": {
        "chart_cols": ["humidity"],
        "chart_names": ["相對濕度"],
        "chart_colors": ["#238443"],
        "map_col": "humidity",
        "map_colors": ["#ffffd9", "#c2e699", "#78c679", "#238443", "#004529"],
        "map_vmin": 0,
        "map_vmax": 100,
        "map_ticks": [0, 20, 40, 60, 80, 100],
        "format": lambda value: f"{value:.0f}%",
        "legend_title": "相對濕度 (%)",
    },
    "💨 風速 (m/s)": {
        "chart_cols": ["wind_speed"],
        "chart_names": ["風速"],
        "chart_colors": ["#7b3294"],
        "map_col": "wind_speed",
        "map_colors": ["#f2f0f7", "#cbc9e2", "#9e9ac8", "#756bb1", "#54278f"],
        "map_vmin": 0,
        "map_vmax": 20,
        "map_ticks": [0, 2, 5, 10, 15, 20],
        "format": lambda value: f"{value:.1f}",
        "legend_title": "風速 (m/s)",
    },
    "📊 測站氣壓 (hPa)": {
        "chart_cols": ["pressure"],
        "chart_names": ["測站氣壓"],
        "chart_colors": ["#636363"],
        "map_col": "pressure",
        "map_colors": ["#fee5d9", "#fcbba1", "#fc9272", "#fb6a4a", "#cb181d"],
        "map_vmin": 850,
        "map_vmax": 1050,
        "map_ticks": [850, 900, 950, 1000, 1050],
        "format": lambda value: f"{value:.0f}",
        "legend_title": "測站氣壓 (hPa)",
    },
}


def interpolate_color(value, colors, vmin, vmax):
    """Return a color blended along the given scale."""
    if pd.isna(value):
        return MISSING_COLOR

    if vmax <= vmin:
        return colors[0]

    ratio = max(0.0, min(1.0, (float(value) - vmin) / (vmax - vmin)))
    position = ratio * (len(colors) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(colors) - 1)
    blend = position - lower_index

    lower = colors[lower_index].lstrip("#")
    upper = colors[upper_index].lstrip("#")

    red = int(int(lower[0:2], 16) * (1 - blend) + int(upper[0:2], 16) * blend)
    green = int(int(lower[2:4], 16) * (1 - blend) + int(upper[2:4], 16) * blend)
    blue = int(int(lower[4:6], 16) * (1 - blend) + int(upper[4:6], 16) * blend)

    return f"#{red:02x}{green:02x}{blue:02x}"


@st.cache_data(ttl=300)
def load_latest_map_data():
    """Load the newest saved observation for each station."""
    conn = database.get_connection()
    query = """
        SELECT observation.*
        FROM WeatherObservations AS observation
        JOIN (
            SELECT stationId, MAX(dataDate) AS latestDate
            FROM WeatherObservations
            GROUP BY stationId
        ) AS latest
          ON observation.stationId = latest.stationId
         AND observation.dataDate = latest.latestDate
    """
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


@st.cache_data(ttl=300)
def load_region_history(region_name):
    return database.get_observations_by_region(region_name)


@st.cache_data(ttl=3600)
def load_geojson():
    geojson_path = APP_DIR / "data" / "taiwan.geojson"
    with geojson_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# Read regions for the selector.
try:
    regions = database.get_all_regions()
except Exception as e:
    st.error(f"資料庫讀取失敗：{e}")
    st.stop()

if not regions:
    st.warning("資料庫目前沒有觀測資料。請先取得資料並執行資料庫匯入流程。")
    st.stop()


# Remember the currently selected region and weather layer.
if "active_region" not in st.session_state:
    st.session_state.active_region = None

if (
    "weather_element" not in st.session_state
    or st.session_state.weather_element not in WEATHER_ELEMENTS
):
    st.session_state.weather_element = list(WEATHER_ELEMENTS.keys())[0]


# Compact control card at the upper left.
with st.container(key="map_controls", border=True):
    st.markdown("### ⛅ 台灣即時氣象地圖")

    base_map = st.radio(
        "顏色模式",
        ["深色", "淺色", "街道圖"],
        horizontal=True,
    )

    weather_element = st.selectbox(
        "地圖顯示資料",
        list(WEATHER_ELEMENTS.keys()),
        key="weather_element",
    )

    selected_region = st.selectbox(
        "選擇地區",
        [""] + sorted(regions),
    )
    st.session_state.active_region = selected_region or None


# Load the latest station rows for the map.
try:
    df_map = load_latest_map_data()
    if df_map.empty:
        st.warning("目前沒有可顯示的最新觀測資料。")
        st.stop()

    geojson_data = load_geojson()
except Exception as e:
    st.error(f"地圖資料載入失敗：{e}")
    st.stop()


# Convert measurements to numbers, then average station values by county.
numeric_columns = [
    "rainfall",
    "wind_dir",
    "wind_speed",
    "temp_c",
    "humidity",
    "pressure",
    "temp_min",
    "temp_max",
]

for column in numeric_columns:
    if column in df_map.columns:
        df_map[column] = pd.to_numeric(df_map[column], errors="coerce")

available_numeric_columns = [
    column for column in numeric_columns if column in df_map.columns
]

county_data = (
    df_map.groupby("regionName", as_index=False)[available_numeric_columns]
    .mean()
)
county_data["matchName"] = county_data["regionName"].map(GEO_MAPPING)

kind_cfg = WEATHER_ELEMENTS[weather_element]
map_column = kind_cfg["map_col"]

if map_column not in county_data.columns:
    st.error(f"資料庫中找不到地圖欄位：{map_column}")
    st.stop()

value_lookup = (
    county_data.dropna(subset=["matchName", map_column])
    .set_index("matchName")[map_column]
    .to_dict()
)

# Select map tiles.
map_api_key = os.getenv("MAP_API_KEY", "")

if base_map == "深色":
    if map_api_key:
        tile_url = (
            "https://{s}.basemaps.cartocdn.com/rastertiles/"
            f"dark_all/{{z}}/{{x}}/{{y}}.png?key={map_api_key}"
        )
        tile_attr = "Map data © CARTO"
    else:
        tile_url = "CartoDB dark_matter"
        tile_attr = None
elif base_map == "淺色":
    if map_api_key:
        tile_url = (
            "https://{s}.basemaps.cartocdn.com/rastertiles/"
            f"voyager/{{z}}/{{x}}/{{y}}.png?key={map_api_key}"
        )
        tile_attr = "Map data © CARTO"
    else:
        tile_url = "CartoDB positron"
        tile_attr = None
else:
    tile_url = "OpenStreetMap"
    tile_attr = None

if st.session_state.active_region and st.session_state.active_region in COORDINATES:
    map_center = COORDINATES[st.session_state.active_region]
    map_zoom = 10
else:
    map_center = [23.6978, 120.9605]
    map_zoom = 8

weather_map = folium.Map(
    location=map_center,
    zoom_start=map_zoom,
    tiles=tile_url,
    attr=tile_attr,
    control_scale=False,
    zoom_control=False,
)


def style_county(feature):
    county_name = feature["properties"]["COUNTYNAME"]
    value = value_lookup.get(county_name)
    fill_color = interpolate_color(
        value,
        kind_cfg["map_colors"],
        kind_cfg["map_vmin"],
        kind_cfg["map_vmax"],
    )
    return {
        "fillColor": fill_color,
        "color": "#ffffff",
        "weight": 1,
        "fillOpacity": 0.72,
    }


folium.GeoJson(
    geojson_data,
    name="縣市觀測值",
    style_function=style_county,
    tooltip=folium.GeoJsonTooltip(
        fields=["COUNTYNAME"],
        aliases=["縣市："],
        style="font-size: 13px; font-weight: bold;",
    ),
).add_to(weather_map)


# Add one value label per county at its approximate center.
for _, row in county_data.iterrows():
    region_name = row["regionName"]
    coordinates = COORDINATES.get(region_name)
    value = row.get(map_column)

    if not coordinates or pd.isna(value):
        continue

    label_text = kind_cfg["format"](float(value))
    label_color = interpolate_color(
        value,
        kind_cfg["map_colors"],
        kind_cfg["map_vmin"],
        kind_cfg["map_vmax"],
    )

    label_html = f"""
        <div style="
            color: {label_color};
            font-size: 12px;
            font-weight: 700;
            white-space: nowrap;
            text-shadow: 0 0 4px #fff, 0 0 7px #fff;
        ">{label_text}</div>
    """

    folium.Marker(
        location=coordinates,
        icon=folium.DivIcon(
            html=label_html,
            icon_size=(64, 22),
            icon_anchor=(32, 11),
        ),
        tooltip=region_name,
    ).add_to(weather_map)


# ── Region details overlay (rendered BEFORE the map so it floats over it) ──
active_region = st.session_state.active_region

if active_region:
    with st.container(key="region_details", border=True):
        st.markdown(f"## 📍 {active_region}")

        latest_region_rows = df_map[df_map["regionName"] == active_region]

        if latest_region_rows.empty:
            st.info("這個地區目前沒有最新觀測資料。")
        else:
            summary = latest_region_rows[numeric_columns].mean(numeric_only=True)

            current_temp = summary.get("temp_c")
            min_temp = summary.get("temp_min")
            max_temp = summary.get("temp_max")

            temp_text = (
                f"{current_temp:.1f} °C"
                if pd.notna(current_temp)
                else "—"
            )
            daily_range = (
                f"{min_temp:.1f}–{max_temp:.1f} °C"
                if pd.notna(min_temp) and pd.notna(max_temp)
                else "—"
            )

            metric_cols = st.columns(3)
            metric_cols[0].metric("即時氣溫", temp_text)
            metric_cols[1].metric("今日高低溫", daily_range)
            metric_cols[2].metric(
                "降雨量",
                f"{summary['rainfall']:.1f} mm"
                if pd.notna(summary.get("rainfall"))
                else "—",
            )

            metric_cols = st.columns(3)
            metric_cols[0].metric(
                "相對濕度",
                f"{summary['humidity']:.0f}%"
                if pd.notna(summary.get("humidity"))
                else "—",
            )
            metric_cols[1].metric(
                "風速",
                f"{summary['wind_speed']:.1f} m/s"
                if pd.notna(summary.get("wind_speed"))
                else "—",
            )
            metric_cols[2].metric(
                "測站氣壓",
                f"{summary['pressure']:.1f} hPa"
                if pd.notna(summary.get("pressure"))
                else "—",
            )

            st.caption(
                "縣市摘要為該縣市最新測站數值的平均；測站氣壓會受到測站海拔影響。"
            )

        st.markdown("### 觀測歷史")

        try:
            history = load_region_history(active_region).copy()
        except Exception as e:
            st.error(f"歷史觀測資料載入失敗：{e}")
            history = pd.DataFrame()

        if history.empty:
            st.info("目前找不到這個地區的歷史觀測資料。")
        else:
            history["dataDate"] = pd.to_datetime(history["dataDate"], errors="coerce")
            history = history.dropna(subset=["dataDate"])

            for column in numeric_columns:
                if column in history.columns:
                    history[column] = pd.to_numeric(history[column], errors="coerce")

            history_columns = [
                column for column in numeric_columns if column in history.columns
            ]

            # Average all stations in the county at each observation time.
            history = (
                history.groupby("dataDate")[history_columns]
                .mean()
                .sort_index()
                .tail(7)
            )

            chart_columns = [
                column
                for column in kind_cfg["chart_cols"]
                if column in history.columns
            ]

            if chart_columns:
                chart = history[chart_columns].dropna(how="all").copy()
                chart.columns = kind_cfg["chart_names"][: len(chart.columns)]

                if not chart.empty:
                    st.line_chart(
                        chart,
                        color=kind_cfg["chart_colors"][: len(chart.columns)],
                        height=220,
                    )
                    st.caption("圖表顯示最近 24 個觀測時間的縣市測站平均值。")
                else:
                    st.info("這個資料類型目前沒有可繪製的數值。")
            else:
                st.info("這個資料類型目前沒有可繪製的欄位。")

        if st.button("✕ 關閉", key="close_region"):
            st.session_state.active_region = None
            st.rerun()


# Keep the map full width; legend is rendered inside the folium iframe.
legend_html = f"""
<div style="
    position: fixed;
    left: 1rem;
    bottom: 1rem;
    z-index: 10000;
    width: 330px;
    padding: 0.8rem;
    background: rgba(15, 23, 42, 0.97) !important;
    border: 1px solid #475569;
    border-radius: 12px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    color: #f8fafc;
">
    <div style="font-weight:700;margin-bottom:8px;">
        {kind_cfg["legend_title"]}
    </div>
    <div style="
        height:14px;
        border-radius:7px;
        background:linear-gradient(to right, {", ".join(kind_cfg["map_colors"])});
    "></div>
    <div style="display:flex;justify-content:space-between;margin-top:5px;font-size:12px;">
        {"".join(f"<span>{tick}</span>" for tick in kind_cfg["map_ticks"])}
    </div>
</div>
"""
weather_map.get_root().html.add_child(Element(legend_html))

map_data = st_folium(
    weather_map,
    use_container_width=True,
    height=900,
    returned_objects=["last_object_clicked_tooltip"],
)

# Clicking a county or its label selects that region.
if map_data and map_data.get("last_object_clicked_tooltip"):
    clicked_name = map_data["last_object_clicked_tooltip"]
    clicked_region = GEO_TO_REGION.get(clicked_name, clicked_name)

    if clicked_region in regions and clicked_region != st.session_state.active_region:
        st.session_state.active_region = clicked_region
        st.rerun()


# Color scale legend.
ticks = kind_cfg["map_ticks"]
color_gradient = ", ".join(kind_cfg["map_colors"])
tick_labels = "".join(
    f'<span style="flex:1;text-align:center;font-size:12px;">{tick}</span>'
    for tick in ticks
)

# Region details are now rendered as an overlay ABOVE the map (before st_folium).
# Nothing needs to be rendered below the map.