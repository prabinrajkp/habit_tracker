import streamlit as st
import datetime
import calendar
import pandas as pd
import json
import os
import random
from github_handler import GithubHandler
from analytics import (
    calculate_completion_stats,
    create_donut_chart,
    create_line_chart,
    create_bar_chart,
    create_tug_of_war_chart,
    create_habit_performance_chart,
)

# VERSION 1.4 - GitHub Gist Backend
st.set_page_config(page_title="Ultimate Habit Tracker", layout="wide")

# Custom CSS for aesthetics
st.markdown(
    """
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        border-radius: 10px;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .setup-box {
        background-color: #e8f5e9;
        padding: 20px;
        border-left: 5px solid #4caf50;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "git_token" not in st.session_state:
    st.session_state.git_token = ""
if "gist_id" not in st.session_state:
    st.session_state.gist_id = ""
if "local_mode" not in st.session_state:
    st.session_state.local_mode = False


def main():
    st.title("🚀 Ultimate Habit Tracker")

    # Removed local config file loading for session-based security

    with st.sidebar:
        st.subheader("⚙️ Configuration")

        st.session_state.local_mode = st.toggle(
            "Local Mode (Offline)",
            value=st.session_state.local_mode,
            help="Use local CSV files instead of GitHub sync",
        )

        st.markdown("---")
        st.markdown("### ☁️ GitHub Sync")
        git_token_input = st.text_input(
            "GitHub Token (PAT)",
            value=st.session_state.git_token,
            type="password",
            help="Your Personal Access Token with 'gist' scope",
        )

        if st.button("Connect & Initialize"):
            if git_token_input:
                with st.spinner("Connecting to GitHub..."):
                    gist_id = GithubHandler.create_or_find_gist(git_token_input)
                    if gist_id:
                        st.session_state.git_token = git_token_input
                        st.session_state.gist_id = gist_id
                        st.session_state.local_mode = False
                        st.success("Successfully connected to GitHub!")
                        st.rerun()
                    else:
                        st.error(
                            "Failed to connect. Check your token permissions (must have 'gist' scope)."
                        )
            else:
                st.error("Please enter a GitHub Token.")

        st.divider()

        with st.expander("🔑 How to get a GitHub Token?"):
            st.markdown(
                """
            1. [Click here](https://github.com/settings/tokens/new?description=HabitTracker&scopes=gist) to go to GitHub Token creation.
            2. Or go to **Settings > Developer Settings > Personal access tokens > Tokens (classic)**.
            3. Generate a new token with the **'gist'** scope.
            4. Copy the token and paste it above!
            """
            )

        st.divider()
        st.subheader("📅 Calendar Settings")
        year = st.selectbox(
            "Year", range(2024, 2030), index=datetime.datetime.now().year - 2024
        )
        month_name = st.selectbox(
            "Month", calendar.month_name[1:], index=datetime.datetime.now().month - 1
        )
        month = list(calendar.month_name).index(month_name)

    # Initialize handler
    if st.session_state.local_mode:
        handler = GithubHandler(local=True)
    elif st.session_state.git_token and st.session_state.gist_id:
        handler = GithubHandler(
            token=st.session_state.git_token, gist_id=st.session_state.gist_id
        )
    else:
        st.markdown(
            """
        <div class="setup-box">
            <h3>Welcome! Let's get synced.</h3>
            <p>To use cloud sync across your devices:</p>
            <ol>
                <li>Get a <b>GitHub Token</b> (30 seconds in the sidebar guide).</li>
                <li>Paste it in the sidebar and click <b>Connect</b>.</li>
                <li>Your data will be stored securely and privately in a GitHub Gist.</li>
            </ol>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.info("💡 You can also try **Local Mode** to get started offline.")
        st.stop()

    # Load data
    try:
        habits_df = handler.get_habits()

        start_date = datetime.date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime.date(year, month, last_day)

        logs_df = handler.get_logs(start_date, end_date)
        metrics_df = handler.get_metrics(start_date, end_date)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📅 Daily Tracker", "📊 Dashboard", "⚙️ Habit Settings"])

    with tab3:
        st.subheader("Configure Your Habits")
        st.info("Your settings are synced to the cloud automatically.")

        new_habit_name = st.text_input("New Habit Name", key="new_habit_name")
        new_habit_goal = st.number_input(
            "Monthly Goal (days)",
            min_value=1,
            max_value=31,
            value=20,
            key="new_habit_goal",
        )

        if st.button("Add Habit"):
            if new_habit_name:
                next_id = 1
                if habits_df is not None and not habits_df.empty:
                    try:
                        next_id = int(habits_df["ID"].max()) + 1
                    except:
                        next_id = 1
                handler.update_habit(next_id, new_habit_name, new_habit_goal)
                st.success(f"Added '{new_habit_name}'!")
                st.rerun()
            else:
                st.error("Please enter a habit name.")

        if habits_df is not None and not habits_df.empty:
            st.write("Current Habits:")
            # Remove legacy "Type" column for clean UI
            display_df = habits_df.copy()
            if "Type" in display_df.columns:
                display_df = display_df.drop(columns=["Type"])

            edited_habits = st.data_editor(
                display_df,
                key="habit_editor",
                hide_index=True,
            )
            if st.button("Save Changes"):
                for _, row in edited_habits.iterrows():
                    handler.update_habit(
                        row["ID"],
                        row["Habit Name"],
                        row["Monthly Goal"],
                    )
                st.success("Updated habits!")
                st.rerun()

        if habits_df is not None and not habits_df.empty:
            st.divider()
            st.subheader("🗑️ Delete a Habit")
            habit_to_delete = st.selectbox(
                "Select habit to remove",
                options=habits_df["Habit Name"].tolist(),
                key="delete_habit_select",
            )

            if st.button("Delete Selected Habit", type="secondary"):
                h_id = habits_df[habits_df["Habit Name"] == habit_to_delete][
                    "ID"
                ].values[0]
                handler.delete_habit(h_id)
                st.warning(f"Deleted habit: {habit_to_delete}")
                st.rerun()

        # DANGER ZONE
        st.divider()
        with st.expander("⚠️ Danger Zone - Delete All Data", expanded=False):
            st.error(
                "This action will permanently delete ALL habits, logs, and metrics."
            )

            # Generate random numbers for verification if not already present
            if "reset_n1" not in st.session_state:
                st.session_state.reset_n1 = random.randint(1, 50)
            if "reset_n2" not in st.session_state:
                st.session_state.reset_n2 = random.randint(1, 50)

            n1 = st.session_state.reset_n1
            n2 = st.session_state.reset_n2

            st.write(f"To confirm, please solve: **{n1} + {n2} = ?**")
            user_answer = st.text_input(
                "Enter the result here:", key="reset_verification"
            )

            if st.button("🔥 ERASE EVERYTHING", type="primary"):
                try:
                    if int(user_answer) == (n1 + n2):
                        if handler.reset_data():
                            st.success("All data has been erased successfully.")
                            # Clear reset state to generate new numbers if they ever come back
                            del st.session_state.reset_n1
                            del st.session_state.reset_n2
                            st.rerun()
                        else:
                            st.error(
                                "Failed to sync reset to GitHub. Please try again."
                            )
                    else:
                        st.error("Incorrect verification answer. Data NOT deleted.")
                except ValueError:
                    st.error("Please enter a valid number.")

    with tab1:
        st.subheader(f"Tracking for {month_name} {year}")

        if habits_df is None or habits_df.empty:
            st.warning("Go to 'Habit Settings' to add some habits first!")
        else:
            selected_date = st.date_input(
                "Select Date to Log",
                datetime.date.today(),
                min_value=start_date,
                max_value=end_date,
                key="log_date_selector",
            )

            day_log = (
                logs_df[logs_df["Date"] == pd.to_datetime(selected_date)]
                if logs_df is not None
                and not logs_df.empty
                and "Date" in logs_df.columns
                else pd.DataFrame()
            )
            day_metrics = (
                metrics_df[metrics_df["Date"] == pd.to_datetime(selected_date)]
                if metrics_df is not None
                and not metrics_df.empty
                and "Date" in metrics_df.columns
                else pd.DataFrame()
            )

            col1, col2 = st.columns([2, 1])

            with col1:
                st.write("Habit List")
                habit_completions = {}
                for _, row in habits_df.iterrows():
                    h_id = f"H{int(row['ID'])}"
                    current_val = "Pending"
                    if not day_log.empty and h_id in day_log.columns:
                        try:
                            val = day_log[h_id].values[0]
                            if val == True or val == "Yes":
                                current_val = "Yes"
                            elif val == False or val == "No":
                                current_val = "No"
                        except:
                            current_val = "Pending"

                    st.markdown(
                        f"**<span style='color:#2ECC71;'>🚀 {row['Habit Name']}</span>**",
                        unsafe_allow_html=True,
                    )
                    habit_completions[h_id] = st.radio(
                        "Status",
                        ["Pending", "Yes", "No"],
                        index=["Pending", "Yes", "No"].index(current_val),
                        key=f"radio_{h_id}",
                        horizontal=True,
                        label_visibility="collapsed",
                    )

            with col2:
                st.write("Other Metrics")

                def get_metric_val(df, col, default):
                    if not df.empty and col in df.columns:
                        try:
                            val = df[col].values[0]
                            return int(val) if pd.notnull(val) else default
                        except:
                            return default
                    return default

                screen_time = st.number_input(
                    "Screen Time (min)",
                    min_value=0,
                    value=get_metric_val(day_metrics, "Screen Time (min)", 0),
                )
                mood = st.slider(
                    "Mood (1-10)",
                    1,
                    10,
                    value=get_metric_val(day_metrics, "Mood (1-10)", 5),
                )
                energy = st.slider(
                    "Energy (1-10)",
                    1,
                    10,
                    value=get_metric_val(day_metrics, "Energy (1-10)", 5),
                )

                ach_val = ""
                if not day_metrics.empty and "Achievements" in day_metrics.columns:
                    ach_val = day_metrics["Achievements"].values[0]
                    if pd.isnull(ach_val):
                        ach_val = ""

                achievements = st.text_area("Achievements", value=ach_val)

            if st.button("Save Daily Log", type="primary"):
                with st.spinner("Saving to cloud..."):
                    handler.save_log(selected_date, habit_completions)
                    handler.save_metrics(
                        selected_date, screen_time, mood, energy, achievements
                    )
                st.success("Saved successfully!")
                st.rerun()

    with tab2:
        st.subheader("Visual Dashboard")
        stats = calculate_completion_stats(logs_df, habits_df)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.plotly_chart(
                create_donut_chart(stats["overall_rate"]), use_container_width=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Total Habits", len(habits_df) if habits_df is not None else 0)
            st.metric("Days Logged", len(logs_df) if logs_df is not None else 0)
            st.markdown("</div>", unsafe_allow_html=True)

        st.plotly_chart(
            create_tug_of_war_chart(stats["good_vs_bad"]), use_container_width=True
        )

        st.plotly_chart(
            create_habit_performance_chart(habits_df, logs_df),
            use_container_width=True,
        )

        with c3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            if not stats["top_habits"].empty:
                st.write("Top Habits:")
                st.dataframe(
                    stats["top_habits"][["Habit Name", "Total Completed"]].head(5),
                    hide_index=True,
                )
            else:
                st.write("Top Habits: No data yet")
            st.markdown("</div>", unsafe_allow_html=True)

        st.plotly_chart(
            create_line_chart(stats["daily_consistency"]), use_container_width=True
        )
        st.plotly_chart(
            create_bar_chart(stats["weekly_comparison"]), use_container_width=True
        )


if __name__ == "__main__":
    main()
