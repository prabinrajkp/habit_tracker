# 🚀 Ultimate Habit Tracker

A powerful, aesthetic Streamlit application that transforms your daily habits into real-time insights, all synced to your personal Google Sheets.

## ✨ Features
- **Google Sign-in**: Securely access your data using your Google account.
- **Automated Google Sheets**: Automatically creates and initializes a tracker spreadsheet in your Google Drive.
- **Daily Tracking**: Easy-to-use checklist for your routines, plus metrics like mood, screen time, and energy.
- **Visual Dashboard**:
    - **Donut Chart**: Overall monthly completion rate.
    - **Line Chart**: Daily consistency over time.
    - **Bar Chart**: Weekly performance comparison.
    - **Top Habits**: Highlights your strongest routines.
- **Calendar Settings**: Flexibility to track any month or year.

## 🛠️ Setup

### 1. Google Cloud Configuration
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Enable **Google Sheets API** and **Google Drive API**.
4. Set up the **OAuth Consent Screen**.
5. Create **OAuth 2.0 Client IDs** (Web Application).
6. Add `http://localhost:6001` to **Authorized redirect URIs**.
7. Download the credentials JSON, rename it to `credentials.json`, and place it in the project root.

### 2. Local Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## 📂 Project Structure
- `app.py`: Main Streamlit interface.
- `auth.py`: Google OAuth authentication logic.
- `sheets_handler.py`: Google Sheets API integration.
- `analytics.py`: Data processing and Plotly charts.
- `documentation_requirement.txt`: Detailed functional requirements and setup guide.

## 📜 Requirements
- Python 3.8+
- Google Account
- Internet connection (for API sync)
