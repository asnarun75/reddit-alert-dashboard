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
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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
        content = item.title + "\n\n" + item.selftext if hasattr(item, 'selftext') else item.body
        matched_keyword = next((kw for kw in KEYWORDS if kw.lower() in content.lower()), None)
        if matched_keyword:
            sentiment = sentiment_analyzer.polarity_scores(content)
            compound_score = sentiment['compound']

            if compound_score >= 0.5:
                sentiment_label = 'positive'
            elif compound_score <= -0.5:
                sentiment_label = 'negative'
            else:
                return

            url = f"https://reddit.com{item.permalink}" if hasattr(item, 'permalink') else ""
            item_id = item.id
            subreddit = item.subreddit.display_name
            created_utc = item.created_utc

            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
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
            requests.post(f"{SUPABASE_URL}/rest/v1/alerts", json=payload, headers=headers)
            print(f"[LOGGED] {sentiment_label.upper()} | r/{subreddit} | {matched_keyword} | {url}")

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
    print("📡 Reddit Alert System started and logging to Supabase (today only)...")
    monitor()

