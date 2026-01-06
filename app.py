import streamlit as st
import datetime
import calendar
import pandas as pd
import json
import os
import random
import uuid
from fpdf import FPDF
from github_handler import GithubHandler
from analytics import (
    calculate_completion_stats,
    create_donut_chart,
    create_line_chart,
    create_bar_chart,
    create_tug_of_war_chart,
    create_habit_performance_chart,
    create_overall_trends_chart,
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


def login_page():
    st.markdown(
        """
        <div style='text-align: center; padding: 20px;'>
            <h1 style='font-size: 3rem;'>🚀 Habit Tracker</h1>
            <p style='color: #666; font-size: 1.2rem;'>Your journey to a better you starts here.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.subheader("🔑 Connect Your Account")

        local_mode = st.toggle(
            "Local Mode (Offline)",
            value=st.session_state.local_mode,
            help="Use local storage instead of GitHub sync",
        )

        if not local_mode:
            st.markdown("---")
            st.markdown("### ☁️ GitHub Sync")
            git_token_input = st.text_input(
                "GitHub Token (PAT)",
                value=st.session_state.git_token,
                type="password",
                help="Your Personal Access Token with 'gist' scope",
            )

            if st.button(
                "Connect & Start Tracking", type="primary", use_container_width=True
            ):
                if git_token_input:
                    with st.spinner("Connecting to GitHub..."):
                        gist_id = GithubHandler.create_or_find_gist(git_token_input)
                        if gist_id:
                            st.session_state.git_token = git_token_input
                            st.session_state.gist_id = gist_id
                            st.session_state.local_mode = False
                            st.success("Successfully connected!")
                            st.rerun()
                        else:
                            st.error("Failed to connect. Check your token permissions.")
                else:
                    st.error("Please enter a GitHub Token.")

            with st.expander("❓ How to get a token?"):
                st.markdown(
                    """
                1. [Click here](https://github.com/settings/tokens/new?description=HabitTracker&scopes=gist) to go to GitHub Token creation.
                2. Generate a token with the **'gist'** scope.
                3. Copy and paste it above!
                """
                )
        else:
            if st.button(
                "Start Local Session", type="primary", use_container_width=True
            ):
                st.session_state.local_mode = True
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def main():
    # Authentication check
    if not st.session_state.local_mode and not (
        st.session_state.git_token and st.session_state.gist_id
    ):
        login_page()
        st.stop()

    # Header with Title and Disconnect
    h_col1, h_col2 = st.columns([4, 1])
    with h_col1:
        st.title("🚀 Ultimate Habit Tracker")
    with h_col2:
        if st.button("Logout / Disconnect"):
            st.session_state.git_token = ""
            st.session_state.gist_id = ""
            st.session_state.local_mode = False
            st.rerun()

    # Calendar Settings in Header columns
    cal_col1, cal_col2, cal_col3 = st.columns([2, 2, 8])
    with cal_col1:
        year = st.selectbox(
            "Year", range(2024, 2030), index=datetime.datetime.now().year - 2024
        )
    with cal_col2:
        month_name = st.selectbox(
            "Month", calendar.month_name[1:], index=datetime.datetime.now().month - 1
        )
    month = list(calendar.month_name).index(month_name)
    start_date = datetime.date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = datetime.date(year, month, last_day)

    # Initialize handler
    if st.session_state.local_mode:
        handler = GithubHandler(local=True)
    else:
        handler = GithubHandler(
            token=st.session_state.git_token, gist_id=st.session_state.gist_id
        )

    # Load data for specific month
    try:
        handler.load_month(year, month)
        habits_df = handler.get_habits()

        logs_df = handler.get_logs()
        metrics_df = handler.get_metrics()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        if st.button("Return to Login"):
            st.session_state.git_token = ""
            st.session_state.local_mode = False
            st.rerun()
        st.stop()

    tab_guide, tab1, tab2, tab4, tab5, tab3 = st.tabs(
        [
            "🏠 Guide",
            "📅 Daily Tracker",
            "📊 Dashboard",
            "📈 Overall Analysis",
            "🖋️ Daily Journal",
            "⚙️ Habit Settings",
        ]
    )

    with tab_guide:
        st.markdown(
            """
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 20px; color: white; margin-bottom: 30px; box-shadow: 0 10px 20px rgba(0,0,0,0.2);'>
                <h2 style='margin: 0; font-size: 2.5rem;'>Welcome to Your Ultimate Habit Tracker 🚀</h2>
                <p style='font-size: 1.2rem; opacity: 0.9;'>Master your routines, track your progress, and unlock your full potential.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                """
                ### 🌟 Why This App?
                Most habit trackers store your data on their servers. **We don't.** 
                Your journey is yours alone. We use **GitHub Gists** to ensure:
                - **Privacy First**: Only you own your data.
                - **Cloud Sync**: Access from any device with your token.
                - **Total Control**: Edit your data directly on GitHub anytime.
                """
            )

            st.markdown(
                """
                ### 🛠️ Key Features
                - **🎯 Smart Habits**: Track 12+ research-backed daily habits out of the box.
                - **📊 Deep Analytics**: Beautiful charts to visualize your consistency and trends.
                - **🖋️ Daily Journal**: Reflect on your day and export your monthly thoughts as a PDF.
                - **📈 Overall Trends**: See how your mood and habits correlate over months.
                """
            )

        with col2:
            st.markdown(
                """
                ### 🚀 Quick Start Guide
                1. **Set Your Goals**: Go to `⚙️ Habit Settings` to tailor your list.
                2. **Track Daily**: Use `📅 Daily Tracker` to log your wins and metrics.
                3. **Reflect**: Spend 2 minutes in `🖋️ Daily Journal` to clear your mind.
                4. **Analyze**: Check `📊 Dashboard` weekly to see your progress.
                """
            )

            st.info(
                "💡 **Pro Tip**: Consistency beats intensity. Even if you miss a day, just start again tomorrow!"
            )

        st.divider()
        st.subheader("🌈 Your Path to Success")
        st.write(
            "Building habits is the compound interest of self-improvement. "
            "Whether it's drinking more water or mastering deep work, "
            "every checkmark is a vote for the person you want to become."
        )

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
                next_id = str(uuid.uuid4())
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
                    h_id = f"H{row['ID']}"
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
            st.metric("Total Months Tracked", len(handler.get_all_available_months()))
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

    with tab4:
        st.subheader("📈 Long-term Habit Analysis")
        st.info("This view aggregates all your historical data from every month.")

        with st.spinner("Fetching historical data..."):
            all_history = handler.load_all_history()

        if not all_history["logs"]:
            st.warning(
                "No historical data found yet. Keep tracking to see your progress trends!"
            )
        else:
            fig_trends = create_overall_trends_chart(all_history)
            st.plotly_chart(fig_trends, use_container_width=True)

            # Additional insights
            st.divider()
            st.subheader("Month-by-Month Summary")
            all_months = handler.get_all_available_months()
            summary_data = []
            for y, m in all_months:
                import calendar as cal

                m_name = cal.month_name[m]
                summary_data.append(
                    {"Month": f"{m_name} {y}", "Source": f"data_{y}_{m:02d}.json"}
                )

            st.table(pd.DataFrame(summary_data))

    with tab5:
        st.subheader(f"🖋️ Daily Journal - {month_name} {year}")

        # Date selector for journal
        j_date = st.date_input(
            "Journal Date",
            datetime.date.today(),
            min_value=start_date,
            max_value=end_date,
            key="journal_date_selector",
        )

        # Load journal for the selected month
        journal_data = handler.load_journal(year, month)
        date_str = j_date.strftime("%Y-%m-%d")
        current_entry = journal_data.get(date_str, "")

        journal_content = st.text_area(
            "Write your thoughts here...",
            value=current_entry,
            height=300,
            key=f"journal_input_{date_str}",
        )

        if st.button("Save Journal Entry", type="primary"):
            with st.spinner("Saving journal..."):
                handler.save_journal(j_date, journal_content)
            st.success("Journal entry saved!")
            st.rerun()

        st.divider()
        st.subheader("📥 Export Journal")

        if st.button("Generate Monthly PDF"):
            if not journal_data:
                st.warning("No journal entries found for this month.")
            else:
                try:
                    pdf = FPDF()
                    pdf.set_auto_page_break(auto=True, margin=15)
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(
                        0,
                        10,
                        f"Habit Tracker Journal - {month_name} {year}",
                        ln=True,
                        align="C",
                    )
                    pdf.ln(10)

                    # Sort entries by date
                    for d_str in sorted(journal_data.keys()):
                        content = journal_data[d_str]
                        if content.strip():
                            pdf.set_font("Arial", "B", 12)
                            pdf.cell(0, 10, f"Date: {d_str}", ln=True)
                            pdf.set_font("Arial", "", 11)
                            pdf.multi_cell(0, 8, content)
                            pdf.ln(5)

                    pdf_output = pdf.output()
                    st.download_button(
                        label="Download PDF",
                        data=bytes(pdf_output),
                        file_name=f"Journal_{year}_{month:02d}.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")

        # Quick view of past entries this month
        if journal_data:
            with st.expander("📖 View Past Entries (This Month)"):
                for d_str in sorted(journal_data.keys(), reverse=True):
                    if journal_data[d_str].strip():
                        st.markdown(f"**{d_str}**")
                        st.info(journal_data[d_str])


if __name__ == "__main__":
    main()
