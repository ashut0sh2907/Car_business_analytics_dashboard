import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_session, DailyRecord, OtherExpense, init_db

st.set_page_config(
    page_title="Car Business Analytics",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Car Business Analytics Dashboard")


@st.cache_data(ttl=60)
def load_data():
    session = get_session()
    try:
        records = session.query(DailyRecord).order_by(DailyRecord.date).all()
        data = [{
            "date": r.date,
            "ride_count": r.ride_count,
            "earnings": r.earnings,
            "cng_expenses": r.cng_expenses,
            "driver_pass_subscription": r.driver_pass_subscription or 0,
            "indrive_topup": r.indrive_topup or 0,
            "odometer_start": r.odometer_start,
            "odometer_end": r.odometer_end,
            "daily_net": r.daily_net,
        } for r in records]
        return pd.DataFrame(data)
    finally:
        session.close()


@st.cache_data(ttl=60)
def load_other_expenses():
    """Load Other Expenses data from database"""
    session = get_session()
    try:
        records = session.query(OtherExpense).order_by(OtherExpense.date).all()
        data = [{
            "date": r.date,
            "expenses": r.expenses,
            "months": r.months,
            "car_emi": r.car_emi,
            "pg_rent": r.pg_rent,
            "total": r.total_other_expenses,
        } for r in records]
        return pd.DataFrame(data) if data else pd.DataFrame()
    finally:
        session.close()


def add_record(date, ride_count, earnings, cng_expenses, driver_pass, indrive, odo_start, odo_end):
    session = get_session()
    try:
        daily_net = earnings - cng_expenses - driver_pass - indrive
        existing = session.query(DailyRecord).filter_by(date=date).first()

        if existing:
            existing.ride_count = ride_count
            existing.earnings = earnings
            existing.cng_expenses = cng_expenses
            existing.driver_pass_subscription = driver_pass
            existing.indrive_topup = indrive
            existing.odometer_start = odo_start if odo_start > 0 else None
            existing.odometer_end = odo_end if odo_end > 0 else None
            existing.daily_net = int(daily_net)
        else:
            record = DailyRecord(
                date=date,
                ride_count=ride_count,
                earnings=earnings,
                cng_expenses=cng_expenses,
                driver_pass_subscription=driver_pass,
                indrive_topup=indrive,
                odometer_start=odo_start if odo_start > 0 else None,
                odometer_end=odo_end if odo_end > 0 else None,
                daily_net=int(daily_net),
            )
            session.add(record)

        session.commit()
        return True
    except Exception as e:
        session.rollback()
        st.error(f"Error saving record: {e}")
        return False
    finally:
        session.close()


# Initialize database
init_db()

# Load data
df = load_data()

# Load other expenses data
other_expenses_df = load_other_expenses()

if df.empty:
    st.warning("No data found. Please run `python import_excel.py` to import your Excel data, or add records below.")
else:

    # --- Enhanced Filters: Date Range or Monthly ---
    st.sidebar.header("Filters")
    min_date = df["date"].min()
    max_date = df["date"].max()


    filter_type = st.sidebar.radio("Analysis Type", ["Date Range", "Monthly"], index=0)

    if filter_type == "Date Range":
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
        else:
            filtered_df = df
        filter_month = None
        selected_month = None
    else:
        # Monthly filter
        months = pd.to_datetime(df["date"]).dt.to_period("M")
        month_list = sorted(months.unique())
        month_strs = [str(m) for m in month_list]
        selected_month = st.sidebar.selectbox("Select Month", month_strs, index=len(month_strs)-1)
        filter_month = pd.Period(selected_month)
        filtered_df = df[months == filter_month]




    # Summary metrics
    if filter_type == "Monthly" and selected_month:
        st.header(f"Summary for {selected_month}")
    else:
        st.header("Summary")

    col1, col2, col3, col4, col5 = st.columns(5)

    total_earnings = filtered_df["earnings"].sum()
    total_expenses = (
        filtered_df["cng_expenses"].sum() +
        filtered_df["driver_pass_subscription"].sum() +
        filtered_df["indrive_topup"].sum()
    )
    total_profit = filtered_df["daily_net"].sum()
    total_rides = filtered_df["ride_count"].sum()
    avg_per_ride = total_earnings / total_rides if total_rides > 0 else 0

    col1.metric("Total Earnings", f"₹{total_earnings:,.0f}")
    col2.metric("Total Expenses", f"₹{total_expenses:,.0f}")
    col3.metric("Net Profit", f"₹{total_profit:,.0f}")
    col4.metric("Total Rides", f"{total_rides:,}")
    col5.metric("Avg per Ride", f"₹{avg_per_ride:,.0f}")

    # Show daily records for selected month if in Monthly mode
    if filter_type == "Monthly" and selected_month:
        st.subheader(f"Daily Records for {selected_month}")
        if not filtered_df.empty:
            st.dataframe(filtered_df.sort_values("date"), use_container_width=True)
        else:
            st.info("No records for this month.")

    # Monthly Summary Section
    st.header("Monthly Summary")

    if not filtered_df.empty:
        # Calculate monthly aggregations
        monthly_df = filtered_df.copy()
        monthly_df['month'] = pd.to_datetime(monthly_df['date']).dt.to_period('M')

        monthly_summary = monthly_df.groupby('month').agg({
            'earnings': 'sum',
            'cng_expenses': 'sum',
            'driver_pass_subscription': 'sum',
            'indrive_topup': 'sum',
            'daily_net': 'sum',
            'ride_count': 'sum',
            'date': 'count'  # Days worked
        }).reset_index()

        # Calculate total expenses per month
        monthly_summary['total_expenses'] = (
            monthly_summary['cng_expenses'] +
            monthly_summary['driver_pass_subscription'] +
            monthly_summary['indrive_topup']
        )

        # Add other expenses if available
        if not other_expenses_df.empty:
            expense_monthly = other_expenses_df.copy()
            expense_monthly['month'] = pd.to_datetime(expense_monthly['date']).dt.to_period('M')
            expense_summary = expense_monthly.groupby('month').agg({
                'car_emi': 'sum',
                'pg_rent': 'sum',
                'expenses': 'sum'
            }).reset_index()

            # Merge with daily summary
            monthly_summary = monthly_summary.merge(expense_summary, on='month', how='left')
            monthly_summary[['car_emi', 'pg_rent', 'expenses']] = monthly_summary[['car_emi', 'pg_rent', 'expenses']].fillna(0)

            # Recalculate total with other expenses
            monthly_summary['total_all_expenses'] = (
                monthly_summary['total_expenses'] +
                monthly_summary['car_emi'] +
                monthly_summary['pg_rent'] +
                monthly_summary['expenses']
            )
            monthly_summary['net_profit'] = monthly_summary['earnings'] - monthly_summary['total_all_expenses']
        else:
            monthly_summary['net_profit'] = monthly_summary['daily_net']

        # Convert month Period to string for display
        monthly_summary['month_str'] = monthly_summary['month'].astype(str)

        # Display as cards or table
        st.subheader("Monthly Performance")

        # Show each month's summary
        for idx, row in monthly_summary.iterrows():
            with st.expander(f"📅 {row['month_str']} - ₹{row['earnings']:,.0f} earnings, {row['ride_count']:,} rides", expanded=(idx == len(monthly_summary)-1)):
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Earnings", f"₹{row['earnings']:,.0f}")
                col2.metric("Total Expenses", f"₹{row.get('total_all_expenses', row['total_expenses']):,.0f}")
                col3.metric("Net Profit", f"₹{row['net_profit']:,.0f}")
                col4.metric("Days Worked", f"{row['date']}")

                # Show detailed breakdown if other expenses exist
                if not other_expenses_df.empty and row.get('car_emi', 0) > 0:
                    st.caption("**Expense Breakdown:**")
                    exp_col1, exp_col2, exp_col3 = st.columns(3)
                    exp_col1.caption(f"Daily Ops: ₹{row['total_expenses']:,.0f}")
                    exp_col2.caption(f"Car EMI: ₹{row.get('car_emi', 0):,.0f}")
                    exp_col3.caption(f"PG Rent: ₹{row.get('pg_rent', 0):,.0f}")
    else:
        st.info("No data available for selected date range")

    # Charts
    st.header("Analytics")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Earnings Trend", "Expense Breakdown", "Daily Performance", "Profit Analysis", "Other Expenses"])

    with tab1:
        fig = px.line(
            filtered_df,
            x="date",
            y=["earnings", "daily_net"],
            title="Earnings & Profit Over Time",
            labels={"value": "Amount (₹)", "date": "Date", "variable": "Metric"},
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        expense_data = pd.DataFrame({
            "Category": ["CNG/Fuel", "Driver Pass + OLA", "InDrive Top-up"],
            "Amount": [
                filtered_df["cng_expenses"].sum(),
                filtered_df["driver_pass_subscription"].sum(),
                filtered_df["indrive_topup"].sum()
            ]
        })
        expense_data = expense_data[expense_data["Amount"] > 0]

        fig = px.pie(
            expense_data,
            values="Amount",
            names="Category",
            title="Expense Distribution",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        fig = px.bar(
            filtered_df,
            x="date",
            y="ride_count",
            title="Daily Ride Count",
            labels={"ride_count": "Rides", "date": "Date"}
        )
        st.plotly_chart(fig, use_container_width=True)

        # Weekly aggregation
        weekly_df = filtered_df.copy()
        weekly_df["week"] = pd.to_datetime(weekly_df["date"]).dt.isocalendar().week
        weekly_df["year"] = pd.to_datetime(weekly_df["date"]).dt.year
        weekly_agg = weekly_df.groupby(["year", "week"]).agg({
            "earnings": "sum",
            "daily_net": "sum",
            "ride_count": "sum"
        }).reset_index()
        weekly_agg["week_label"] = weekly_agg["year"].astype(str) + "-W" + weekly_agg["week"].astype(str)

        fig2 = px.bar(
            weekly_agg,
            x="week_label",
            y=["earnings", "daily_net"],
            title="Weekly Earnings vs Profit",
            labels={"value": "Amount (₹)", "week_label": "Week"},
            barmode="group"
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab4:
        # Profit margin over time
        profit_df = filtered_df.copy()
        profit_df["profit_margin"] = (profit_df["daily_net"] / profit_df["earnings"] * 100).fillna(0)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=profit_df["date"],
            y=profit_df["profit_margin"],
            mode="lines+markers",
            name="Profit Margin %",
            line=dict(color="green")
        ))
        fig.add_hline(y=profit_df["profit_margin"].mean(), line_dash="dash",
                      annotation_text=f"Avg: {profit_df['profit_margin'].mean():.1f}%")
        fig.update_layout(
            title="Daily Profit Margin",
            xaxis_title="Date",
            yaxis_title="Profit Margin (%)"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Cumulative profit
        cumulative_df = filtered_df.copy()
        cumulative_df["cumulative_profit"] = cumulative_df["daily_net"].cumsum()

        fig2 = px.area(
            cumulative_df,
            x="date",
            y="cumulative_profit",
            title="Cumulative Profit",
            labels={"cumulative_profit": "Total Profit (₹)", "date": "Date"}
        )
        st.plotly_chart(fig2, use_container_width=True)


    with tab5:
        st.subheader("Other Expenses Tracking")

        if other_expenses_df.empty:
            st.info("No other expenses recorded yet. Other expenses include Car EMI, PG Rent, and miscellaneous costs.")
        else:
            # Filter other expenses by sidebar selection
            if filter_type == "Date Range" and 'start_date' in locals() and 'end_date' in locals():
                filtered_expenses = other_expenses_df[
                    (other_expenses_df["date"] >= start_date) &
                    (other_expenses_df["date"] <= end_date)
                ]
            elif filter_type == "Monthly" and filter_month is not None:
                months_exp = pd.to_datetime(other_expenses_df["date"]).dt.to_period("M")
                filtered_expenses = other_expenses_df[months_exp == filter_month]
            else:
                filtered_expenses = other_expenses_df

            if filtered_expenses.empty:
                st.warning("No other expenses in selected date range")
            else:
                # Summary metrics for other expenses
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Car EMI", f"₹{filtered_expenses['car_emi'].sum():,.0f}")
                col2.metric("Total PG Rent", f"₹{filtered_expenses['pg_rent'].sum():,.0f}")
                col3.metric("Total Misc Expenses", f"₹{filtered_expenses['expenses'].sum():,.0f}")
                col4.metric("Grand Total", f"₹{filtered_expenses['total'].sum():,.0f}")

                # Pie chart - Expense category breakdown
                st.subheader("Expense Category Breakdown")
                expense_totals = {
                    "Car EMI": filtered_expenses['car_emi'].sum(),
                    "PG Rent": filtered_expenses['pg_rent'].sum(),
                    "Misc Expenses": filtered_expenses['expenses'].sum()
                }
                # Filter out zero values
                expense_totals = {k: v for k, v in expense_totals.items() if v > 0}

                if expense_totals:
                    fig = px.pie(
                        values=list(expense_totals.values()),
                        names=list(expense_totals.keys()),
                        title="Other Expenses Distribution",
                        hole=0.4
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Line chart - EMI and Rent over time
                st.subheader("Fixed Expenses Over Time")
                if len(filtered_expenses) > 1:
                    fig = go.Figure()

                    if filtered_expenses['car_emi'].sum() > 0:
                        fig.add_trace(go.Scatter(
                            x=filtered_expenses['date'],
                            y=filtered_expenses['car_emi'],
                            mode='lines+markers',
                            name='Car EMI',
                            line=dict(color='red')
                        ))

                    if filtered_expenses['pg_rent'].sum() > 0:
                        fig.add_trace(go.Scatter(
                            x=filtered_expenses['date'],
                            y=filtered_expenses['pg_rent'],
                            mode='lines+markers',
                            name='PG Rent',
                            line=dict(color='blue')
                        ))

                    fig.update_layout(
                        title="Monthly Fixed Expenses",
                        xaxis_title="Date",
                        yaxis_title="Amount (₹)",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Detailed table
                st.subheader("Expense Records")
                display_expenses = filtered_expenses.copy()
                display_expenses = display_expenses.sort_values('date', ascending=False)
                st.dataframe(
                    display_expenses[['date', 'expenses', 'car_emi', 'pg_rent', 'total']],
                    use_container_width=True,
                    hide_index=True
                )

# Data entry section
st.header("Add/Update Record")

with st.form("add_record_form"):
    col1, col2 = st.columns(2)

    with col1:
        new_date = st.date_input("Date", value=datetime.today())
        new_rides = st.number_input("Ride Count", min_value=0, value=0)
        new_earnings = st.number_input("Earnings (₹)", min_value=0, value=0)
        new_cng = st.number_input("CNG Expenses (₹)", min_value=0, value=0)

    with col2:
        new_driver_pass = st.number_input("Driver Pass + OLA Subscription (₹)", min_value=0.0, value=0.0)
        new_indrive = st.number_input("InDrive Top-up (₹)", min_value=0.0, value=0.0)
        new_odo_start = st.number_input("Odometer Start (Km)", min_value=0.0, value=0.0)
        new_odo_end = st.number_input("EOD Odometer (Km)", min_value=0.0, value=0.0)

    submitted = st.form_submit_button("Save Record")

    if submitted:
        if add_record(new_date, new_rides, new_earnings, new_cng,
                      new_driver_pass, new_indrive, new_odo_start, new_odo_end):
            st.success(f"Record for {new_date} saved successfully!")
            st.cache_data.clear()
            st.rerun()


# --- Add/Update Other Expenses Section ---
st.header("Add/Update Other Expenses")
with st.form("add_other_expense_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        other_date = st.date_input("Expense Date", key="other_expense_date", value=datetime.today())
    with col2:
        other_car_emi = st.number_input("Car EMI (₹)", min_value=0.0, value=0.0, key="other_car_emi")
        other_pg_rent = st.number_input("PG Rent (₹)", min_value=0.0, value=0.0, key="other_pg_rent")
    with col3:
        other_misc = st.number_input("Miscellaneous Expenses (₹)", min_value=0.0, value=0.0, key="other_misc")
        other_months = st.text_input("Months/Notes", value="", key="other_months")
    other_submitted = st.form_submit_button("Save Other Expense")

def add_other_expense(date, car_emi, pg_rent, expenses, months):
    session = get_session()
    try:
        existing = session.query(OtherExpense).filter_by(date=date).first()
        if existing:
            existing.car_emi = car_emi
            existing.pg_rent = pg_rent
            existing.expenses = expenses
            existing.months = months
        else:
            record = OtherExpense(
                date=date,
                car_emi=car_emi,
                pg_rent=pg_rent,
                expenses=expenses,
                months=months
            )
            session.add(record)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        st.error(f"Error saving other expense: {e}")
        return False
    finally:
        session.close()

if other_submitted:
    if add_other_expense(other_date, other_car_emi, other_pg_rent, other_misc, other_months):
        st.success(f"Other expense for {other_date} saved successfully!")
        st.cache_data.clear()
        st.rerun()

# Raw data view
with st.expander("View Raw Data"):
    if not df.empty:
        st.dataframe(df.sort_values("date", ascending=False), use_container_width=True)
