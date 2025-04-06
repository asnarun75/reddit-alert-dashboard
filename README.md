# Reddit Sentiment Monitor + Dashboard

- Live dashboard built with Streamlit
- Sentiment + keyword-based alerts stored in Supabase
- Background script (EC2/local) monitors Reddit posts/comments in near real-time

## Features
- Sentiment analysis (positive/negative)
- Filters by subreddit, keyword, and date
- Live alerts stored in Supabase
- Public dashboard powered by Streamlit Cloud

## Setup

### Local Use (Logger Script)
1. Copy `.env.example` to `.env` and fill in your credentials
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python reddit_alert_logger.py`

### Deploy Dashboard (Streamlit)
1. Add `.streamlit/secrets.toml` with Supabase values
2. Push to GitHub
3. Deploy via [streamlit.io/cloud](https://streamlit.io/cloud)
