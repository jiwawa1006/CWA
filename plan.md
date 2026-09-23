# AIoT-CWA — Implementation Plan

## Project Goal

Build a Taiwan Weather Forecast web application using the CWA Open Data API.

### Core pipeline

```text
CWA Open Data API
        ↓
     Raw JSON
        ↓
 Python / Pandas
        ↓
  Data validation
        ↓
     SQLite
        ↓
   SQL queries
        ↓
    Streamlit
        ↓
 ┌──────┴────────┐
 ▼               ▼
Chart           Table
        ↓
 Optional Taiwan Map
        ↓
     GitHub
```

### Technology Stack

- Python 3.x
- `requests`
- CWA Open Data API
- JSON
- `pandas`
- SQLite
- Streamlit
- Folium / `streamlit-folium` (optional)
- Git / GitHub
- Antigravity as the coding agent

---

# Gate System

This project is developed as a sequence of **gates**.

A gate is not complete until all of its acceptance criteria pass.

### Rules

1. Complete gates in order.
2. Do not start the next gate while the current gate is failing.
3. Each gate must leave the repository in a runnable state.
4. Prefer small, testable changes over large rewrites.
5. Never hard-code the CWA API key.
6. Keep API fetching, parsing, database logic, and UI logic separated.
7. After each gate, run the relevant tests/checks and commit the result to Git.
8. If a later gate exposes a problem in an earlier gate, fix the earlier gate rather than adding a workaround in the UI.

---

# Gate 0 — Project Initialization

## Objective

Create a clean Python project structure and development environment.

## Expected structure

```text
AIoT-CWA/
├── app.py
├── fetch_weather.py
├── parse_weather.py
├── database.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── tests/
│   ├── test_parser.py
│   └── sample_weather.json
├── data/
│   └── .gitkeep
└── data.db                 # generated locally; normally gitignored
```

## Tasks

- Initialize Git repository.
- Create Python virtual environment.
- Create `requirements.txt`.
- Create `.gitignore`.
- Create `.env.example`.
- Create initial README.
- Create basic module files.
- Add a minimal test structure.

## Acceptance Criteria

- [ ] `python --version` works.
- [ ] Virtual environment can be activated.
- [ ] Dependencies can be installed.
- [ ] Repository has clean initial structure.
- [ ] No API key is committed.
- [ ] `git status` is clean after the initial commit.

## Gate Check

```bash
python --version
pip install -r requirements.txt
git status
```

### Commit

```text
chore: initialize AIoT-CWA project
```

---

# Gate 1 — CWA API Configuration

## Objective

Configure access to the CWA Open Data API without exposing secrets.

## Tasks

- Identify the required CWA weather dataset/API endpoint.
- Read the API key from an environment variable.
- Support `.env` locally if desired.
- Keep `.env` out of Git.
- Define a configurable API URL.
- Add request timeout.
- Add HTTP error handling.

## Configuration concept

```text
.env
├── CWA_API_KEY=...
└── CWA_API_URL=...
```

The repository should only contain:

```text
.env.example
```

with placeholder values.

## Acceptance Criteria

- [ ] API key is not hard-coded.
- [ ] API key is not printed in logs.
- [ ] Missing API key produces a clear error.
- [ ] API timeout is configured.
- [ ] HTTP errors are handled.
- [ ] API endpoint can be changed through configuration.

## Gate Check

Run the API client manually and verify that it receives valid JSON.

### Commit

```text
feat: add CWA API configuration and client
```

---

# Gate 2 — Raw Weather Data Acquisition

## Objective

Retrieve the CWA forecast JSON and preserve the raw response.

## Tasks

Implement:

```text
fetch_weather.py
```

Responsibilities:

1. Build API request.
2. Send HTTP GET request.
3. Validate response.
4. Parse JSON.
5. Save raw JSON under `data/`.
6. Return the JSON object to callers.

Example flow:

```text
CWA API
   ↓
requests.get()
   ↓
HTTP response
   ↓
response.json()
   ↓
data/weather_raw.json
```

## Acceptance Criteria

- [ ] API request succeeds with a valid key.
- [ ] Raw JSON is saved.
- [ ] Saved JSON is valid.
- [ ] Network errors are handled.
- [ ] HTTP errors are handled.
- [ ] Invalid JSON is handled.
- [ ] API key is never written into the raw data file.

## Gate Check

```bash
python fetch_weather.py
```

Then verify:

```text
data/weather_raw.json
```

exists and contains valid CWA JSON.

### Commit

```text
feat: implement CWA weather data acquisition
```

---

# Gate 3 — JSON Parsing and Data Normalization

