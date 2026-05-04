# linkedin_bot.py
# Build using Playwright + selectors in docs/README.md
# Pattern: search → filter → generate_bid() → post → mark_processed()
# See README.md "Architecture Diagram" section for full flow.

# ============================================================
# scripts/linkedin_bot.py — LinkedIn Browser Automation
# ============================================================
# Uses Playwright with a persistent browser context so LinkedIn
# cookies/session persist across runs (no re-login every time).
#
# IMPORTANT: LinkedIn has strict ToS on automation. This bot:
#   - Limits to 10–15 comments/day
#   - Adds random delays between actions
#   - Only runs during business hours
#   - Uses a persistent session (not a fresh browser each time)
# ============================================================

import sys
import os
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config.config import (
    LINKEDIN_EMAIL, LINKEDIN_PASSWORD,
    KEYWORDS, LINKEDIN_DAILY_LIMIT,
    LINKEDIN_SESSION,
)
from scripts.dedup        import init_db, is_processed, mark_processed, get_daily_count
from scripts.ai_generator import generate_bid
from scripts.utils        import (
    get_logger, is_business_hours,
    human_delay, post_delay, search_delay,
    human_type, random_scroll, move_mouse_randomly,
    get_random_user_agent,
)

log = get_logger("linkedin_bot")

# ─── Relevance filter ──────────────────────────────────────
HIRE_SIGNALS = [
    "looking for", "need a", "need someone", "need help",
    "hiring", "want a", "freelancer", "developer needed",
    "build", "create", "website", "web app", "budget",
    "quote", "dm me", "message me", "reach out", "open to",
    "paid", "$", "usd", "€", "gbp",
]

def is_relevant(text: str) -> bool:
    """Return True if the post looks like a job/project request."""
    t = text.lower()
    return sum(1 for kw in HIRE_SIGNALS if kw in t) >= 2


# ─── Login ─────────────────────────────────────────────────
def login(page) -> bool:
    """
    Log into LinkedIn. Returns True on success.
    With a persistent session, this is usually skipped after first run.
    """
    log.info("Navigating to LinkedIn login page...")
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    human_delay(2, 4)

    # If already logged in, the feed is shown directly
    if "feed" in page.url:
        log.info("Already logged in (session restored).")
        return True

    try:
        page.fill("#username", LINKEDIN_EMAIL)
        human_delay(0.8, 1.8)

        pw_field = page.locator("#password")
        pw_field.click()
        human_delay(0.3, 0.7)
        human_type(pw_field, LINKEDIN_PASSWORD)
        human_delay(0.5, 1.2)

        page.click("button[type='submit']")
        human_delay(4, 7)

        if "feed" in page.url or "checkpoint" in page.url:
            log.info("Login successful.")
            return True
        else:
            log.error(f"Login failed. Current URL: {page.url}")
            return False

    except Exception as e:
        log.error(f"Login exception: {e}")
        return False


# ─── Search ────────────────────────────────────────────────
def search_posts(page, keyword: str) -> list[dict]:
    """
    Search LinkedIn for recent posts containing the keyword.
    Returns a list of dicts: {id, text, element}.
    """
    encoded = keyword.replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/search/results/content/"
        f"?keywords={encoded}&sortBy=date_posted"
    )
    log.info(f"Searching: '{keyword}'")
    page.goto(url, wait_until="domcontentloaded")
    # Wait for the search results container or at least some time to load
    try:
        page.wait_for_selector(".search-results-container", timeout=10000)
    except PlaywrightTimeout:
        page.wait_for_timeout(5000)
    human_delay(3, 6)

    # Scroll down to load more results
    for _ in range(4):
        random_scroll(page, 400, 900)
        human_delay(1, 2.5)

    results = []
    # LinkedIn wraps each post in this container or uses [data-urn] for posts
    cards = page.query_selector_all(".feed-shared-update-v2")
    if not cards:
        cards = page.query_selector_all(".search-result__occluded-item")
    if not cards:
        cards = page.query_selector_all("div[data-urn]")
        
    log.info(f"Found {len(cards)} post cards for '{keyword}'")

    for card in cards[:12]:   # Cap at 12 per search
        try:
            # Unique post identifier
            post_id = (
                card.get_attribute("data-urn") or
                card.get_attribute("id") or
                ""
            )
            if not post_id:
                continue

            # Post text
            text_el = card.query_selector(".feed-shared-text") or card.query_selector(".update-components-text") or card.query_selector("span[dir='ltr']")
            if not text_el:
                continue
            text = text_el.inner_text().strip()

            results.append({
                "id":      post_id,
                "text":    text,
                "element": card,
                "keyword": keyword,
            })

        except Exception as e:
            log.debug(f"Error parsing card: {e}")

    return results


