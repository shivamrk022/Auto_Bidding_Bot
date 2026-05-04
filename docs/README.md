# Auto Bidding Bot — Complete Guide

> **Risk reminder:** LinkedIn and X prohibit automation in their ToS. This is for
> educational/personal use. Your accounts may be restricted or banned. Use
> responsibly and at your own risk.

---

## Folder Structure

```
auto-bidding-bot/
│
├── main.py                    ← Entry point — run this
├── requirements.txt           ← Python dependencies
├── .env                       ← Credentials (never commit this!)
│
├── config/
│   └── config.py              ← All settings: API keys, limits, keywords
│
├── scripts/
│   ├── dedup.py               ← SQLite deduplication (tracks processed posts)
│   ├── utils.py               ← Human delays, logging, browser helpers
│   ├── ai_generator.py        ← Groq AI bid generation
│   ├── linkedin_bot.py        ← LinkedIn Playwright automation
│   └── twitter_bot.py         ← X/Twitter Playwright automation (adapt from LinkedIn)
│
├── n8n/
│   └── README_n8n.md          ← n8n workflow setup instructions
│
└── data/                      ← Auto-created at runtime
    ├── processed_posts.db     ← SQLite dedup database
    ├── linkedin_session/      ← LinkedIn browser session (cookies)
    ├── twitter_session/       ← Twitter browser session (cookies)
    └── bot.log                ← Activity log
```

---

## Step 1 — Environment Setup

### 1a. Install Python dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 1b. Create your `.env` file
```bash
# .env (never commit this file)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
LINKEDIN_EMAIL=you@email.com
LINKEDIN_PASSWORD=yourpassword
TWITTER_EMAIL=you@email.com
TWITTER_PASSWORD=yourpassword
TWITTER_USERNAME=yourhandle
```

Get your free Groq API key at: https://console.groq.com

### 1c. Load env in Python (optional)
Add this to the top of `config.py` to auto-load from `.env`:
```python
from dotenv import load_dotenv
load_dotenv()
```

---

## Step 2 — First Run (Session Setup)

**Run once with headless=False to log in manually and save your session.**

```bash
# Start with LinkedIn
python main.py --platform linkedin
```

The browser window will open. If not logged in, it will attempt auto-login.
If CAPTCHA or 2FA appears — solve it manually. The session is then saved to
`data/linkedin_session/` and reused on every future run.

Repeat for Twitter:
```bash
python main.py --platform twitter
```

---

## Step 3 — Test AI Generation

Verify Groq is working before running the full bot:
```bash
python main.py --test-ai
```

Expected output:
```
── LinkedIn bid ──
Saw your post about needing a Python developer — building AI chatbots is
something I've done for 15+ clients. I work with OpenAI and LangChain
and can have a prototype ready within 5 days. Happy to chat about scope!

── Twitter bid ──
Just built something similar last month! Python + LangChain works great
for this. DM me if you'd like a quick quote.
```

---

## Step 4 — View Stats
```bash
python main.py --stats
```

---

## Step 5 — Full Run
```bash
# Both platforms (default)
python main.py

# LinkedIn only
python main.py --platform linkedin

# Skip business-hours check (for testing)
python main.py --platform linkedin --force
```

---

## Step 6 — Twitter Bot (Adapt from LinkedIn Bot)

The `twitter_bot.py` follows the EXACT same structure as `linkedin_bot.py`.
Key differences to change when writing it:

| LinkedIn | Twitter/X |
|----------|-----------|
| `SESSION_PATH = LINKEDIN_SESSION` | `SESSION_PATH = TWITTER_SESSION` |
| `get_daily_count("linkedin")` | `get_daily_count("twitter")` |
| Search URL: `linkedin.com/search/results/content/` | Search URL: `twitter.com/search?q=...&f=live` |
| Card selector: `.feed-shared-update-v2` | Card selector: `article[data-testid='tweet']` |
| Text selector: `.feed-shared-text` | Text selector: `div[data-testid='tweetText']` |
| Comment button: `button[aria-label*='omment']` | Reply button: `button[data-testid='reply']` |
| Submit: `.comments-comment-box__submit-button--cr` | Submit: `button[data-testid='tweetButton']` |
| Comment box: `.ql-editor` | Reply box: `div[data-testid='tweetTextarea_0']` |
| Post ID: `data-urn` attribute | Post ID: extracted from tweet URL `/status/123456` |
| Post delay: 60–180s | Post delay: 90–180s (stricter) |
| Daily limit: `LINKEDIN_DAILY_LIMIT` | Daily limit: `TWITTER_DAILY_LIMIT` |

