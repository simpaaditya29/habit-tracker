import calendar
from datetime import date, datetime
import json
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# 1. CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(
    page_title="Daily Habit Tracker & Dashboard",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE = "habit_data.json"

DEFAULT_HABITS = []

# ==========================================
# 2. DATA PERSISTENCE & STORAGE LOGIC
# ==========================================
def load_data():
    """Loads saved tracking data from disk or creates default state."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error("Error reading data file. It might be corrupted.")
    return {}


def save_data(data):
    """Saves current state to local JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_month_key(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def initialize_month_data(year: int, month: int, habits: list) -> dict:
    """Creates a blank tracking grid for a given year and month."""
    num_days = calendar.monthrange(year, month)[1]
    days_data = {}
    for day in range(1, num_days + 1):
        d_str = f"{day:02d}"
        days_data[d_str] = {habit: False for habit in habits}

    return {
        "year": year,
        "month": month,
        "habits": habits.copy(),
        "days": days_data,
    }


# ==========================================
# 3. HELPER & CALCULATION FUNCTIONS
# ==========================================
def get_week_number_of_month(year: int, month: int, day: int) -> int:
    """Returns the week index of the month (Week 1 through Week 5/6)."""
    first_day_weekday = calendar.monthrange(year, month)[0]
    adjusted_day = day + first_day_weekday
    return (adjusted_day - 1) // 7 + 1


def calculate_metrics(month_data: dict):
    """Computes daily, weekly, and monthly aggregate metrics."""
    habits = month_data["habits"]
    days_dict = month_data["days"]
    year = month_data["year"]
    month = month_data["month"]

    records = []
    for day_str, habit_status in days_dict.items():
        day_num = int(day_str)
        curr_date = date(year, month, day_num)
        weekday_name = curr_date.strftime("%a")
        week_num = get_week_number_of_month(year, month, day_num)

        row = {
            "Day": day_num,
            "Date": curr_date.strftime("%Y-%m-%d"),
            "Weekday": weekday_name,
            "Week": f"Week {week_num}",
        }
        completed_count = 0
        for h in habits:
            # Safely get status, default to False if habit was newly added
            status = habit_status.get(h, False)
            row[h] = status
            if status:
                completed_count += 1

        row["Completed"] = completed_count
        row["Incomplete"] = len(habits) - completed_count
        row["Percentage"] = (completed_count / len(habits)) * 100 if habits else 0
        records.append(row)

    df = pd.DataFrame(records)
    return df


# ==========================================
# 4. APPLICATION STATE & SIDEBAR
# ==========================================
app_data = load_data()

st.sidebar.title("📌 Habit Settings")

# Year & Month Selector
selected_year = st.sidebar.number_input("Year", min_value=2024, max_value=2035, value=2026)
selected_month = st.sidebar.selectbox(
    "Month",
    options=list(range(1, 13)),
    index=9,  # October
    format_func=lambda m: calendar.month_name[m],
)

month_key = get_month_key(selected_year, selected_month)

# Initialize data if not yet present
if month_key not in app_data:
    app_data[month_key] = initialize_month_data(
        selected_year, selected_month, DEFAULT_HABITS
    )
    save_data(app_data)

current_month_data = app_data[month_key]
active_habits = current_month_data.get("habits", DEFAULT_HABITS)

# Habit Management - Display Active
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Active Habits")
for i, h in enumerate(active_habits, 1):
    st.sidebar.text(f"{i}. {h}")

# Habit Management - Add/Remove
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Manage Habits")

# Add Habit
new_habit = st.sidebar.text_input("Add new habit:", placeholder="e.g. Meditate for 10 mins")
if st.sidebar.button("➕ Add Habit"):
    if new_habit and new_habit not in active_habits:
        active_habits.append(new_habit)
        current_month_data["habits"] = active_habits
        # Backfill the new habit as False for all existing days in the current month
        for day in current_month_data["days"]:
            current_month_data["days"][day][new_habit] = False
        save_data(app_data)
        st.rerun()
    elif new_habit in active_habits:
        st.sidebar.warning("Habit already exists!")

# Remove Habit
habit_to_remove = st.sidebar.selectbox("Remove habit:", [""] + active_habits)
if st.sidebar.button("🗑️ Delete Habit"):
    if habit_to_remove:
        active_habits.remove(habit_to_remove)
        current_month_data["habits"] = active_habits
        save_data(app_data)
        st.rerun()

# Reset & Clear Logic
st.sidebar.markdown("---")
st.sidebar.subheader("⚠️ Reset Controls")
col_reset_btn, col_demo_btn = st.sidebar.columns(2)

if col_reset_btn.button("🔄 Reset Month"):
    app_data[month_key] = initialize_month_data(
        selected_year, selected_month, active_habits
    )
    save_data(app_data)
    st.sidebar.success(f"Reset {calendar.month_name[selected_month]}!")
    st.rerun()

if col_demo_btn.button("✨ Load Sample"):
    num_days = calendar.monthrange(selected_year, selected_month)[1]
    for d in range(1, num_days + 1):
        d_str = f"{d:02d}"
        for h in active_habits:
            app_data[month_key]["days"][d_str][h] = bool(np.random.rand() > 0.35)
    save_data(app_data)
    st.sidebar.success("Sample data generated!")
    st.rerun()

# ==========================================
# 5. MAIN DASHBOARD & TABS
# ==========================================
st.title(f"📊 {calendar.month_name[selected_month]} {selected_year} Habit Tracker")

df_month = calculate_metrics(current_month_data)

tab_dashboard, tab_tracking, tab_weekly = st.tabs(
    ["📈 Dashboard & Insights", "✅ Daily Check-In Grid", "📅 Weekly Breakdown"]
)

# ----------------------------------------------------
# TAB 1: DASHBOARD & INSIGHTS
# ----------------------------------------------------
with tab_dashboard:
    if not active_habits:
        st.warning("No habits found. Add some habits from the sidebar to see metrics.")
    else:
        total_habits_available = len(active_habits) * len(df_month)
        total_habits_checked = int(df_month["Completed"].sum())
        overall_percentage = (
            (total_habits_checked / total_habits_available) * 100
            if total_habits_available > 0
            else 0
        )

        habit_sums = {h: df_month[h].sum() for h in active_habits}
        top_habit = (
            max(habit_sums, key=habit_sums.get) if habit_sums and max(habit_sums.values()) > 0 else "N/A"
        )
        top_habit_count = habit_sums[top_habit] if top_habit != "N/A" else 0

        peak_day_row = df_month.loc[df_month["Completed"].idxmax()]
        peak_day_str = f"Day {peak_day_row['Day']} ({peak_day_row['Weekday']})"

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Overall Completion", f"{overall_percentage:.1f}%")
        kpi2.metric("Total Habits Checked", f"{total_habits_checked} / {total_habits_available}")
        kpi3.metric("Leading Habit", f"{top_habit}", f"{top_habit_count} completions")
        kpi4.metric("Peak Performance Day", peak_day_str, f"{peak_day_row['Completed']} completed")

        st.markdown("---")

        st.subheader("Weekly Performance Gauges")
        weekly_agg = df_month.groupby("Week")[["Completed", "Incomplete"]].sum()
        weeks = sorted(weekly_agg.index.tolist())

        week_cols = st.columns(len(weeks))
        for idx, wk in enumerate(weeks):
            with week_cols[idx]:
                wk_comp = int(weekly_agg.loc[wk, "Completed"])
                wk_incomp = int(weekly_agg.loc[wk, "Incomplete"])
                wk_total = wk_comp + wk_incomp
                wk_rate = (wk_comp / wk_total * 100) if wk_total > 0 else 0

                fig_donut = go.Figure(
                    go.Pie(
                        values=[wk_comp, wk_incomp],
                        labels=["Done", "Pending"],
                        hole=0.65,
                        marker_colors=["#2ECC71", "#E0E0E0"],
                        textinfo="none",
                    )
                )
                fig_donut.update_layout(
                    showlegend=False,
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=160,
                    annotations=[
                        dict(
                            text=f"<b>{wk_rate:.0f}%</b>",
                            x=0.5,
                            y=0.5,
                            font_size=18,
                            showarrow=False,
                        )
                    ],
                )
                st.caption(f"**{wk}** ({wk_comp}/{wk_total})")
                st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("---")

        st.subheader("Activity Performance Trajectory")
        col_view_opt, col_habit_filter = st.columns([1, 2])
        with col_view_opt:
            view_mode = st.radio(
                "Graph View", ["Daily Status", "Cumulative Trend"], horizontal=True
            )
        with col_habit_filter:
            selected_habit_view = st.multiselect(
                "Filter Activities",
                options=active_habits,
                default=active_habits[:3] if len(active_habits) >= 3 else active_habits,
            )

        if selected_habit_view:
            plot_df = pd.DataFrame({"Day": df_month["Day"]})
            for h in selected_habit_view:
                if view_mode == "Cumulative Trend":
                    plot_df[h] = df_month[h].astype(int).cumsum()
                else:
                    plot_df[h] = df_month[h].astype(int)

            fig_line = px.line(
                plot_df,
                x="Day",
                y=selected_habit_view,
                markers=True,
                title=f"Performance Trajectory ({view_mode})",
                labels={"value": "Completions", "variable": "Habit"},
            )
            fig_line.update_layout(height=400, hovermode="x unified")
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Select at least one habit above to view trajectory.")

# ----------------------------------------------------
# TAB 2: INTERACTIVE DAILY CHECK-IN GRID
# ----------------------------------------------------
with tab_tracking:
    if not active_habits:
        st.warning("Add some habits in the sidebar to start tracking!")
    else:
        st.subheader("Daily Habit Logging")
        st.caption("Toggle checkboxes below to record daily habit progress.")

        days_in_month = calendar.monthrange(selected_year, selected_month)[1]
        day_selected = st.slider("Select Day of Month to Edit", 1, days_in_month, value=1)
        d_str = f"{day_selected:02d}"

        selected_day_date = date(selected_year, selected_month, day_selected)
        st.markdown(
            f"#### Editing: **{selected_day_date.strftime('%A, %d %B %Y')}**"
        )

        day_col1, day_col2 = st.columns(2)
        updated = False

        for idx, habit in enumerate(active_habits):
            target_col = day_col1 if idx % 2 == 0 else day_col2
            current_val = current_month_data["days"][d_str].get(habit, False)

            new_val = target_col.checkbox(
                habit, value=current_val, key=f"chk_{d_str}_{habit}"
            )
            if new_val != current_val:
                current_month_data["days"][d_str][habit] = new_val
                updated = True

        if updated:
            save_data(app_data)
            st.success("Changes saved!")
            st.rerun()

        st.markdown("---")
        st.subheader("Full Month Overview Table")

        display_df = df_month[["Day", "Weekday", "Week"] + active_habits + ["Completed", "Percentage"]]
        display_df["Percentage"] = display_df["Percentage"].map(lambda x: f"{x:.1f}%")
        st.dataframe(display_df, use_container_width=True, height=450)

# ----------------------------------------------------
# TAB 3: WEEKLY SUMMARY BREAKDOWN
# ----------------------------------------------------
with tab_weekly:
    if not active_habits:
        st.info("Add habits to view weekly summaries.")
    else:
        st.subheader("Weekly Habit Consistency Summary")

        weekly_summary = []
        for wk, group in df_month.groupby("Week"):
            total_slots = len(group) * len(active_habits)
            done = int(group["Completed"].sum())
            missed = total_slots - done
            rate = (done / total_slots * 100) if total_slots > 0 else 0.0

            weekly_summary.append(
                {
                    "Week": wk,
                    "Days In Week": len(group),
                    "Habits Completed": done,
                    "Habits Incomplete": missed,
                    "Completion Rate": f"{rate:.1f}%",
                }
            )

        st.table(pd.DataFrame(weekly_summary))