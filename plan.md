# AIoT-CWA Taiwan Weather Forecast — 5-Gate Implementation Plan

## Project Goal

Build an end-to-end Taiwan weather forecast system:

**CWA Open Data API → JSON → Python/Pandas → SQLite → SQL → Streamlit → Chart/Table → Optional Taiwan Map**

The project is developed through five sequential gates. **Do not move to the next gate until the current gate passes all acceptance criteria.**

---

# Gate 1 — Project Setup & CWA API Access

## Objective

Establish a clean Python project and prove that it can securely connect to the CWA Open Data API and retrieve valid JSON.

## Implementation Tasks

- Create the Python project structure.
- Create a virtual environment.
- Add `requirements.txt`.
- Configure the CWA API key through an environment variable or `.env`.
- Implement a CWA API client using `requests`.
- Add request timeout and HTTP error handling.
- Retrieve the required Taiwan regional forecast dataset.
- Save one raw API response for development/debugging.
- Add `.gitignore` so API secrets and local database files are not committed.

Suggested structure:

```text
AIoT-CWA/
├── data/
│   └── weather_raw.json
├── src/
│   ├── fetch_weather.py
│   ├── parse_weather.py
│   └── database.py
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── plan.md
```

## Deliverables

- Working Python environment
- `requirements.txt`
- `.env.example`
- CWA API fetching module
- Sample raw JSON response
- Initial README
- Git repository initialized

## Gate 1 Acceptance Criteria

- [ ] Python environment runs successfully.
- [ ] Dependencies install successfully.
- [ ] API key is not hard-coded.
- [ ] CWA API request succeeds with a valid key.
- [ ] JSON response is received and can be saved.
- [ ] HTTP/API errors produce useful messages.
- [ ] No secret/API key is committed to Git.

**Gate condition:** Raw CWA JSON can be retrieved reliably.

---

# Gate 2 — JSON Analysis & Temperature Extraction

## Objective

Transform the nested CWA JSON response into a clean tabular dataset containing regional daily minimum and maximum temperatures.

## Implementation Tasks

- Inspect the actual CWA JSON hierarchy.
- Identify:
  - region/location name
  - forecast date
  - `MinT`
  - `MaxT`
- Implement the parser in `parse_weather.py`.
- Convert the nested JSON into a Pandas DataFrame.
- Normalize dates and numeric temperatures.
- Handle missing or malformed values safely.
- Support the required Taiwan regions.
- Add a small parser test using representative JSON.
- Validate the number of regions and forecast dates.

Target DataFrame:

```text
regionName | dataDate   | minT | maxT
-----------|------------|------|-----
北部地區     | 2026-04-14 | 18   | 26
中部地區     | 2026-04-14 | 20   | 30
南部地區     | 2026-04-14 | 22   | 31
...
```

## Deliverables

- `parse_weather.py`
- Parsed Pandas DataFrame
- Sample/test JSON
- Parsing test or validation script
- Documentation of the CWA JSON structure

## Gate 2 Acceptance Criteria

- [ ] Parser reads the actual CWA JSON format.
- [ ] Region names are extracted correctly.
- [ ] Forecast dates are extracted correctly.
- [ ] MinT values are extracted correctly.
- [ ] MaxT values are extracted correctly.
- [ ] Missing values do not crash the parser.
- [ ] Output has a predictable row per region/date.
- [ ] Parsed data can be displayed as a DataFrame.

**Gate condition:** Raw CWA JSON can be deterministically transformed into clean temperature records.

---

# Gate 3 — SQLite Persistence & Query Layer

## Objective

Persist processed weather data in SQLite and provide a clean database interface for Streamlit.

## Implementation Tasks

Create `data.db` and the `TemperatureForecasts` table:

```sql
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id INTEGER PRIMARY KEY,
    regionName TEXT NOT NULL,
    dataDate TEXT NOT NULL,
    minT REAL,
    maxT REAL
);
```

Implement:

- database initialization
- bulk insertion
- duplicate handling where appropriate
- query for all regions
- query for one region
- query for a date range
- parameterized SQL

Keep all database logic inside `database.py`.

End-to-end data loading:

```text
CWA API
  ↓
JSON
  ↓
Parser
  ↓
DataFrame
  ↓
SQLite
```

## Deliverables

- `database.py`
- `data.db`
- Database initialization function
- Insert function
- Region query function
- Forecast query function
- Database validation/test

## Gate 3 Acceptance Criteria

- [ ] SQLite database is created automatically.
- [ ] Required table/schema exists.
- [ ] Parsed records can be inserted.
- [ ] Data can be retrieved with SQL.
- [ ] Region list can be retrieved.
- [ ] A selected region returns forecast records.
- [ ] SQL queries are parameterized.
- [ ] Database logic is separated from the UI.

**Gate condition:** The complete API → parser → SQLite pipeline works without Streamlit.

---

# Gate 4 — Streamlit Weather Dashboard

## Objective

