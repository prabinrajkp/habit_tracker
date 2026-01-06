import requests
import json
import pandas as pd
import datetime
import os
import uuid


class GithubHandler:
    def __init__(self, token=None, gist_id=None, local=False):
        self.token = token
        self.gist_id = gist_id
        self.local = local
        self.local_dir = "local_data"
        self.old_filename = "habit_tracker_data.json"
        self.habits_filename = "habits.json"

        self.headers = (
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
            if self.token
            else {}
        )

        if self.local and not os.path.exists(self.local_dir):
            os.makedirs(self.local_dir)

        self.habits = []
        self.current_month_data = {"logs": [], "metrics": []}
        self.current_journal_data = {}
        self.current_year = None
        self.current_month = None

        self._initial_load_and_migrate()

    def _initial_load_and_migrate(self):
        """Loads habits and checks if migration from old single-file format is needed."""
        fetch_all = self._fetch_all_gist_files()

        # 1. Check for legacy file and migrate if needed
        if self.old_filename in fetch_all:
            legacy_data = json.loads(fetch_all[self.old_filename])
            self.habits = legacy_data.get("habits", [])

            # Split logs/metrics by month
            logs = legacy_data.get("logs", [])
            metrics = legacy_data.get("metrics", [])

            monthly_buckets = {}
            for entry in logs + metrics:
                d = datetime.datetime.strptime(entry["Date"], "%Y-%m-%d")
                key = f"data_{d.year}_{d.month:02d}.json"
                if key not in monthly_buckets:
                    monthly_buckets[key] = {"logs": [], "metrics": []}

                if "Mood (1-10)" in entry:  # Metric
                    monthly_buckets[key]["metrics"].append(entry)
                else:  # Log
                    monthly_buckets[key]["logs"].append(entry)

            # Save migrated files
            self._save_habits()
            for filename, data in monthly_buckets.items():
                self._upload_to_gist(filename, data)

            # Delete legacy file
            self._delete_from_gist(self.old_filename)
        else:
            # 2. Normal load of habits
            if self.habits_filename in fetch_all:
                self.habits = json.loads(fetch_all[self.habits_filename])
            elif self.local:
                habits_path = os.path.join(self.local_dir, self.habits_filename)
                if os.path.exists(habits_path):
                    with open(habits_path, "r") as f:
                        self.habits = json.load(f)

            # 3. If still empty, populate with default habits from JSON
            if not self.habits:
                default_file = "default_habits.json"
                if os.path.exists(default_file):
                    with open(default_file, "r") as f:
                        defaults = json.load(f)
                        # Add IDs to defaults
                        for h in defaults:
                            if "ID" not in h:
                                h["ID"] = str(uuid.uuid4())
                        self.habits = defaults
                else:
                    self.habits = []
                self._save_habits()

    def _fetch_all_gist_files(self):
        """Returns a dict of filename -> content for all files in the gist."""
        if self.local:
            files = {}
            if os.path.exists(self.local_dir):
                for f in os.listdir(self.local_dir):
                    if f.endswith(".json"):
                        with open(os.path.join(self.local_dir, f), "r") as file:
                            files[f] = file.read()
            return files

        if not self.token or not self.gist_id:
            return {}
        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                gist_data = response.json()
                return {
                    name: info["content"] for name, info in gist_data["files"].items()
                }
        except:
            pass
        return {}

    def load_month(self, year, month):
        """Loads logs and metrics for a specific month."""
        self.current_year = year
        self.current_month = month
        filename = f"data_{year}_{month:02d}.json"

        files = self._fetch_all_gist_files()
        if filename in files:
            self.current_month_data = json.loads(files[filename])
        else:
            self.current_month_data = {"logs": [], "metrics": []}
        return self.current_month_data

    def load_journal(self, year, month):
        """Loads journal entries for a specific month."""
        filename = f"journal_{year}_{month:02d}.json"
        files = self._fetch_all_gist_files()
        if filename in files:
            self.current_journal_data = json.loads(files[filename])
        else:
            self.current_journal_data = {}
        return self.current_journal_data

    def get_all_available_months(self):
        """Scans gist files for all data_YYYY_MM.json files and returns a list of (year, month)."""
        files = self._fetch_all_gist_files()
        months = []
        for f in files.keys():
            if f.startswith("data_") and f.endswith(".json"):
                parts = f.replace("data_", "").replace(".json", "").split("_")
                if len(parts) == 2:
                    months.append((int(parts[0]), int(parts[1])))
        return sorted(months)

    def load_all_history(self):
        """Fetches every monthly data file and returns a merged dictionary of ALL logs and metrics."""
        files = self._fetch_all_gist_files()
        all_logs = []
        all_metrics = []
        for f, content in files.items():
            if f.startswith("data_") and f.endswith(".json"):
                month_data = json.loads(content)
                all_logs.extend(month_data.get("logs", []))
                all_metrics.extend(month_data.get("metrics", []))
        return {"logs": all_logs, "metrics": all_metrics}

    def _save_habits(self):
        self._upload_to_gist(self.habits_filename, self.habits)

    def _save_current_month(self):
        if self.current_year and self.current_month:
            filename = f"data_{self.current_year}_{self.current_month:02d}.json"
            self._upload_to_gist(filename, self.current_month_data)

    def _upload_to_gist(self, filename, data):
        if self.local:
            with open(os.path.join(self.local_dir, filename), "w") as f:
                json.dump(data, f, indent=2)
            return True

        if not self.token or not self.gist_id:
            return False
        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            payload = {"files": {filename: {"content": json.dumps(data, indent=2)}}}
            response = requests.patch(url, headers=self.headers, json=payload)
            return response.status_code == 200
        except:
            return False

    def _delete_from_gist(self, filename):
        if self.local:
            path = os.path.join(self.local_dir, filename)
            if os.path.exists(path):
                os.remove(path)
            return True
        try:
            url = f"https://api.github.com/gists/{self.gist_id}"
            payload = {"files": {filename: None}}
            requests.patch(url, headers=self.headers, json=payload)
        except:
            pass

    def get_habits(self):
        return pd.DataFrame(self.habits)

    def update_habit(self, habit_id, name, goal):
        updated = False
        for h in self.habits:
            if str(h.get("ID")) == str(habit_id):
                h["Habit Name"] = name
                h["Monthly Goal"] = goal
                updated = True
                break
        if not updated:
            self.habits.append(
                {"ID": habit_id, "Habit Name": name, "Monthly Goal": goal}
            )
        self._save_habits()

    def delete_habit(self, habit_id):
        self.habits = [h for h in self.habits if str(h.get("ID")) != str(habit_id)]
        self._save_habits()
        # Note: We don't clean up logs across all monthly files for performance,
        # analytics should handle missing IDs.

    def reset_data(self):
        files = self._fetch_all_gist_files()
        for f in files.keys():
            if f.endswith(".json"):
                self._delete_from_gist(f)
        self.habits = []
        self.current_month_data = {"logs": [], "metrics": []}
        return True

    def get_logs(self, start_date=None, end_date=None):
        # Optimized to use current loaded month unless dates suggest otherwise
        df = pd.DataFrame(self.current_month_data["logs"])
        if df.empty:
            return df
        df["Date"] = pd.to_datetime(df["Date"])
        if start_date and end_date:
            mask = (df["Date"] >= pd.to_datetime(start_date)) & (
                df["Date"] <= pd.to_datetime(end_date)
            )
            return df.loc[mask]
        return df

    def save_log(self, date, habit_completions):
        date_str = date.strftime("%Y-%m-%d")
        # Ensure we are saving to the correct month file
        if date.year != self.current_year or date.month != self.current_month:
            self.load_month(date.year, date.month)

        logs = self.current_month_data["logs"]
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

        self.current_month_data["logs"] = logs
        self._save_current_month()

    def get_metrics(self, start_date=None, end_date=None):
        df = pd.DataFrame(self.current_month_data["metrics"])
        if df.empty:
            return df
        df["Date"] = pd.to_datetime(df["Date"])
        if start_date and end_date:
            mask = (df["Date"] >= pd.to_datetime(start_date)) & (
                df["Date"] <= pd.to_datetime(end_date)
            )
            return df.loc[mask]
        return df

    def save_metrics(self, date, screen_time, mood, energy, achievements):
        date_str = date.strftime("%Y-%m-%d")
        if date.year != self.current_year or date.month != self.current_month:
            self.load_month(date.year, date.month)

        metrics = self.current_month_data["metrics"]
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

        self.current_month_data["metrics"] = metrics
        self._save_current_month()

    def save_journal(self, date, content):
        date_str = date.strftime("%Y-%m-%d")
        year, month = date.year, date.month
        filename = f"journal_{year}_{month:02d}.json"

        # Check if we need to load a different month's journal
        current_journal_filename = (
            f"journal_{self.current_year}_{self.current_month:02d}.json"
            if self.current_year
            else None
        )
        if filename != current_journal_filename:
            self.load_journal(year, month)

        self.current_journal_data[date_str] = content
        self._upload_to_gist(filename, self.current_journal_data)

    @staticmethod
    def create_or_find_gist(token):
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        # Check for new version file first
        try:
            response = requests.get("https://api.github.com/gists", headers=headers)
            if response.status_code == 200:
                gists = response.json()
                for gist in gists:
                    if (
                        "habits.json" in gist["files"]
                        or "habit_tracker_data.json" in gist["files"]
                    ):
                        return gist["id"]

            # Create new if none found
            payload = {
                "description": "Habit Tracker Data",
                "public": False,
                "files": {"habits.json": {"content": "[]"}},
            }
            response = requests.post(
                "https://api.github.com/gists", headers=headers, json=payload
            )
            if response.status_code == 201:
                return response.json()["id"]
        except:
            pass
        return None