## Objective

Convert the CWA JSON structure into a simple tabular format.

## Target schema

```text
regionName
dataDate
minT
maxT
```

Example:

| regionName | dataDate | minT | maxT |
|---|---|---:|---:|
| 北部地區 | 2026-04-14 | 18 | 26 |
| 中部地區 | 2026-04-14 | 20 | 30 |
| 南部地區 | 2026-04-14 | 22 | 31 |

## Tasks

Implement:

```text
parse_weather.py
```

Responsibilities:

- Read raw JSON.
- Navigate the CWA JSON hierarchy.
- Extract region name.
- Extract forecast date.
- Find `MinT`.
- Find `MaxT`.
- Normalize dates.
- Convert temperatures to numeric values.
- Return a Pandas DataFrame.

## Important

Do not assume that every JSON field is always present.

Handle:

- missing `weatherElement`
- missing `time`
- missing `MinT`
- missing `MaxT`
- unexpected values
- empty locations

## Acceptance Criteria

- [ ] Parser produces a DataFrame.
- [ ] Required columns exist.
- [ ] Dates are normalized.
- [ ] MinT is numeric.
- [ ] MaxT is numeric.
- [ ] Multiple regions are parsed.
- [ ] Multiple forecast days are parsed.
- [ ] Missing data does not crash the entire parser.
- [ ] Parser has automated tests using sample JSON.

## Gate Check

```bash
pytest
```

Expected result:

```text
All parser tests passed
```

### Commit

```text
feat: parse and normalize CWA forecast JSON
```

---

# Gate 4 — Data Validation

## Objective

Ensure bad API data does not silently enter the database.

## Validation Rules

At minimum:

```text
regionName != empty
dataDate is valid
minT is numeric
maxT is numeric
minT <= maxT
```

Additional validation may include:

- duplicate region/date detection
- unexpected temperature values
- unsupported region names
- missing forecast dates

## Tasks

Add a validation layer.

Suggested flow:

```text
Raw JSON
   ↓
Parser
   ↓
DataFrame
   ↓
Validation
   ↓
Validated DataFrame
```

## Acceptance Criteria

- [ ] Invalid rows can be detected.
- [ ] Validation errors are understandable.
- [ ] `minT > maxT` is rejected or explicitly handled.
- [ ] Missing required fields are detected.
- [ ] Duplicate records are detected.
- [ ] Valid sample data passes validation.

## Gate Check

Run both valid and intentionally invalid test cases.

```bash
pytest
```

### Commit

```text
feat: add weather data validation
```

---

# Gate 5 — SQLite Database

## Objective

Persist normalized weather data in SQLite.

## Database

```text
data.db
```

## Table

```sql
CREATE TABLE TemperatureForecasts (
    id INTEGER PRIMARY KEY,
    regionName TEXT NOT NULL,
    dataDate TEXT NOT NULL,
    minT REAL,
    maxT REAL,
    UNIQUE(regionName, dataDate)
);
```

## Tasks

Implement:

```text
database.py
```

Functions should include:

```python
initialize_database()
insert_forecasts(df)
get_regions()
get_forecast(region)
```

Optional:

```python
clear_forecasts()
upsert_forecasts(df)
```

## Requirements

- Use parameterized SQL.
- Prevent duplicate region/date records.
- Keep connection handling clean.
- Keep SQL logic inside `database.py`.
- Do not scatter SQL statements throughout the Streamlit UI.

## Acceptance Criteria

- [ ] Database is created automatically.
- [ ] Table is created automatically.
- [ ] Valid forecast data can be inserted.
- [ ] Duplicate region/date data is handled.
- [ ] Regions can be queried.
- [ ] Forecast data can be queried by region.
- [ ] SQL injection is avoided through parameterized queries.

## Gate Check

Verify:

```text
data.db
└── TemperatureForecasts
```

and manually test:

```sql
SELECT DISTINCT regionName
FROM TemperatureForecasts;
```

### Commit

```text
feat: add SQLite weather database layer
```

---

# Gate 6 — End-to-End Data Pipeline

## Objective

Connect API acquisition, parsing, validation, and database storage.

## Target workflow

```text
CWA API
   ↓
fetch_weather.py
   ↓
raw JSON
   ↓
parse_weather.py
   ↓
DataFrame
   ↓
validation
   ↓
database.py
   ↓
SQLite
```

## Tasks

Create a simple pipeline entry point or command that can execute:

```text
fetch → parse → validate → save
```

The pipeline should be safe to run repeatedly.

## Acceptance Criteria

