import streamlit as st
import pandas as pd
import requests
import datetime
import os
from dotenv import load_dotenv

# ===== INITIAL SETUP =====
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

st.set_page_config(page_title="Reddit Sentiment Alerts", layout="wide")
st.title("📊 Reddit Sentiment Alert Dashboard")

# ===== FUNCTION TO LOAD DATA =====
def load_data():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    today = datetime.datetime.utcnow().date()
    today_iso = today.isoformat()
    url = f"{SUPABASE_URL}/rest/v1/alerts?select=*&created_utc=gte.{today_iso}T00:00:00Z&order=created_utc.desc"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        df = pd.DataFrame(response.json())
        df['created_utc'] = pd.to_datetime(df['created_utc'])
        return df
    else:
        st.error("Failed to load data from Supabase")
        return pd.DataFrame()

# ===== LOAD AND FILTER DATA =====
data = load_data()
st.sidebar.header("🔍 Filter Alerts")

if not data.empty:
    # Filters
    sentiment_filter = st.sidebar.multiselect("Sentiment", options=data['sentiment'].unique(), default=list(data['sentiment'].unique()))
    subreddit_filter = st.sidebar.multiselect("Subreddit", options=sorted(data['subreddit'].unique()), default=list(data['subreddit'].unique()))
    keyword_filter = st.sidebar.multiselect("Keyword", options=sorted(data['matched_keyword'].unique()), default=list(data['matched_keyword'].unique()))

    # Apply filters
    filtered_data = data[
        data['sentiment'].isin(sentiment_filter) &
        data['subreddit'].isin(subreddit_filter) &
        data['matched_keyword'].isin(keyword_filter)
    ]

    # Display
    st.markdown(f"### Showing {len(filtered_data)} results")
    st.dataframe(filtered_data[['created_utc', 'sentiment', 'subreddit', 'matched_keyword', 'content', 'url']], height=600)

    # CSV download
    csv = filtered_data.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name='filtered_reddit_alerts.csv',
        mime='text/csv'
    )
else:
    st.warning("No data available for today.")

