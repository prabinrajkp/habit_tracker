import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def calculate_completion_stats(logs_df, habits_df):
    # Pre-define empty DataFrames with columns to avoid Plotly errors
    empty_consistency = pd.DataFrame(columns=["Date", "Completed Count"])
    empty_top = pd.DataFrame(columns=["Habit Name", "Total Completed"])
    empty_weekly = pd.DataFrame(columns=["Week", "Completed Count"])

    if habits_df is None or habits_df.empty:
        return {
            "overall_rate": 0,
            "daily_consistency": empty_consistency,
            "top_habits": empty_top,
            "weekly_comparison": empty_weekly,
            "good_vs_bad": {"good": 0, "bad": 0},
        }

    # If habits exist but logs don't, we still want to show 0% progress
    if logs_df is None or logs_df.empty:
        return {
            "overall_rate": 0,
            "daily_consistency": empty_consistency,
            "top_habits": empty_top,
            "weekly_comparison": empty_weekly,
            "good_vs_bad": {"good": 0, "bad": 0},
        }

    try:
        habit_cols = [c for c in logs_df.columns if c.startswith("H")]
        if not habit_cols:
            return {
                "overall_rate": 0,
                "daily_consistency": empty_consistency,
                "top_habits": empty_top,
                "weekly_comparison": empty_weekly,
                "good_vs_bad": {"good": 0, "bad": 0},
            }

        # Overall completion rate
        total_cells = logs_df[habit_cols].size
        total_completed = logs_df[habit_cols].sum().sum()
        overall_rate = (total_completed / total_cells) * 100 if total_cells > 0 else 0

        # Daily consistency
        if "Date" in logs_df.columns:
            daily_consistency = (
                logs_df.set_index("Date")[habit_cols].sum(axis=1).reset_index()
            )
            daily_consistency.columns = ["Date", "Completed Count"]
        else:
            daily_consistency = empty_consistency

        # Top habits
        habit_totals = logs_df[habit_cols].sum().reset_index()
        habit_totals.columns = ["H_ID", "Total Completed"]
        habit_totals["ID"] = (
            habit_totals["H_ID"].str.replace("H", "", regex=False).astype(int)
        )

        top_habits = pd.merge(habit_totals, habits_df, on="ID")
        top_habits = top_habits.sort_values(by="Total Completed", ascending=False)

        # Weekly comparison
        if "Date" in logs_df.columns:
            logs_copy = logs_df.copy()
            logs_copy["Date"] = pd.to_datetime(logs_copy["Date"])
            logs_copy["Week"] = logs_copy["Date"].dt.isocalendar().week
            weekly_comp = (
                logs_copy.groupby("Week")[habit_cols].sum().sum(axis=1).reset_index()
            )
            weekly_comp.columns = ["Week", "Completed Count"]
        else:
            weekly_comp = empty_weekly

        # Good vs Bad Tug of War
        if "Type" not in habits_df.columns:
            habits_df["Type"] = "Good"

        good_habit_ids = [
            f"H{row['ID']}" for _, row in habits_df.iterrows() if row["Type"] == "Good"
        ]
        bad_habit_ids = [
            f"H{row['ID']}" for _, row in habits_df.iterrows() if row["Type"] == "Bad"
        ]

        good_total = (
            logs_df[[c for c in good_habit_ids if c in logs_df.columns]].sum().sum()
        )
        bad_total = (
            logs_df[[c for c in bad_habit_ids if c in logs_df.columns]].sum().sum()
        )

        return {
            "overall_rate": overall_rate,
            "daily_consistency": daily_consistency,
            "top_habits": top_habits,
            "weekly_comparison": weekly_comp,
            "good_vs_bad": {"good": good_total, "bad": bad_total},
        }
    except Exception as e:
        st.error(f"Error in analytics: {e}")
        return {
            "overall_rate": 0,
            "daily_consistency": empty_consistency,
            "top_habits": empty_top,
            "weekly_comparison": empty_weekly,
            "good_vs_bad": {"good": 0, "bad": 0},
        }


def create_donut_chart(rate):
    try:
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=["Completed", "Remaining"],
                    values=[rate, max(0, 100 - rate)],
                    hole=0.7,
                    marker_colors=["#2ECC71", "#ECF0F1"],
                )
            ]
        )
        fig.update_layout(
            showlegend=False,
            annotations=[
                dict(text=f"{rate:.1f}%", x=0.5, y=0.5, font_size=20, showarrow=False)
            ],
            margin=dict(t=0, b=0, l=0, r=0),
            height=200,
        )
        return fig
    except:
        return go.Figure()


def create_line_chart(df):
    if df is None or df.empty or "Date" not in df.columns:
        fig = go.Figure()
        fig.update_layout(title="Daily Consistency (No Data)")
        return fig
    try:
        fig = px.line(df, x="Date", y="Completed Count", title="Daily Consistency")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(title=f"Error creating line chart: {e}")
        return fig


def create_bar_chart(df):
    if df is None or df.empty or "Week" not in df.columns:
        fig = go.Figure()
        fig.update_layout(title="Weekly Performance (No Data)")
        return fig
    try:
        fig = px.bar(df, x="Week", y="Completed Count", title="Weekly Performance")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(title=f"Error creating bar chart: {e}")
        return fig


def create_tug_of_war_chart(counts):
    try:
        good = counts.get("good", 0)
        bad = counts.get("bad", 0)
        total = good + bad

        if total == 0:
            fig = go.Figure()
            fig.update_layout(title="Tug of War: No Data")
            return fig

        good_pct = (good / total) * 100
        bad_pct = (bad / total) * 100

        fig = go.Figure()

        # Add "Good" side (Green)
        fig.add_trace(
            go.Bar(
                y=["Balance"],
                x=[good],
                name="Good Habits",
                orientation="h",
                marker_color="#2ECC71",
            )
        )

        # Add "Bad" side (Red)
        fig.add_trace(
            go.Bar(
                y=["Balance"],
                x=[bad],
                name="Bad Habits",
                orientation="h",
                marker_color="#E74C3C",
            )
        )

        fig.update_layout(
            barmode="stack",
            title="⚔️ Good vs Bad: Tug of War",
            xaxis_title="Completions Count",
            yaxis_visible=False,
            height=200,
            showlegend=True,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=50, b=30, l=10, r=10),
        )

        return fig
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(title=f"Error creating Tug of War: {e}")
        return fig


def create_habit_performance_chart(habits_df, logs_df):
    try:
        if habits_df is None or habits_df.empty or logs_df is None or logs_df.empty:
            fig = go.Figure()
            fig.update_layout(title="Habit Performance: No Data")
            return fig

        habit_cols = [c for c in logs_df.columns if c.startswith("H")]
        if not habit_cols:
            return go.Figure()

        completions = logs_df[habit_cols].sum().reset_index()
        completions.columns = ["H_ID", "Completed"]
        completions["ID"] = (
            completions["H_ID"].str.replace("H", "", regex=False).astype(int)
        )

        df = pd.merge(completions, habits_df, on="ID")
        df["Color"] = df["Type"].map({"Good": "#2ECC71", "Bad": "#E74C3C"})

        fig = px.bar(
            df,
            x="Habit Name",
            y="Completed",
            color="Type",
            color_discrete_map={"Good": "#2ECC71", "Bad": "#E74C3C"},
            title="🎯 Habit Performance Breakdown",
        )

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis_title="",
            yaxis_title="Total Days Completed",
        )
        return fig
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(title=f"Error creating performance chart: {e}")
        return fig