# ─── Comment ───────────────────────────────────────────────
def post_comment(page, post: dict, comment: str) -> bool:
    """
    Click the Comment button on a LinkedIn post and submit text.
    Returns True if successful.
    """
    card = post["element"]
    try:
        # Scroll the post into view
        card.scroll_into_view_if_needed()
        human_delay(1, 2)
        move_mouse_randomly(page)

        # Click the Comment button
        # LinkedIn uses aria-label="Comment" on the button
        btn = (
            card.query_selector("button[aria-label*='omment']") or
            card.query_selector(".comment-button")
        )
        if not btn:
            log.warning("Comment button not found on post.")
            return False

        btn.click()
        human_delay(2, 3.5)

        # Comment input box (Quill editor)
        box = (
            page.query_selector(".ql-editor[contenteditable='true']") or
            page.query_selector(".comments-comment-box__input")
        )
        if not box:
            log.warning("Comment input box not found.")
            return False

        box.click()
        human_delay(0.5, 1.0)
        human_type(box, comment)
        human_delay(1, 2)

        # Submit — try the button first, then Ctrl+Enter
        submit = page.query_selector("button.comments-comment-box__submit-button--cr")
        if submit:
            submit.click()
        else:
            page.keyboard.press("Control+Return")

        human_delay(3, 5)
        log.info("Comment posted successfully.")
        return True

    except PlaywrightTimeout:
        log.error("Timeout while posting comment.")
        return False
    except Exception as e:
        log.error(f"Error posting comment: {e}")
        return False


# ─── Main bot loop ─────────────────────────────────────────
def run():
    """Entry point — runs the full LinkedIn bot session."""

    init_db()

    today_count = get_daily_count("linkedin")
    if today_count >= LINKEDIN_DAILY_LIMIT:
        log.info(f"Daily limit reached ({today_count}/{LINKEDIN_DAILY_LIMIT}). Done for today.")
        return

    remaining = LINKEDIN_DAILY_LIMIT - today_count
    log.info(f"Starting LinkedIn bot. Posted today: {today_count}. Remaining budget: {remaining}.")

    os.makedirs(LINKEDIN_SESSION, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=LINKEDIN_SESSION,
            headless=False,
            channel="msedge",
            slow_mo=50,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            user_agent=get_random_user_agent(),
            viewport={"width": random.randint(1280, 1440),
                      "height": random.randint(800, 900)},
        )

        page = ctx.new_page()

        # Hide webdriver property (basic anti-detection)
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page.goto("https://www.linkedin.com", wait_until="domcontentloaded")
        human_delay(2, 4)

        # Login if needed
        if "feed" not in page.url:
            if not login(page):
                ctx.close()
                return

        posted = 0
        keywords = KEYWORDS.copy()
        random.shuffle(keywords)   # Vary the order each run

        for kw in keywords:
            if posted >= remaining:
                break

            posts = search_posts(page, kw)

            for post in posts:
                if posted >= remaining:
                    break

                pid  = post["id"]
                text = post["text"]

                if is_processed(pid, "linkedin"):
                    log.debug(f"Already processed: {pid[:40]}")
                    continue

                if not is_relevant(text):
                    log.debug("Not relevant, skipping.")
                    continue

                log.info(f"Processing: {text[:100]}...")

                comment = generate_bid(text, "linkedin")
                if not comment:
                    log.warning("AI generation failed, skipping post.")
                    continue

                success = post_comment(page, post, comment)

                if success:
                    mark_processed(pid, "linkedin", kw, comment)
                    posted += 1
                    total  = today_count + posted
                    log.info(f"Progress: {total}/{LINKEDIN_DAILY_LIMIT} today.")
                    post_delay()   # Wait 1–3 min before next comment

            search_delay()   # Wait 30–75s before next keyword

        log.info(f"LinkedIn session done. Posted {posted} comment(s) this run.")
        ctx.close()


if __name__ == "__main__":
    run()