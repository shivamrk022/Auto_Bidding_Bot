# ============================================================
# scripts/utils.py — Utility Functions
# ============================================================
# Human-like delays, business hours check, typing simulation,
# and logging helpers used by both platform bots.
# ============================================================

import time
import random
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import (
    BUSINESS_HOURS_START, BUSINESS_HOURS_END,
    ACTION_DELAY_MIN, ACTION_DELAY_MAX,
    POST_DELAY_MIN, POST_DELAY_MAX,
    SEARCH_DELAY_MIN, SEARCH_DELAY_MAX,
    LOG_FILE, DATA_DIR
)


# ─── Logger Setup ────────────────────────────────────────────
def get_logger(name: str) -> logging.Logger:
    """Create a logger that writes to both console and file."""
    os.makedirs(DATA_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Format: [2024-01-15 09:30:00] INFO linkedin_bot: Message
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ─── Timing Utilities ────────────────────────────────────────
def is_business_hours() -> bool:
    """
    Returns True only if current time is within business hours.
    Bots only run during business hours to look more human.
    """
    current_hour = datetime.now().hour
    return BUSINESS_HOURS_START <= current_hour < BUSINESS_HOURS_END


def human_delay(min_s: float = None, max_s: float = None):
    """
    Sleep for a random duration to simulate human hesitation.
    Defaults to ACTION_DELAY_MIN / ACTION_DELAY_MAX from config.
    """
    min_s = min_s if min_s is not None else ACTION_DELAY_MIN
    max_s = max_s if max_s is not None else ACTION_DELAY_MAX
    delay = random.uniform(min_s, max_s)
    time.sleep(delay)


def post_delay():
    """Longer delay BETWEEN posting comments. Use after each post."""
    delay = random.uniform(POST_DELAY_MIN, POST_DELAY_MAX)
    mins = int(delay // 60)
    secs = int(delay % 60)
    print(f"  ⏳ Cooling down for {mins}m {secs}s before next post...")
    time.sleep(delay)


def search_delay():
    """Medium delay between keyword searches."""
    delay = random.uniform(SEARCH_DELAY_MIN, SEARCH_DELAY_MAX)
    print(f"  ⏳ Waiting {delay:.0f}s before next search...")
    time.sleep(delay)


# ─── Browser Interaction Helpers ─────────────────────────────
def human_type(element, text: str):
    """
    Type text character by character with random speed.
    Looks much more human than element.fill() which types instantly.
    
    Args:
        element: A Playwright element (must be focused/clicked first)
        text:    The string to type
    """
    for char in text:
        element.type(char)
        # Random delay: 40–150ms per character (like real typing)
        time.sleep(random.uniform(0.04, 0.15))

        # Occasionally add a longer pause (like thinking)
        if random.random() < 0.05:
            time.sleep(random.uniform(0.3, 0.8))


def random_scroll(page, min_px: int = 200, max_px: int = 800):
    """Scroll the page by a random amount to simulate reading."""
    px = random.randint(min_px, max_px)
    page.evaluate(f"window.scrollBy(0, {px})")
    human_delay(0.5, 1.5)


def move_mouse_randomly(page):
    """
    Move the mouse to a random position on the page.
    Helps avoid detection patterns from perfectly static cursors.
    """
    x = random.randint(100, 1200)
    y = random.randint(100, 700)
    page.mouse.move(x, y)
    human_delay(0.2, 0.6)


def get_random_user_agent() -> str:
    """Return a realistic browser user agent string."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ]
    return random.choice(agents)


# ─── Quick Test ──────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Business hours: {is_business_hours()}")
    print(f"Current hour:   {datetime.now().hour}")
    print("Testing delays...")
    human_delay(1, 2)
    print("Done.")