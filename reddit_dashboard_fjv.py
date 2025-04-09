import streamlit as st
import pandas as pd
import requests
import datetime
import pytz
import json
import seaborn as sns
import matplotlib.pyplot as plt
from io import BytesIO
from streamlit_autorefresh import st_autorefresh

# ===== LOAD SUPABASE SECRETS FOR FJV =====
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]  # Use alternate key for FJV

st.set_page_config(page_title="Reddit FJV Alerts", layout="wide")
st.title("📊 FJV Reddit Sentiment Alert Dashboard")

# ===== FUNCTION TO LOAD DATA =====
def load_data(start_date, end_date):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    url = f"{SUPABASE_URL}/rest/v1/fjv_alerts?select=*&created_utc=gte.{start_date}T00:00:00Z&created_utc=lte.{end_date}T23:59:59Z&order=created_utc.desc"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        df = pd.DataFrame(response.json())

        if df.empty:
            st.warning("✅ Supabase responded but returned 0 records.")
            return df

        st.subheader("🧪 Debug: Returned Columns from Supabase")
        st.write(df.columns.tolist())
        st.write(df.head())

        if 'created_utc' not in df.columns:
            st.error("⚠️ 'created_utc' field is missing in the Supabase response!")
            return pd.DataFrame()

        df['created_utc'] = pd.to_datetime(df['created_utc']).dt.tz_localize('UTC').dt.tz_convert('America/New_York')
        return df
    else:
        st.error("Failed to load data from Supabase")
        return pd.DataFrame()

# ===== DATE RANGE AND REFRESH INTERVAL =====
st.sidebar.header("📅 Date Range")
today = datetime.date.today()
def_start = today - datetime.timedelta(days=7)

# Today only filter
today_only = st.sidebar.checkbox("🔘 Today Only", value=False)
if today_only:
    start_date = end_date = today
else:
    start_date = st.sidebar.date_input("Start Date", value=def_start, max_value=today)
    end_date = st.sidebar.date_input("End Date", value=today, min_value=start_date, max_value=today)

refresh_interval = st.sidebar.selectbox("🔁 Auto-refresh every...", options=[0, 30, 60, 120, 300], format_func=lambda x: f"{x} seconds" if x else "Off")
if refresh_interval:
    st_autorefresh(interval=refresh_interval * 1000, limit=None, key="fjv-refresh")

last_refresh = datetime.datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d %I:%M:%S %p %Z')

# ===== LOAD AND FILTER DATA =====
data = load_data(start_date.isoformat(), end_date.isoformat())
st.sidebar.header("🔍 Filter Alerts")

if not data.empty:
    data['created_utc'] = data['created_utc'].dt.tz_localize(None)

    sentiment_filter = st.sidebar.multiselect("Sentiment", options=data['sentiment'].unique(), default=list(data['sentiment'].unique()))
    subreddit_filter = st.sidebar.multiselect("Subreddit", options=sorted(data['subreddit'].unique()), default=list(data['subreddit'].unique()))
    keyword_filter = st.sidebar.multiselect("Keyword", options=sorted(data['matched_keyword'].unique()), default=list(data['matched_keyword'].unique()))

    display_mode = st.sidebar.radio("📊 Display Chart Mode", options=["Absolute", "Percentage"])

    filtered_data = data[
        data['sentiment'].isin(sentiment_filter) &
        data['subreddit'].isin(subreddit_filter) &
        data['matched_keyword'].isin(keyword_filter)
    ]

    st.markdown(f"### Showing {len(filtered_data)} results from {start_date} to {end_date} (Timezone: EST)")
    st.caption(f"Last updated: {last_refresh}")

    for _, row in filtered_data.iterrows():
        with st.container():
            st.markdown(f"**🧵 {row['subreddit']}** • *{row['created_utc'].strftime('%Y-%m-%d %I:%M %p')}* • `{row['sentiment'].upper()}`")
            st.markdown(f"*Keyword:* `{row['matched_keyword']}`")
            st.markdown(f"> {row['content'][:300]}...")
            st.markdown(f"[🔗 View on Reddit]({row['url']})")
            st.markdown("---")

    csv = filtered_data.to_csv(index=False)
    st.download_button("📥 Download CSV", csv, "fjv_reddit_alerts.csv", "text/csv")

    excel_buffer = BytesIO()
    filtered_data.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)
    st.download_button("📥 Download Excel", excel_buffer, "fjv_reddit_alerts.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    json_data = filtered_data.to_json(orient="records")
    st.download_button("📥 Download JSON", json_data, "fjv_reddit_alerts.json")

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

