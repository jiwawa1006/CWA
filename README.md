# ⛅ 台灣即時氣象地圖 · Taiwan Real-Time Weather Map

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://new-cwa.streamlit.app)

An interactive, full-screen weather dashboard for Taiwan built with **Streamlit** + **Folium**.  
Live weather observations are fetched from the [Central Weather Administration (CWA)](https://opendata.cwa.gov.tw/) Open Data API, stored in SQLite, and visualised on an interactive choropleth map.

---

## 🌐 Live Demo

**👉 [https://new-cwa.streamlit.app](https://new-cwa.streamlit.app)**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗺️ **Full-screen choropleth map** | Taiwan counties coloured by temperature, rainfall, humidity, wind speed, or pressure |
| 📍 **Region detail panel** | Click any county to see current metrics and a 24-observation history chart |
| 🎨 **Map style switcher** | Dark / Light / Street tile modes |
| 📊 **5 weather layers** | Temperature · Rainfall · Humidity · Wind speed · Station pressure |
| 🔄 **Auto-refresh** | Data cached for 5 minutes; map re-queries on every visit |

---

## 🗂️ Project Structure

```
new_cwa/
├── app.py                        # Streamlit dashboard (single-page app)
├── src/
│   ├── __init__.py
│   ├── fetch_weather.py          # Fetch raw JSON from CWA API
│   ├── parse_weather.py          # Parse JSON → Pandas DataFrame
│   └── database.py               # SQLite init, insert, and query helpers
├── data/
│   ├── taiwan.geojson            # County boundary polygons
│   └── weather_raw.json          # Latest raw API response (gitignored)
├── .streamlit/
│   └── secrets.toml.example      # Template for Streamlit Secrets
├── requirements.txt
├── .env                          # Local API keys (gitignored)
└── .gitignore
```

---

## 🚀 Local Setup

### 1. Clone & install

```bash
git clone https://github.com/jiwawa1006/new_cwa.git
cd new_cwa
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API keys

Copy the example and fill in your keys:

```bash
cp .env.example .env   # or create .env manually
```

`.env` contents:

```env
CWA_API_KEY=CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
CWA_API=/api/v1/rest/datastore/O-A0001-001
MAP_API_KEY=          # optional – CARTO tile key
```

> Get a free API key from the [CWA Open Data Portal](https://opendata.cwa.gov.tw/).

### 3. Seed the database (first run only)

```bash
python src/fetch_weather.py   # downloads weather_raw.json
python src/database.py        # creates data.db and inserts observations
```

### 4. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push the repo to GitHub (`.env` and `data.db` are gitignored — that's intentional).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select this repo / `app.py`.
3. In **App settings → Secrets**, paste:

```toml
CWA_API_KEY = "CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
CWA_API     = "/api/v1/rest/datastore/O-A0001-001"
MAP_API_KEY = ""   # optional
```

4. Deploy. On first load the app will auto-fetch and seed the database.

---

## 🛠️ Tech Stack

- **Python 3.11+**
- [Streamlit](https://streamlit.io/) — web framework
- [Folium](https://python-visualization.github.io/folium/) + [streamlit-folium](https://folium.streamlit.app/) — interactive map
- [Pandas](https://pandas.pydata.org/) — data processing
- [SQLite](https://www.sqlite.org/) — lightweight local database
- [CWA Open Data API](https://opendata.cwa.gov.tw/) — real-time weather source

---

## 📄 License

MIT