---

## Step 7 — n8n Workflow (Scheduling)

### Option A: Simple Python scheduler (no n8n needed)
```python
# schedule_runner.py
import schedule
import time
import subprocess

def run_bot():
    subprocess.run(["python", "main.py", "--platform", "both"])

# Run every 3 hours on weekdays
schedule.every().monday.at("09:00").do(run_bot)
schedule.every().monday.at("13:00").do(run_bot)
schedule.every().tuesday.at("09:00").do(run_bot)
# ... add more days

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Option B: n8n workflow (visual, recommended)

**In n8n, create this workflow:**

```
[Cron Node] → [IF: Business Hours?] → [Execute Command: python main.py]
                      ↓ No
               [Stop & Do Nothing]
```

**Cron node settings:**
- Mode: Every X hours
- Hours: 3 (runs every 3 hours)
- Days: Monday to Friday only

**IF node condition:**
```javascript
// In Expression field:
{{ new Date().getHours() >= 9 && new Date().getHours() < 18 }}
```

**Execute Command node:**
```bash
cd /path/to/auto-bidding-bot && venv\Scripts\python main.py --platform both
```

**Add a Slack/Email notification node at the end** to get reports:
```javascript
// Message template:
Bot run complete at {{ $now.toISO() }}
Check logs: data/bot.log
```

### Option C: Cron (Linux/Mac)
```bash
# Edit crontab: crontab -e
# Run every 3 hours, Mon-Fri, 9am-6pm
0 9,12,15 * * 1-5 cd /path/to/auto-bidding-bot && python main.py --platform both >> data/cron.log 2>&1
```

---

## Google Sheets Deduplication (Alternative to SQLite)

If you prefer Google Sheets for dedup (visible in browser, easy to manage):

1. Create a Google Sheet with columns: `post_id | platform | timestamp | comment`
2. In n8n, use the **Google Sheets node** to:
   - **Check:** Search for post_id before processing
   - **Write:** Append a row after successful comment

This replaces `dedup.py` but adds n8n dependency. SQLite is simpler and faster.

---

## Keyword Tuning

Edit `config.py` → `KEYWORDS` list. Good performing keywords:
```python
KEYWORDS = [
    "looking for developer",    # High intent
    "need a website",           # High intent
    "need freelancer",          # High intent
    "need python developer",    # Specific to your skill
    "budget developer",         # Has budget = serious buyer
    "DM developers",            # Explicit call-out
    "need automation",          # Matches your AI/automation skill
]
```

Avoid too-broad keywords like "developer" — too much noise.

---

## Safety Checklist

Before running in production:
- [ ] Daily limits set low (LinkedIn: ≤15, Twitter: ≤10)
- [ ] `headless=True` only after confirming sessions work
- [ ] Business hours check enabled
- [ ] Post delays set to 60–180 seconds minimum
- [ ] Different keywords searched in random order each run
- [ ] Bot log reviewed weekly for errors
- [ ] Backup `data/linkedin_session/` and `data/twitter_session/` (your saved logins)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| LinkedIn keeps asking to re-login | Delete `data/linkedin_session/` and log in again manually |
| Groq returns 429 error | You've hit the free tier rate limit; wait 10 minutes |
| Comment button not found | LinkedIn updated their UI; update the CSS selector in `linkedin_bot.py` |
| Posts found but none are "relevant" | Lower the threshold in `is_relevant()` from 2 matches to 1 |
| n8n Execute Command fails | Use absolute path to Python: `/usr/bin/python3 /full/path/main.py` |

---

## Architecture Diagram

```
n8n Cron Trigger (every 3 hours, business hours only)
        │
        ▼
   main.py runner
   ┌─────────────┐     ┌──────────────┐
   │ linkedin_   │     │ twitter_     │
   │ bot.py      │     │ bot.py       │
   └──────┬──────┘     └──────┬───────┘
          │                   │
          ▼                   ▼
   Playwright browser   Playwright browser
   (persistent session) (persistent session)
          │                   │
          ▼                   ▼
   Search posts         Search tweets
          │                   │
          ▼                   ▼
   dedup.py check ──── Skip if seen before
          │
          ▼
   ai_generator.py ──── Groq API ──── Unique bid
          │
          ▼
   Post comment/reply
          │
          ▼
   dedup.py mark ──── SQLite DB (processed_posts.db)
          │
          ▼
   Log to data/bot.log
```
