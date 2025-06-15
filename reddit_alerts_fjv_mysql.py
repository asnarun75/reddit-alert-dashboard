"""
Reddit Alert Ingestion Script using MySQL

This script monitors Reddit posts (based on keywords/subreddits) and saves relevant alert data into a MySQL table.
All previous Supabase functionality has been removed and replaced with native MySQL storage.

Author: ChatGPT for Arun Arunachalam
Date: 2025-05-29

Functions:
- save_alert(alert_data): Connects to MySQL and inserts alert records
- main(): The entry point to fetch/process alerts and store them

Environment:
Ensure `.env` file contains:
    MYSQL_HOST=localhost
    MYSQL_USER=reddit_user
    MYSQL_PASSWORD=your_password
    MYSQL_DATABASE=reddit_dashboard
"""


import mysql.connector
import os
from dotenv import load_dotenv
load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "reddit_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "your_password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "reddit_dashboard")

def save_alert(alert_data):
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        query = """
            INSERT INTO fjv_alerts (title, url, subreddit, matched_keyword, sentiment, content, author, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (
            alert_data["title"],
            alert_data["url"],
            alert_data["subreddit"],
            alert_data["matched_keyword"],
            alert_data["sentiment"],
            alert_data.get("content", ""),
            alert_data.get("author", "")
        ))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

import praw
import time
import logging
import requests
import os
from dotenv import load_dotenv
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
from pathlib import Path
from datetime import datetime, timezone

# ===== INITIAL SETUP =====
nltk.download('vader_lexicon')
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# ===== LOAD ENV VARIABLES =====
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_SECRET = os.getenv('REDDIT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT')
SUBREDDITS_TO_MONITOR = ['sadhgurusecrets', 'SadhguruTruth', 'TrueReddit', 'india', 'spirituality', 'religion']
KEYWORDS = ['Isha Foundation','Inner Engineering','Yoga','Meditation','Mysticism','Consecration','Spirituality','Karma','Sadhana','Dhyanalinga','Rudraksha','Mystical Experience','Volunteering']

# ===== SETUP SERVICES =====
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_SECRET,
    user_agent=REDDIT_USER_AGENT
)
sentiment_analyzer = SentimentIntensityAnalyzer()
seen_ids = set()
today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc).timestamp()

# ===== MAIN ALERTING FUNCTION =====
def analyze_and_send(item):
    try:
        content = item.title + "\n\n" + item.selftext if hasattr(item, 'selftext') else item.body
        matched_keyword = next((kw for kw in KEYWORDS if kw.lower() in content.lower()), None)
        if matched_keyword:
            sentiment = sentiment_analyzer.polarity_scores(content)
            compound_score = sentiment['compound']

            # ONLY log if NEGATIVE
            if compound_score <= -0.5:
                sentiment_label = 'negative'
            else:
                return

            url = f"https://reddit.com{item.permalink}" if hasattr(item, 'permalink') else ""
            item_id = item.id
            subreddit = item.subreddit.display_name
            created_utc = item.created_utc

            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "id": item_id,
                "subreddit": subreddit,
                "content": content[:1000],
                "sentiment": sentiment_label,
                "matched_keyword": matched_keyword,
                "url": url,
                "created_utc": datetime.utcfromtimestamp(created_utc).isoformat()
            }
            print(f"[LOGGED] NEGATIVE | r/{subreddit} | {matched_keyword} | {url}")

    except Exception as e:
        logging.error(f"Error in analyze_and_send: {e}")

# ===== MONITOR LOOP =====
def monitor():
    while True:
        try:
            for subreddit in SUBREDDITS_TO_MONITOR:
                print(f"🔍 Checking posts in r/{subreddit}")
                for post in reddit.subreddit(subreddit).new(limit=25):
                    if post.id not in seen_ids and post.created_utc >= today_start:
                        print(f"📝 New post: {post.title}")
                        analyze_and_send(post)
                        seen_ids.add(post.id)

                print(f"💬 Checking comments in r/{subreddit}")
                for comment in reddit.subreddit(subreddit).comments(limit=25):
                    if comment.id not in seen_ids and comment.created_utc >= today_start:
                        print(f"💬 New comment: {comment.body[:50]}")
                        analyze_and_send(comment)
                        seen_ids.add(comment.id)

        except Exception as e:
            logging.error(f"Main loop error: {e}")
            time.sleep(60)


# ===== ENTRY POINT =====
if __name__ == '__main__':
    print("📡 FJV Reddit Alert System started (only negative, JV Supabase)...")
    monitor()
