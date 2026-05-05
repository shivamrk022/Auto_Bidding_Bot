# ============================================================
# config/config.py — Central Configuration for Auto Bidding Bot
# ============================================================
# Fill in your credentials and preferences here.
# Never commit this file to Git (add to .gitignore)
# ============================================================
from dotenv import load_dotenv
load_dotenv()
import os

# ─── API Keys ───────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "your_openrouter_api_key_here")

# ─── LinkedIn Credentials ───────────────────────────────────
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "your@email.com")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "your_password")

# ─── X / Twitter Credentials ────────────────────────────────
TWITTER_EMAIL    = os.getenv("TWITTER_EMAIL", "your@email.com")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "your_password")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "your_username")  # without @

# ─── Search Keywords ────────────────────────────────────────
# These are the phrases the bot searches for on both platforms
KEYWORDS = [
    "looking for developer",
    "looking for freelancer",
    "need a website",
    "need a web developer",
    "need a python developer",
    "hiring developer",
    "need automation",
    "need AI developer",
    "looking for programmer",
    "need help with website",
    "need app developer",
    "budget developer",
    "DM developers",
]

# ─── Your Skills (used in AI prompt) ────────────────────────
MY_SKILLS = """
- Full-stack web development: React, Next.js, Node.js, Python/Django/FastAPI
- AI integration: OpenAI, Groq, LangChain, RAG systems
- Workflow automation: n8n, Make (Integromat), Zapier, custom APIs
- Browser automation: Playwright, Selenium
- Databases: PostgreSQL, MongoDB, SQLite, Supabase
- Cloud: AWS, Vercel, Railway, DigitalOcean
- Years of experience: 5+, worked with 50+ clients
"""

import random
# ─── Daily Limits (CRITICAL — keep these low) ───────────────
LINKEDIN_DAILY_LIMIT = random.randint(10, 15)   # Max comments per day on LinkedIn (10-15)
TWITTER_DAILY_LIMIT  = random.randint(5, 10)    # Max replies per day on X/Twitter (5-10)

# ─── Business Hours (24h format, your local timezone) ───────
BUSINESS_HOURS_START = 9    # 9 AM
BUSINESS_HOURS_END   = 18   # 6 PM

# ─── Delay Settings (seconds) ───────────────────────────────
# Between individual actions (typing, clicking)
ACTION_DELAY_MIN = 2.0
ACTION_DELAY_MAX = 5.0

# Between posting comments (human pace)
POST_DELAY_MIN = 60   # 1 minute
POST_DELAY_MAX = 180  # 3 minutes

# Between keyword searches
SEARCH_DELAY_MIN = 30
SEARCH_DELAY_MAX = 75

# ─── Paths ──────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR      = os.path.join(BASE_DIR, "data")
DB_PATH       = os.path.join(DATA_DIR, "processed_posts.xlsx")
LINKEDIN_SESSION = os.path.join(DATA_DIR, "linkedin_session")
TWITTER_SESSION  = os.path.join(DATA_DIR, "twitter_session")
LOG_FILE      = os.path.join(DATA_DIR, "bot.log")