Build the required interactive Web App using Streamlit and the SQLite query layer.

## Implementation Tasks

Create `app.py` with:

### 1. Dashboard

Title:

```text
Taiwan Weather Forecast
```

### 2. Region Selector

Provide a dropdown populated from SQLite:

```text
Select Region
[ 中部地區 ▼ ]
```

### 3. Temperature Chart

Display:

- MinT
- MaxT
- forecast date
- temperature axis
- legend

### 4. Forecast Table

Display:

```text
Date        MinT    MaxT
2026-04-14   20      30
2026-04-15   21      31
2026-04-16   22      32
...
```

### 5. Error/Empty-State Handling

Handle:

- empty database
- unavailable region
- missing temperature data
- database connection failure

### 6. Separation of Responsibilities

Use:

```text
app.py
  ↓
database.py
  ↓
SQLite
```

Do not duplicate database implementation throughout `app.py`.

## Deliverables

- Working `app.py`
- Interactive region dropdown
- MinT/MaxT line chart
- Forecast table
- Error/empty states
- Screenshot or demo for README

## Gate 4 Acceptance Criteria

- [ ] `streamlit run app.py` starts successfully.
- [ ] Region dropdown is populated from SQLite.
- [ ] Selecting a region queries SQLite.
- [ ] MinT and MaxT are shown in a chart.
- [ ] Forecast records are shown in a table.
- [ ] Changing region updates chart and table.
- [ ] Empty/error states are handled cleanly.
- [ ] API key is not exposed in the UI/source.
- [ ] The app uses the Gate 3 database layer.

**Gate condition:** A user can launch the Web App, select a Taiwan region, and view its forecast chart and table.

---

# Gate 5 — Integration, Optional Taiwan Map & Delivery

## Objective

Turn the MVP into a complete, reproducible project suitable for demonstration and GitHub submission.

## Implementation Tasks

### A. End-to-End Integration

Verify:

```text
CWA API
   ↓
Raw JSON
   ↓
Python Parser
   ↓
Pandas
   ↓
SQLite
   ↓
SQL Query
   ↓
Streamlit
   ↓
Chart + Table
```

### B. Optional Taiwan Map

Only after the core dashboard is stable, add:

- Folium
- Streamlit-Folium
- Taiwan regional markers
- temperature-based marker colors

Suggested categories:

```text
< 20°C       → blue
20–25°C      → green
25–30°C      → yellow
> 30°C       → red
```

Example popup:

```text
中部地區
Date: 2026-04-14
Min: 20°C
Max: 30°C
```

The map is optional and must not break the MVP.

### C. Testing

Test:

- API failure
- invalid API key
- malformed JSON
- missing temperature value
- empty database
- invalid region
- database connection failure
- Streamlit startup

### D. Documentation

Complete `README.md` with:

- project purpose
- architecture
- project structure
- installation
- API key configuration
- database setup
- data-fetch procedure
- Streamlit execution
- screenshots
- optional map feature
- GitHub usage

### E. GitHub Delivery

Commit the final project with a clean history and ensure secrets are excluded.

Recommended final structure:

```text
AIoT-CWA/
├── data/
│   └── weather_raw.json
├── src/
│   ├── fetch_weather.py
│   ├── parse_weather.py
│   └── database.py
├── app.py
├── data.db
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── plan.md
```

## Deliverables

- Fully integrated project
- Optional Taiwan map
- Test/validation results
- Complete README
- Clean Git repository
- GitHub repository
- Final Streamlit demonstration

## Gate 5 Acceptance Criteria

- [ ] API → JSON → Parser → SQLite → Streamlit works end-to-end.
- [ ] Streamlit works from the documented setup procedure.
- [ ] Region selection works.
- [ ] Chart and table show consistent data.
- [ ] Optional map works without breaking the MVP.
- [ ] API failures and empty data are handled.
- [ ] No API secrets are committed.
- [ ] `requirements.txt` reproduces the environment.
- [ ] README contains complete setup/execution instructions.
- [ ] GitHub repository contains the final working project.

**Final gate condition:** A new developer can clone the repository, configure the CWA API key, install dependencies, retrieve weather data, and launch the Streamlit dashboard using only the README.

---

# Gate Summary

| Gate | Focus | Required Output |
|---|---|---|
| **1** | Project Setup + CWA API | Working API retrieval + raw JSON |
| **2** | JSON Analysis | Clean region/date/MinT/MaxT DataFrame |
| **3** | SQLite | Persistent database + query layer |
| **4** | Streamlit | Interactive chart + table dashboard |
| **5** | Integration + Delivery | Optional map + tests + GitHub + README |

## Core MVP

```text
CWA API
   ↓
JSON
   ↓
Python/Pandas
   ↓
SQLite
   ↓
Streamlit
   ↓
Region Selector
   ↓
Temperature Chart + Table
```

Advanced features such as the Taiwan map and additional analytics should only be added after the core pipeline is stable.
