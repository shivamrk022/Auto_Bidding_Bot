# ============================================================
# scripts/dedup.py — Deduplication using SQLite
# ============================================================
# Tracks which posts we've already replied to, so we never
# comment twice on the same post. Also enforces daily limits.
# ============================================================

import sqlite3
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import DB_PATH, DATA_DIR


def init_db():
    """
    Create the SQLite database and tables if they don't exist yet.
    Call this at the start of every bot run.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Main deduplication table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_posts (
            post_id   TEXT NOT NULL,
            platform  TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            keyword   TEXT,
            comment   TEXT,
            PRIMARY KEY (post_id, platform)
        )
    """)

    # Daily stats table (for reporting)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            date      TEXT NOT NULL,
            platform  TEXT NOT NULL,
            count     INTEGER DEFAULT 0,
            PRIMARY KEY (date, platform)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized.")


def is_processed(post_id: str, platform: str) -> bool:
    """
    Return True if we've already commented on this post.
    
    Args:
        post_id:  Unique ID of the post (from platform URL or data attribute)
        platform: 'linkedin' or 'twitter'
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM processed_posts WHERE post_id = ? AND platform = ?",
        (post_id, platform)
    )
    found = cursor.fetchone() is not None
    conn.close()
    return found


def mark_processed(post_id: str, platform: str, keyword: str = "", comment: str = ""):
    """
    Mark a post as processed so we skip it next time.
    
    Args:
        post_id:  Unique ID of the post
        platform: 'linkedin' or 'twitter'
        keyword:  The keyword that found this post (for logging)
        comment:  The comment we posted (for logging)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Insert into processed posts
    cursor.execute(
        """INSERT OR IGNORE INTO processed_posts 
           (post_id, platform, timestamp, keyword, comment) 
           VALUES (?, ?, ?, ?, ?)""",
        (post_id, platform, datetime.now().isoformat(), keyword, comment)
    )

    # Update daily stats
    today = datetime.now().date().isoformat()
    cursor.execute(
        """INSERT INTO daily_stats (date, platform, count) VALUES (?, ?, 1)
           ON CONFLICT(date, platform) DO UPDATE SET count = count + 1""",
        (today, platform)
    )

    conn.commit()
    conn.close()


def get_daily_count(platform: str) -> int:
    """
    How many comments/replies have we posted today for this platform?
    
    Args:
        platform: 'linkedin' or 'twitter'
    Returns:
        Integer count of posts made today
    """
    today = datetime.now().date().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT count FROM daily_stats WHERE date = ? AND platform = ?",
        (today, platform)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0


def get_all_stats() -> dict:
    """
    Return a summary of all-time stats for reporting.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT platform, COUNT(*) FROM processed_posts GROUP BY platform")
    totals = dict(cursor.fetchall())

    cursor.execute(
        """SELECT platform, SUM(count) FROM daily_stats 
           WHERE date >= date('now', '-7 days') GROUP BY platform"""
    )
    last_7_days = dict(cursor.fetchall())

    conn.close()
    return {
        "all_time": totals,
        "last_7_days": last_7_days,
        "today_linkedin": get_daily_count("linkedin"),
        "today_twitter": get_daily_count("twitter"),
    }


# ── Quick test ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("Testing dedup system...")
    mark_processed("test123", "linkedin", "need developer", "Hi, I can help!")
    print("Is processed:", is_processed("test123", "linkedin"))   # True
    print("Not processed:", is_processed("test999", "linkedin"))  # False
    print("Stats:", get_all_stats())
