
import mysql.connector
import os

import streamlit as st
import pandas as pd
import datetime
import pytz
import seaborn as sns
import matplotlib.pyplot as plt
from io import BytesIO
from streamlit_autorefresh import st_autorefresh

MYSQL_HOST = st.secrets["MYSQL_HOST"]
MYSQL_USER = st.secrets["MYSQL_USER"]
MYSQL_PASSWORD = st.secrets["MYSQL_PASSWORD"]
MYSQL_DATABASE = st.secrets["MYSQL_DATABASE"]

def load_data(start_date, end_date):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor(dictionary=True)
        query = (
            "SELECT * FROM alerts "
            "WHERE timestamp BETWEEN %s AND %s "
            "ORDER BY timestamp DESC"
        )
        cursor.execute(query, (f"{start_date} 00:00:00", f"{end_date} 23:59:59"))
        return pd.DataFrame(cursor.fetchall())
    except mysql.connector.Error as err:
        st.error(f"MySQL Error: {err}")
        return pd.DataFrame()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

st.set_page_config(page_title="Reddit Sentiment Alerts", layout="wide")
st.title("📊 Reddit Sentiment Alert Dashboard")

st.sidebar.header("📅 Date Range")
today = datetime.date.today()
def_start = today - datetime.timedelta(days=7)

today_only = st.sidebar.checkbox("🔘 Today Only", value=False)
if today_only:
    start_date = end_date = today
else:
    start_date = st.sidebar.date_input("Start Date", value=def_start, max_value=today)
    end_date = st.sidebar.date_input("End Date", value=today, min_value=start_date, max_value=today)

refresh_interval = st.sidebar.selectbox("🔁 Auto-refresh every...", options=[0, 30, 60, 120, 300], format_func=lambda x: f"{x} seconds" if x else "Off")
if refresh_interval:
    st_autorefresh(interval=refresh_interval * 1000, limit=None, key="auto-refresh")

last_refresh = datetime.datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %I:%M:%S %p %Z')

data = load_data(start_date.isoformat(), end_date.isoformat())
st.write("📦 Raw DataFrame Preview:")
st.dataframe(data.head())
st.sidebar.header("🔍 Filter Alerts")

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

if not data.empty:
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data['created_utc'] = data['timestamp'].dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    data['category'] = data['matched_keyword'].apply(map_keyword_to_category)
    data['created_utc'] = data['created_utc'].dt.tz_localize(None)

    sentiment_filter = st.sidebar.multiselect("Sentiment", options=data['sentiment'].unique(), default=list(data['sentiment'].unique()))
    subreddit_filter = st.sidebar.multiselect("Subreddit", options=sorted(data['subreddit'].unique()), default=list(data['subreddit'].unique()))
    keyword_filter = st.sidebar.multiselect("Keyword", options=sorted(data['matched_keyword'].unique()), default=list(data['matched_keyword'].unique()))
    category_filter = st.sidebar.multiselect("Keyword Category", options=sorted(data['category'].unique()), default=list(data['category'].unique()))

    display_mode = st.sidebar.radio("📊 Display Chart Mode", options=["Absolute", "Percentage"])

    filtered_data = data[
        data['sentiment'].isin(sentiment_filter) &
        data['subreddit'].isin(subreddit_filter) &
        data['matched_keyword'].isin(keyword_filter) &
        data['category'].isin(category_filter)
    ]

    st.markdown(f"### Showing {len(filtered_data)} results from {start_date} to {end_date} (Timezone: EST)")
    st.caption(f"Last updated: {last_refresh}")

    for _, row in filtered_data.iterrows():
        with st.container():
            st.markdown(f"**🧵 {row['subreddit']}** • *{row['created_utc'].strftime('%Y-%m-%d %I:%M %p')}* • `{row['sentiment'].upper()}`")
            st.markdown(f"*Keyword:* `{row['matched_keyword']}` | *Category:* `{row['category']}`")
            st.markdown(f"> {row['content'][:300]}...")
            st.markdown(f"[🔗 View on Reddit]({row['url']})")
            st.markdown("---")

    csv = filtered_data.to_csv(index=False)
    st.download_button("📥 Download CSV", csv, "filtered_reddit_alerts.csv", "text/csv")

    excel_buffer = BytesIO()
    filtered_data.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)
    st.download_button("📥 Download Excel", excel_buffer, "filtered_reddit_alerts.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    json_data = filtered_data.to_json(orient="records")
    st.download_button("📥 Download JSON", json_data, "filtered_reddit_alerts.json")

    st.markdown("### 🔥 Keyword-Sentiment Heatmap")
    heatmap_data = filtered_data.groupby(['matched_keyword', 'sentiment']).size().unstack(fill_value=0)
    if display_mode == "Percentage":
        heatmap_data = heatmap_data.div(heatmap_data.sum(axis=1), axis=0).fillna(0) * 100
        fmt = ".1f"
    else:
        fmt = "d"

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(heatmap_data, annot=True, fmt=fmt, cmap="coolwarm", linewidths=0.5, ax=ax)
    st.pyplot(fig)

    st.markdown("### 📈 Sentiment Trend Over Time")
    trend_df = filtered_data.copy()
    trend_df['date'] = trend_df['created_utc'].dt.date
    sentiment_trend = trend_df.groupby(['date', 'sentiment']).size().unstack(fill_value=0)
    st.line_chart(sentiment_trend)

    st.markdown("### 🏷️ Top Keywords")
    top_keywords = filtered_data['matched_keyword'].value_counts().head(10)
    st.bar_chart(top_keywords)

    st.markdown("### 👤 Most Active Users")
    if 'author' in filtered_data.columns:
        top_authors = filtered_data['author'].value_counts().head(10)
        st.bar_chart(top_authors)

    new_alerts = filtered_data[filtered_data['created_utc'].dt.date == today]
    st.success(f"🆕 New alerts today: {len(new_alerts)}")
else:
    st.warning("No data available for the selected date range.")