- [ ] One command can refresh the database.
- [ ] API data is fetched successfully.
- [ ] Data is parsed successfully.
- [ ] Data passes validation.
- [ ] Data is inserted/upserted into SQLite.
- [ ] Running the pipeline twice does not create duplicate records.
- [ ] Errors are reported clearly.

## Gate Check

Run the complete pipeline twice.

```bash
python fetch_weather.py
```

or the project's chosen pipeline command.

Then confirm that duplicate rows are not created.

### Commit

```text
feat: connect weather ingestion pipeline
```

---

# Gate 7 — Streamlit MVP

## Objective

Build the minimum usable weather dashboard.

## UI requirements

The application must provide:

1. Page title
2. Region dropdown
3. Temperature line chart
4. Forecast data table

## UI flow

```text
Start Streamlit
      ↓
Connect SQLite
      ↓
Load regions
      ↓
Region dropdown
      ↓
User selects region
      ↓
Query SQLite
      ↓
DataFrame
      ↓
Chart + Table
```

## Example UI

```text
Taiwan Weather Forecast

Select Region
[ 中部地區 ▼ ]

Temperature Forecast

        MaxT ─────────
        MinT ─────────

Date          MinT    MaxT
2026-04-14     20      30
2026-04-15     21      31
...
```

## Tasks

Implement:

```text
app.py
```

Use:

- Streamlit
- Pandas
- SQLite

## Acceptance Criteria

- [ ] `streamlit run app.py` starts successfully.
- [ ] Region dropdown is populated from the database.
- [ ] Selecting a region updates the data.
- [ ] MinT and MaxT are displayed.
- [ ] Line chart is displayed.
- [ ] Data table is displayed.
- [ ] Empty results are handled gracefully.
- [ ] Database implementation remains separated from UI code.

## Gate Check

```bash
streamlit run app.py
```

Manually verify:

- region selection
- chart
- table
- empty/no-data behavior

### Commit

```text
feat: build Streamlit weather dashboard MVP
```

---

# Gate 8 — Dashboard Quality

## Objective

Make the MVP clean and usable.

## Tasks

Improve:

- page title
- layout
- chart labels
- temperature units
- date formatting
- table formatting
- loading/error messages
- empty-state messages
- sidebar or controls if useful

Optional:

- summary metrics
- latest forecast date
- selected-region MinT
- selected-region MaxT

## Acceptance Criteria

- [ ] UI is readable.
- [ ] Chart clearly distinguishes MinT and MaxT.
- [ ] Dates are understandable.
- [ ] Temperature units are shown.
- [ ] Errors do not expose secrets or stack traces unnecessarily.
- [ ] Empty database state has a useful message.

### Commit

```text
feat: improve weather dashboard UX
```

---

# Gate 9 — Taiwan Map Visualization (Optional)

## Objective

Add geographical visualization using Folium.

## Technology

```text
folium
streamlit-folium
```

## Concept

```text
Weather Data
     ↓
Region temperature
     ↓
Taiwan map
     ↓
Temperature-colored markers
```

## Suggested temperature scale

| Temperature | Display |
|---|---|
| < 20°C | Blue |
| 20–25°C | Green |
| 25–30°C | Yellow |
| > 30°C | Red |

## Map interaction

Selecting a region/date should show information such as:

```text
中部地區
Date: 2026-04-14
Min: 20°C
Max: 30°C
```

## Acceptance Criteria

- [ ] Taiwan map renders.
- [ ] Major weather regions have markers.
- [ ] Marker information is correct.
- [ ] Temperature classification is correct.
- [ ] Map does not break the main dashboard.
- [ ] Map is optional and can be disabled without breaking the application.

### Commit

```text
feat: add optional Taiwan weather map
```

---

# Gate 10 — Testing and Reliability

## Objective

Make the project reliable enough for demonstration.

## Test areas

### API

- [ ] successful request
- [ ] timeout
- [ ] HTTP error
- [ ] invalid JSON

### Parser

- [ ] valid JSON
- [ ] missing fields
- [ ] multiple regions
- [ ] multiple dates

### Validation

- [ ] missing region
- [ ] invalid date
- [ ] invalid temperature
- [ ] MinT > MaxT
- [ ] duplicate records

### Database

- [ ] initialization
- [ ] insert
- [ ] duplicate handling
- [ ] region query
- [ ] forecast query

## Acceptance Criteria

```bash
pytest
```

passes.

The application can start from a fresh environment after installation.

### Commit

```text
test: add pipeline and database reliability tests
```

---

# Gate 11 — GitHub and Reproducibility

## Objective

Make the project reproducible for another developer.

## Repository should contain

