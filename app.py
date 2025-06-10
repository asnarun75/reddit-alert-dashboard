import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for macOS compatibility

from flask import Flask, render_template, request, send_file


import pandas as pd
import mysql.connector
import matplotlib.pyplot as plt
import seaborn as sns
import os
import io
import datetime
import pytz
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# Database config from env
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

CATEGORY_MAP = {
    'mindfulness': ['meditation', 'present moment', 'awareness', 'clarity', 'equanimity'],
    'spirituality': ['art of iiving', 'Gurudev', 'Sri Sri Ravi Shankar'],
    'wellness': ['breathe', 'calm anxiety', 'stress', 'peace'],
    'practice': ['yoga', 'compassionate']
}

def map_keyword_to_category(keyword):
    for category, keywords in CATEGORY_MAP.items():
        if keyword.lower() in [k.lower() for k in keywords]:
            return category
    return 'other'

def is_valid_date_format(date_string):
    if not date_string: # Allow empty strings, get_data will handle them
        return True
    try:
        datetime.datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def get_data(start_date, end_date):
    # Handle empty or None date strings
    if not start_date: # Checks for None or empty string
        start_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    if not end_date: # Checks for None or empty string
        end_date = datetime.date.today().strftime('%Y-%m-%d')

    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT * FROM alerts
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY timestamp DESC
        """
        cursor.execute(query, (f"{start_date} 00:00:00", f"{end_date} 23:59:59"))
        df = pd.DataFrame(cursor.fetchall())
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['created_utc'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('America/New_York')
            df['category'] = df['matched_keyword'].apply(map_keyword_to_category)
            df['created_utc'] = df['created_utc'].dt.tz_localize(None)
        return df
    except Exception as e:
        print(f"DB ERROR: {e}")
        return pd.DataFrame()

@app.route('/', methods=['GET', 'POST'])
def index():
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=7)
    data = pd.DataFrame()
    filters = {}

    if request.method == 'POST':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if not is_valid_date_format(start_date) or not is_valid_date_format(end_date):
            # Get today and default_start for rendering index.html with an error
            today = datetime.date.today()
            default_start = today - datetime.timedelta(days=7)
            return render_template('index.html',
                                   error_message="Invalid date format. Please use YYYY-MM-DD.",
                                   today=today,
                                   default_start=default_start)

        data = get_data(start_date, end_date)

        filters = {
            'sentiment': request.form.getlist('sentiment'),
            'subreddit': request.form.getlist('subreddit'),
            'matched_keyword': request.form.getlist('matched_keyword'),
            'category': request.form.getlist('category')
        }

        for key, values in filters.items():
            if values:
                data = data[data[key].isin(values)]

        # Save downloadable formats
        data.to_csv("filtered.csv", index=False)
        data.to_excel("filtered.xlsx", index=False)
        data.to_json("filtered.json", orient="records")

        # Heatmap
        heatmap_path = "static/heatmap.png"
        if not data.empty:
            heatmap_data = data.groupby(['matched_keyword', 'sentiment']).size().unstack(fill_value=0)
            plt.figure(figsize=(10, 6))
            sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='coolwarm', linewidths=0.5)
            plt.tight_layout()
            plt.savefig(heatmap_path)
            plt.close()

        return render_template('results.html', data=data, heatmap=heatmap_path)

    return render_template('index.html', today=today, default_start=default_start)

@app.route('/download/<filetype>')
def download(filetype):
    if filetype == 'csv':
        return send_file("filtered.csv", as_attachment=True)
    elif filetype == 'excel':
        return send_file("filtered.xlsx", as_attachment=True)
    elif filetype == 'json':
        return send_file("filtered.json", as_attachment=True)
    else:
        return "Invalid download type", 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
