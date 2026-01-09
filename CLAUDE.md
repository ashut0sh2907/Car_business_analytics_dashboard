# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Analytics dashboard for car/taxi business earnings and expense tracking. Built with Streamlit + Plotly + SQLite. All monetary values are in INR (Indian Rupees).

## Tech Stack

- **Framework**: Streamlit 1.40.0
- **Visualization**: Plotly 5.24.0
- **Database**: SQLite (via SQLAlchemy ORM 2.0.36)
- **Data Processing**: pandas 2.2.3, openpyxl 3.1.5

## Development Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Configure custom database location
cp .env.example .env
# Edit .env to change DATABASE_URL if needed (defaults to car_business.db)

# Import Excel data to database
python import_excel.py

# Run the dashboard
streamlit run app.py
```

## Project Structure

- `app.py` - Main Streamlit dashboard with charts and data entry
- `database.py` - SQLAlchemy models and database connection
- `import_excel.py` - Script to migrate Excel data to SQLite (idempotent)
- `Taxi_Earnings_Record.xlsx` - Original data source
- `car_business.db` - SQLite database file (created after first import)

## Architecture & Design Patterns

### Upsert Pattern
The `add_record()` function (app.py:38-74) implements upsert logic:
- Queries for existing record by date
- Updates if found, inserts if not
- Critical for data entry form and Excel import

### Caching Strategy
- `@st.cache_data(ttl=60)` decorator on `load_data()` (app.py:17) caches database reads
- Cache cleared after adding records: `st.cache_data.clear()` + `st.rerun()` (app.py:250-251)
- Reduces database hits while keeping UI responsive

### Session Management
All database operations use try-finally blocks for proper session cleanup:
```python
session = get_session()
try:
    # database operations
finally:
    session.close()
```

### Computed Properties
DailyRecord model provides derived metrics (database.py:32-44):
- `total_expenses` - Sum of all expense categories
- `distance_traveled` - Odometer end minus start

## Data Flow

```
Excel (.xlsx) → import_excel.py (pandas) → SQLite (SQLAlchemy) → app.py (Streamlit) → Interactive UI (Plotly)
```

## Database Schema

### `daily_records` table (database.py:18-44)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | Integer | Primary Key, Auto-increment | Record ID |
| `date` | Date | NOT NULL, **UNIQUE** | Day identifier (critical for upsert) |
| `ride_count` | Integer | Default 0 | Number of rides |
| `earnings` | Integer | Default 0 | Total earnings in INR |
| `cng_expenses` | Integer | Default 0 | Fuel/CNG costs |
| `driver_pass_subscription` | Float | Default 0 | OLA driver pass fees |
| `indrive_topup` | Float | Default 0 | InDrive app credits |
| `odometer_start` | Float | **Nullable** | Starting mileage (km) |
| `odometer_end` | Float | **Nullable** | Ending mileage (km) |
| `daily_net` | Integer | Default 0 | Calculated profit |

**Note**: Odometer fields are nullable. Zero values from UI are converted to NULL (app.py:50-51, 61-62).

**Computed Properties**:
- `total_expenses` - Auto-calculated sum of expenses
- `distance_traveled` - Odometer difference if both values present

## Key Business Logic

### Daily Net Calculation
```python
daily_net = earnings - cng_expenses - driver_pass - indrive
```
Implemented in app.py:41 and applied consistently across data entry and imports.

### Expense Categories
Three distinct expense types tracked:
1. **CNG/Fuel** - Direct fuel costs
2. **Driver Pass + OLA Subscription** - Platform fees
3. **InDrive Top-up** - App credit purchases

### Odometer Handling
- Zero values from form inputs are converted to NULL to differentiate "not recorded" from "actual zero"
- `distance_traveled` property safely handles missing values

## UI Components

Dashboard has 4 main analytics tabs:

1. **Earnings Trend** (app.py:129-138)
   - Line chart comparing earnings vs profit over time
   - Unified hover mode for easy comparison

2. **Expense Breakdown** (app.py:140-158)
   - Donut chart (hole=0.4) showing expense distribution
   - Filters out zero-value categories

3. **Daily Performance** (app.py:160-189)
   - Bar chart of daily ride counts
   - Weekly aggregation using ISO week calculation (pandas `dt.isocalendar().week`)
   - Grouped bar chart for weekly earnings vs profit

4. **Profit Analysis** (app.py:191-224)
   - Line chart of profit margin % with average reference line
   - Area chart showing cumulative profit over time

### Summary Metrics (app.py:104-122)
Five key metrics displayed at top:
- Total Earnings
- Total Expenses
- Net Profit
- Total Rides
- Avg per Ride (earnings/rides)

### Data Entry Form (app.py:227-251)
- Two-column layout for efficient data entry
- Auto-calculates daily_net on submission
- Updates existing records if date already exists
- Clears cache and reruns to show updated data

## Important Implementation Notes

### SQLite Configuration
- Default database file: `car_business.db` in project root
- Engine uses `check_same_thread=False` (database.py:15) for Streamlit's multi-threaded environment
- Can override location via `DATABASE_URL` environment variable

### Data Import
- `import_excel.py` is **idempotent** - safe to run multiple times
- Provides console feedback: "Added: X, Updated: Y"
- Maps Excel column names to database schema (import_excel.py:18-28)
- Handles NaN values with `fillna(0)`

### Database Connection
- Falls back to `sqlite:///car_business.db` if .env not configured (database.py:8-11)
- `init_db()` creates tables if they don't exist (database.py:47-48)
- Called automatically when app.py starts (app.py:78)
