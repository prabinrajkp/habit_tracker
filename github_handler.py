import requests
import json
import pandas as pd
import datetime
import os


class GithubHandler:
    def __init__(self, token=None, gist_id=None, local=False):
        self.token = token
        self.gist_id = gist_id
        self.local = local
        self.local_dir = "local_data"
        self.filename = "habit_tracker_data.json"
        self.headers = (
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            if self.token
            else {}
        )

        if self.local:
            if not os.path.exists(self.local_dir):
                os.makedirs(self.local_dir)
            self._initialize_local_files()

        self.data = self._load_data()

    def _initialize_local_files(self):
        # Local CSVs for backward compatibility or local-only mode
        habits_path = os.path.join(self.local_dir, "habits.csv")
        logs_path = os.path.join(self.local_dir, "logs.csv")
        metrics_path = os.path.join(self.local_dir, "metrics.csv")

        if not os.path.exists(habits_path):
            pd.DataFrame(columns=["ID", "Habit Name", "Monthly Goal"]).to_csv(
                habits_path, index=False
            )
        if not os.path.exists(logs_path):
            pd.DataFrame(columns=["Date"]).to_csv(logs_path, index=False)
        if not os.path.exists(metrics_path):
            pd.DataFrame(
                columns=[
                    "Date",
                    "Screen Time (min)",
                    "Mood (1-10)",
                    "Energy (1-10)",
                    "Achievements",
                ]
            ).to_csv(metrics_path, index=False)

    def _load_data(self):
        if self.local:
            # For local mode, we still use CSVs to maintain compatibility with existing local data
            return {
                "habits": pd.read_csv(
                    os.path.join(self.local_dir, "habits.csv")
                ).to_dict("records"),
                "logs": pd.read_csv(os.path.join(self.local_dir, "logs.csv")).to_dict(
                    "records"
                ),
                "metrics": pd.read_csv(
                    os.path.join(self.local_dir, "metrics.csv")
                ).to_dict("records"),
            }

        if not self.token or not self.gist_id:
            return {"habits": [], "logs": [], "metrics": []}

        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                gist_data = response.json()
                if self.filename in gist_data["files"]:
                    content = gist_data["files"][self.filename]["content"]
                    return json.loads(content)
            return {"habits": [], "logs": [], "metrics": []}
        except Exception as e:
            print(f"Error loading data from GitHub: {e}")
            return {"habits": [], "logs": [], "metrics": []}

    def _save_data(self):
        if self.local:
            pd.DataFrame(self.data["habits"]).to_csv(
                os.path.join(self.local_dir, "habits.csv"), index=False
            )
            pd.DataFrame(self.data["logs"]).to_csv(
                os.path.join(self.local_dir, "logs.csv"), index=False
            )
            pd.DataFrame(self.data["metrics"]).to_csv(
                os.path.join(self.local_dir, "metrics.csv"), index=False
            )
            return True

        if not self.token or not self.gist_id:
            return False

        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            payload = {
                "files": {self.filename: {"content": json.dumps(self.data, indent=2)}}
            }
            response = requests.patch(url, headers=self.headers, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Error saving data to GitHub: {e}")
            return False

    def get_habits(self):
        return pd.DataFrame(self.data["habits"])

    def update_habit(self, habit_id, name, goal):
        habits = self.data["habits"]
        updated = False
        for h in habits:
            if str(h.get("ID")) == str(habit_id):
                h["Habit Name"] = name
                h["Monthly Goal"] = goal
                # Clean up legacy Type attribute if exists
                if "Type" in h:
                    del h["Type"]
                updated = True
                break
        if not updated:
            habits.append(
                {
                    "ID": habit_id,
                    "Habit Name": name,
                    "Monthly Goal": goal,
                }
            )

        self.data["habits"] = habits
        self._save_data()

    def delete_habit(self, habit_id):
        # 1. Remove from habits list
        self.data["habits"] = [
            h for h in self.data["habits"] if str(h.get("ID")) != str(habit_id)
        ]

        # 2. Clean up logs
        h_id = f"H{habit_id}"
        for log in self.data["logs"]:
            if h_id in log:
                del log[h_id]

        self._save_data()

    def get_logs(self, start_date, end_date):
        df = pd.DataFrame(self.data["logs"])
        if df.empty:
            return df
        df["Date"] = pd.to_datetime(df["Date"])
        mask = (df["Date"] >= pd.to_datetime(start_date)) & (
            df["Date"] <= pd.to_datetime(end_date)
        )
        return df.loc[mask]

    def save_log(self, date, habit_completions):
        date_str = date.strftime("%Y-%m-%d")
        logs = self.data["logs"]

        updated = False
        for l in logs:
            if l.get("Date") == date_str:
                l.update(habit_completions)
                updated = True
                break

        if not updated:
            new_log = {"Date": date_str}
            new_log.update(habit_completions)
            logs.append(new_log)

        self.data["logs"] = logs
        self._save_data()

    def get_metrics(self, start_date, end_date):
        df = pd.DataFrame(self.data["metrics"])
        if df.empty:
            return df
        df["Date"] = pd.to_datetime(df["Date"])
        mask = (df["Date"] >= pd.to_datetime(start_date)) & (
            df["Date"] <= pd.to_datetime(end_date)
        )
        return df.loc[mask]

    def save_metrics(self, date, screen_time, mood, energy, achievements):
        date_str = date.strftime("%Y-%m-%d")
        metrics = self.data["metrics"]

        values = {
            "Date": date_str,
            "Screen Time (min)": screen_time,
            "Mood (1-10)": mood,
            "Energy (1-10)": energy,
            "Achievements": achievements,
        }

        updated = False
        for m in metrics:
            if m.get("Date") == date_str:
                m.update(values)
                updated = True
                break

        if not updated:
            metrics.append(values)

        self.data["metrics"] = metrics
        self._save_data()

    @staticmethod
    def create_or_find_gist(token):
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        filename = "habit_tracker_data.json"

        # 1. Search existing gists
        try:
            response = requests.get("https://api.github.com/gists", headers=headers)
            if response.status_code == 200:
                gists = response.json()
                for gist in gists:
                    if filename in gist["files"]:
                        return gist["id"]

            # 2. Create new gist if not found
            payload = {
                "description": "Habit Tracker Data",
                "public": False,
                "files": {
                    filename: {
                        "content": json.dumps({"habits": [], "logs": [], "metrics": []})
                    }
                },
            }
            response = requests.post(
                "https://api.github.com/gists", headers=headers, json=payload
            )
            if response.status_code == 201:
                return response.json()["id"]
        except Exception as e:
            print(f"Error in GitHub API: {e}")

        return None
