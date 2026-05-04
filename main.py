#!/usr/bin/env python3
# ============================================================
# main.py — Auto Bidding Bot Runner
# ============================================================
# Usage:
#   python main.py --platform linkedin
#   python main.py --platform twitter
#   python main.py --platform both
#   python main.py --test-ai     (test AI generation only)
#   python main.py --stats       (show database stats)
# ============================================================

import argparse
import sys
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.utils  import is_business_hours, get_logger
from scripts.dedup  import init_db, get_all_stats
from config.config  import LINKEDIN_DAILY_LIMIT, TWITTER_DAILY_LIMIT

log = get_logger("main")


def show_stats():
    """Print today's stats and all-time totals."""
    init_db()
    stats = get_all_stats()
    print("\n" + "="*45)
    print("  AUTO BIDDING BOT — STATS")
    print("="*45)
    print(f"  Today   → LinkedIn: {stats['today_linkedin']}/{LINKEDIN_DAILY_LIMIT}  |  Twitter: {stats['today_twitter']}/{TWITTER_DAILY_LIMIT}")
    print(f"  7 days  → {stats.get('last_7_days', {})}")
    print(f"  All time→ {stats.get('all_time', {})}")
    print("="*45 + "\n")


def test_ai():
    """Quick test of AI generation without posting anything."""
    from scripts.ai_generator import generate_bid
    sample = "Looking for a Python developer to build an AI chatbot. Budget $800. DM me."
    print("\n── LinkedIn bid ──")
    print(generate_bid(sample, "linkedin") or "FAILED")
    print("\n── Twitter bid ──")
    print(generate_bid(sample, "twitter") or "FAILED")


def main():
    parser = argparse.ArgumentParser(description="Auto Bidding Bot")
    parser.add_argument(
        "--platform",
        choices=["linkedin", "twitter", "both"],
        default="both",
        help="Which platform to run (default: both)",
    )
    parser.add_argument("--test-ai",  action="store_true", help="Test AI generation only")
    parser.add_argument("--stats",    action="store_true", help="Show database stats and exit")
    parser.add_argument("--force",    action="store_true", help="Skip business-hours check")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if args.test_ai:
        test_ai()
        return

    if not args.force and not is_business_hours():
        log.info("Outside business hours. Use --force to override.")
        return

    show_stats()

    if args.platform in ("linkedin", "both"):
        log.info("━━━ Running LinkedIn Bot ━━━")
        from scripts.linkedin_bot import run as run_linkedin
        run_linkedin()

    if args.platform in ("twitter", "both"):
        log.info("━━━ Running Twitter Bot ━━━")
        # Twitter bot follows the same pattern as linkedin_bot.py
        # Adapt scripts/linkedin_bot.py → scripts/twitter_bot.py (see README)
        try:
            from scripts.twitter_bot import run as run_twitter
            run_twitter()
        except ImportError:
            log.warning("twitter_bot.py not found. See README to create it.")


if __name__ == "__main__":
    main()
