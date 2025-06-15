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
            INSERT INTO alerts (title, url, subreddit, matched_keyword, sentiment, content, author, timestamp)
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
SUBREDDITS_TO_MONITOR = ['Meditation', 'ArtOfLiving', 'india', 'MeditationPractice', 'Ex_ArtOfLiving', 'IndiaSpeaks', 'breathwork']
KEYWORDS = ['art of iiving', 'Gurudev','Sri Sri Ravi Shankar','meditation','yoga','calm anxiety','stress','breathe','awareness','peace','Present moment' ,'clarity', 'compassionate' ,'equanimity']

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
        if hasattr(item, 'selftext'):
            content = f"{item.title}\n\n{item.selftext}"
        else:
            content = item.body

        matched_keyword = next((kw for kw in KEYWORDS if kw.lower() in content.lower()), None)
        if matched_keyword:
            sentiment = sentiment_analyzer.polarity_scores(content)
            compound_score = sentiment['compound']

            if compound_score >= 0.5: 
                sentiment_label = 'positive'
            elif compound_score <= -0.5:
                sentiment_label = 'negative'
            else:
                return  # Neutral sentiment, skip

            url = f"https://reddit.com{item.permalink}" if hasattr(item, 'permalink') else ""
            item_id = item.id
            subreddit = item.subreddit.display_name
            created_utc = item.created_utc

            alert = {
                "title": item.title if hasattr(item, "title") else "(no title)",
                "url": url,
                "subreddit": subreddit,
                "matched_keyword": matched_keyword,
                "sentiment": sentiment_label,
                "content": content[:1000],
                "author": str(item.author) if hasattr(item, "author") else "unknown"
            }

            print(f"[LOGGED] {sentiment_label.upper()} | r/{subreddit} | {matched_keyword} | {url}")
            save_alert(alert)

    except Exception as e:
        logging.error(f"Error in analyze_and_send: {e}")

# ===== MONITOR LOOP =====
def monitor():
    while True:
        try:
            for subreddit in SUBREDDITS_TO_MONITOR:
                for post in reddit.subreddit(subreddit).new(limit=50):
                    if post.id not in seen_ids and post.created_utc >= today_start:
                        analyze_and_send(post)
                        seen_ids.add(post.id)

                for comment in reddit.subreddit(subreddit).comments(limit=50):
                    if comment.id not in seen_ids and comment.created_utc >= today_start:
                        analyze_and_send(comment)
                        seen_ids.add(comment.id)

            time.sleep(30)

        except Exception as e:
            logging.error(f"Main loop error: {e}")
            time.sleep(60)

# ===== ENTRY POINT =====
if __name__ == '__main__':
    print("📡 Reddit Alert System started and logging to MySQL (today only)...")
    monitor()

