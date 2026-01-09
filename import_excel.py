"""
One-time script to import data from Taxi_Earnings_Record.xlsx to SQLite.
"""

import pandas as pd
from datetime import datetime, date
from database import init_db, get_session, DailyRecord, OtherExpense


# ===================== UTIL =====================

def normalize_date(raw_date):
    """Convert any excel/string datetime to Python date"""
    if isinstance(raw_date, str):
        return datetime.strptime(raw_date, "%Y-%m-%d").date()
    elif isinstance(raw_date, datetime):
        return raw_date.date()
    elif isinstance(raw_date, date):
        return raw_date
    else:
        raise ValueError(f"Invalid date format: {raw_date}")


# ================= DAILY RECORD =================

def import_daily_records(excel_path: str):

    sheets = ["Daily Record 2025", "Daily Record 2026"]
    all_df = []

    for sheet in sheets:
        print(f"Reading sheet: {sheet}")
        df = pd.read_excel(excel_path, sheet_name=sheet)

        if df.empty:
            continue

        df = df.rename(columns={
            "Date": "date",
            "Ride Count": "ride_count",
            "Earnings (₹)": "earnings",
            "CNG Expenses (₹)": "cng_expenses",
            "Driver Pass (₹)+OLA Subscription": "driver_pass_subscription",
            "InDrive Top-up": "indrive_topup",
            "Odometer(Km)": "odometer_start",
            "EOD Odometer(km)": "odometer_end",
            "Daily Net (₹)": "daily_net",
        })

        df['daily_net'] = (
            df['earnings'] -
            df['cng_expenses'] -
            df['driver_pass_subscription'].fillna(0) -
            df['indrive_topup'].fillna(0)
        )

        df = df.fillna(0)
        print(f"  Loaded {len(df)} records")
        all_df.append(df)

    combined = pd.concat(all_df, ignore_index=True)
    combined = combined.sort_values('date')

    session = get_session()
    added = updated = 0

    try:
        for _, row in combined.iterrows():

            record_date = normalize_date(row["date"])

            with session.no_autoflush:
                existing = session.query(DailyRecord)\
                    .filter_by(date=record_date).first()

            if existing:
                existing.ride_count = int(row["ride_count"])
                existing.earnings = int(row["earnings"])
                existing.cng_expenses = int(row["cng_expenses"])
                existing.driver_pass_subscription = float(row["driver_pass_subscription"])
                existing.indrive_topup = float(row["indrive_topup"])
                existing.odometer_start = float(row["odometer_start"]) if row["odometer_start"] else None
                existing.odometer_end = float(row["odometer_end"]) if row["odometer_end"] else None
                existing.daily_net = int(row["daily_net"])
                updated += 1
            else:
                record = DailyRecord(
                    date=record_date,
                    ride_count=int(row["ride_count"]),
                    earnings=int(row["earnings"]),
                    cng_expenses=int(row["cng_expenses"]),
                    driver_pass_subscription=float(row["driver_pass_subscription"]),
                    indrive_topup=float(row["indrive_topup"]),
                    odometer_start=float(row["odometer_start"]) if row["odometer_start"] else None,
                    odometer_end=float(row["odometer_end"]) if row["odometer_end"] else None,
                    daily_net=int(row["daily_net"]),
                )
                session.add(record)
                added += 1

        session.commit()
        print(f"  Added: {added}")
        print(f"  Updated: {updated}")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return added, updated


# ================= OTHER EXPENSE =================

def import_other_expenses(excel_path: str):

    sheets = ["Other Expenses 2025", "Other Expenses 2026"]
    all_df = []

    for sheet in sheets:
        print(f"Reading sheet: {sheet}")
        df = pd.read_excel(excel_path, sheet_name=sheet)

        if df.empty:
            continue

        df = df.rename(columns={
            "Date": "date",
            "Expenses(₹)": "expenses",
            "Months": "months",
            "Car EMI(₹)": "car_emi",
            "Pg Rent(₹)": "pg_rent",
        })

        df[['expenses','car_emi','pg_rent']] = \
            df[['expenses','car_emi','pg_rent']].fillna(0)

        df = df[
            (df['expenses'] != 0) |
            (df['car_emi'] != 0) |
            (df['pg_rent'] != 0)
        ]

        print(f"  Loaded {len(df)} records")
        all_df.append(df)

    combined = pd.concat(all_df, ignore_index=True)
    combined = combined.sort_values('date')

    session = get_session()
    added = updated = 0

    try:
        for _, row in combined.iterrows():

            record_date = normalize_date(row["date"])

            with session.no_autoflush:
                existing = session.query(OtherExpense)\
                    .filter_by(date=record_date).first()

            if existing:
                existing.expenses = float(row["expenses"])
                existing.months = str(row["months"]) if pd.notna(row["months"]) else None
                existing.car_emi = float(row["car_emi"])
                existing.pg_rent = float(row["pg_rent"])
                updated += 1
            else:
                record = OtherExpense(
                    date=record_date,
                    expenses=float(row["expenses"]),
                    months=str(row["months"]) if pd.notna(row["months"]) else None,
                    car_emi=float(row["car_emi"]),
                    pg_rent=float(row["pg_rent"]),
                )
                session.add(record)
                added += 1

        session.commit()
        print(f"  Added: {added}")
        print(f"  Updated: {updated}")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return added, updated


# ================= MAIN =================

def import_excel_to_db(excel_path="Taxi_Earnings_Record.xlsx"):

    print("Initializing database...")
    init_db()

    print("\nIMPORTING DAILY RECORDS")
    d_add, d_upd = import_daily_records(excel_path)

    print("\nIMPORTING OTHER EXPENSES")
    e_add, e_upd = import_other_expenses(excel_path)

    print("\nIMPORT COMPLETE")
    print(f"Daily: {d_add} added, {d_upd} updated")
    print(f"Expense: {e_add} added, {e_upd} updated")


if __name__ == "__main__":
    import_excel_to_db()
