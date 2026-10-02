# AIoT-CWA Taiwan Weather Forecast

## Project Purpose
This project provides an interactive web dashboard for Taiwan's regional weather forecasts. It retrieves a 7-day weather forecast from the Central Weather Administration (CWA) Open Data API, processes the JSON response using Python and Pandas, stores the parsed temperature data in a local SQLite database, and visualizes it using a Streamlit web application. It includes features like a regional selector, interactive temperature charts, forecast data tables, and an interactive Taiwan weather map.

## Architecture
The system pipeline operates as follows:
**CWA API → JSON → Python/Pandas → SQLite → SQL → Streamlit → Chart/Table/Map**

1. **Data Retrieval**: Fetch raw JSON data from the CWA Open Data API (F-A0010-001).
2. **Data Processing**: Parse the JSON using Python/Pandas to extract minimum (MinT) and maximum (MaxT) temperatures per region and date.
3. **Storage**: Save the cleaned tabular dataset into a local SQLite database (`data.db`).
4. **Visualization**: Query the database using Streamlit to present data via interactive line charts, data tables, and an optional Folium map.

## Project Structure
```text
AIoT-CWA/
├── data/
│   └── weather_raw.json      # Raw JSON response for debugging
├── src/
│   ├── fetch_weather.py      # Script to retrieve data from CWA API
│   ├── parse_weather.py      # Script to parse JSON into tabular format
│   └── database.py           # SQLite database initialization and queries
├── app.py                    # Streamlit web dashboard
├── data.db                   # SQLite database (generated)
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment variables file
├── .env                      # Local environment variables file (not tracked)
├── .gitignore                # Git ignore rules
└── README.md                 # Project documentation
```

## Installation
1. Clone this repository to your local machine:
   ```bash
   git clone https://github.com/your-username/AIoT-CWA.git
   cd AIoT-CWA
   ```
2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## API Key Configuration
1. Obtain an API authorization key from the [CWA Open Data Portal](https://opendata.cwa.gov.tw/).
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` and add your CWA API key:
   ```env
   CWA_API_KEY=your_api_key_here
   ```

## Database Setup and Data-Fetch Procedure
To initialize the SQLite database and fetch the latest weather forecast data:
1. Ensure your `.env` is correctly configured with your API key.
2. Run the fetch script to get the raw JSON data:
   ```bash
   python src/fetch_weather.py
   ```
3. Run the parse script to insert the data into the database:
   ```bash
   python src/parse_weather.py
   ```

## Streamlit Execution
To run the interactive web dashboard:
```bash
streamlit run app.py
```
Then, open the provided local URL (usually `http://localhost:8501`) in your web browser.

## Features
- **Region Selector**: Choose a specific region in Taiwan (e.g., Northern, Central, Southern, Eastern) to view its forecast.
- **Temperature Chart**: View interactive line charts for Minimum (MinT) and Maximum (MaxT) temperatures over a 7-day period.
- **Forecast Table**: A tabular data view of the forecast dates and temperatures.
- **Interactive Taiwan Map (Optional)**: A Folium-based interactive map displaying Taiwan's regions with color-coded markers based on average temperature (<20°C: blue, 20-25°C: green, 25-30°C: yellow, >30°C: red).

## Screenshots
*(Add screenshots of your application dashboard here - Chart, Table, and Map)*

## GitHub Usage
When pushing your project to GitHub, ensure that your `.env` file (containing your private API key) and the generated `data.db` database file are added to your `.gitignore` to prevent sensitive data or local state from being committed.