```text
AIoT-CWA/
├── app.py
├── fetch_weather.py
├── parse_weather.py
├── database.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
├── tests/
└── data/
```

Do not commit:

```text
.env
*.db
__pycache__/
.pytest_cache/
.venv/
secrets
API keys
```

## README must explain

1. Project purpose
2. Architecture
3. Installation
4. CWA API key setup
5. How to fetch data
6. How to initialize/update SQLite
7. How to start Streamlit
8. Project structure
9. Example screenshots
10. Known limitations

## Acceptance Criteria

- [ ] Git repository is clean.
- [ ] README is complete.
- [ ] No secret is committed.
- [ ] Another developer can understand the project.
- [ ] Installation instructions work.
- [ ] Application startup instructions work.

### Commit

```text
docs: finalize project documentation
```

---

# Gate 12 — Final Demonstration

## Objective

Demonstrate the complete AIoT-CWA workflow.

## Demo sequence

### 1. Explain the architecture

```text
CWA API
  ↓
Python
  ↓
JSON
  ↓
Pandas
  ↓
SQLite
  ↓
SQL
  ↓
Streamlit
```

### 2. Run data acquisition

Show:

```text
CWA API → raw JSON
```

### 3. Show JSON parsing

Show:

```text
regionName
dataDate
minT
maxT
```

### 4. Show SQLite

Show:

```text
TemperatureForecasts
```

### 5. Show SQL query

Example:

```sql
SELECT *
FROM TemperatureForecasts
WHERE regionName = '中部地區';
```

### 6. Show Streamlit

Demonstrate:

- region selection
- temperature chart
- forecast table

### 7. Optional map

Demonstrate:

- Taiwan map
- temperature markers
- selected region

## Final Acceptance Criteria

- [ ] Complete pipeline works from API to dashboard.
- [ ] Data is stored persistently.
- [ ] Dashboard is interactive.
- [ ] Project can be reproduced from README.
- [ ] Tests pass.
- [ ] GitHub repository is clean.
- [ ] No credentials are exposed.

### Final Commit

```text
release: complete AIoT-CWA weather dashboard
```

---

# Antigravity Operating Rules

When using Antigravity, treat each gate as an independent task.

## Before starting a gate

Tell Antigravity:

```text
We are working on Gate N.

Read PLAN.md first.

Implement only the requirements of this gate.
Do not start later gates.
Do not rewrite unrelated working code.

Before finishing:
1. Run the relevant tests/checks.
2. Report what changed.
3. Report the verification results.
4. Report any remaining issues.
```

## After a gate passes

Review the changes yourself.

Then commit:

```bash
git status
git diff
git add .
git commit -m "..."
```

Only after that should you move to the next gate.

---

# Recommended Development Order

```text
Gate 0
  │
  ▼
Gate 1 ── API configuration
  │
  ▼
Gate 2 ── Fetch raw JSON
  │
  ▼
Gate 3 ── Parse JSON
  │
  ▼
Gate 4 ── Validate data
  │
  ▼
Gate 5 ── SQLite
  │
  ▼
Gate 6 ── End-to-end pipeline
  │
  ▼
Gate 7 ── Streamlit MVP
  │
  ▼
Gate 8 ── Dashboard quality
  │
  ├───────────────┐
  ▼               ▼
Gate 9          Gate 10
Map             Testing
  │               │
  └───────┬───────┘
          ▼
      Gate 11
      GitHub
          │
          ▼
      Gate 12
      Demo
```

---

# Definition of Done

The project is considered complete when:

```text
[✓] CWA API works
[✓] Raw JSON can be retrieved
[✓] JSON can be parsed
[✓] MinT / MaxT are extracted
[✓] Data is validated
[✓] Data is stored in SQLite
[✓] SQL queries work
[✓] Streamlit dashboard works
[✓] Region selection works
[✓] Temperature chart works
[✓] Temperature table works
[✓] Tests pass
[✓] GitHub repository is documented
[✓] Secrets are protected
[✓] Optional Taiwan map works, if implemented
```

## Final Architecture

```text
┌──────────────────────┐
│ CWA Open Data API    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ fetch_weather.py     │
│ API / HTTP / JSON    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ parse_weather.py     │
│ JSON → DataFrame     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Validation           │
│ Data quality checks  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ database.py          │
│ SQLite / SQL         │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ app.py               │
│ Streamlit            │
├──────────────────────┤
│ Region selector      │
│ Temperature chart    │
│ Forecast table       │
│ Taiwan map (optional)│
└──────────────────────┘
```

**Core principle:** finish and verify one gate before progressing to the next gate.
