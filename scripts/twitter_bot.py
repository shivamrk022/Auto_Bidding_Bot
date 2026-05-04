import sys
import os
import random
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config.config import (
    TWITTER_EMAIL, TWITTER_PASSWORD, TWITTER_USERNAME,
    KEYWORDS, TWITTER_DAILY_LIMIT,
    TWITTER_SESSION,
)
from scripts.dedup        import init_db, is_processed, mark_processed, get_daily_count
from scripts.ai_generator import generate_bid
from scripts.utils        import (
    get_logger, is_business_hours,
    human_delay, post_delay, search_delay,
    human_type, random_scroll, move_mouse_randomly,
    get_random_user_agent,
)

log = get_logger("twitter_bot")

HIRE_SIGNALS = [
    "looking for", "need a", "need someone", "need help",
    "hiring", "want a", "freelancer", "developer needed",
    "build", "create", "website", "web app", "budget",
    "quote", "dm me", "message me", "reach out", "open to",
    "paid", "$", "usd", "€", "gbp",
]

def is_relevant(text: str) -> bool:
    t = text.lower()
    return sum(1 for kw in HIRE_SIGNALS if kw in t) >= 2

def login(page) -> bool:
    log.info("Navigating to Twitter/X login page...")
    page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
    human_delay(3, 5)

    if "home" in page.url:
        log.info("Already logged in (session restored).")
        return True

    try:
        # Check if login is needed
        email_input = page.query_selector("input[autocomplete='username']")
        if not email_input:
            email_input = page.wait_for_selector("input[autocomplete='username']", timeout=10000)
            
        email_input.fill(TWITTER_EMAIL)
        human_delay(0.5, 1.0)
        page.click("button:has-text('Next')")
        human_delay(2, 3)

        # Sometimes it asks for username
        username_input = page.query_selector("input[data-testid='ocfEnterTextTextInput']")
        if username_input:
            username_input.fill(TWITTER_USERNAME)
            page.click("button:has-text('Next')")
            human_delay(3, 4)

        # Wait for the password input with a longer timeout
        try:
            pwd_input = page.wait_for_selector("input[name='password'], input[type='password']", timeout=10000)
            pwd_input.fill(TWITTER_PASSWORD)
            human_delay(0.5, 1.0)
            
            # Click the Log in button
            login_btn = page.query_selector("button[data-testid='LoginForm_Login_Button']") or page.query_selector("button:has-text('Log in')")
            if login_btn:
                login_btn.click()
            else:
                page.keyboard.press("Enter")
            human_delay(4, 7)
        except PlaywrightTimeout:
            log.warning("Automated login interrupted (CAPTCHA or UI block). Please log in manually in the browser window within 60 seconds.")
            page.wait_for_url("**/home", timeout=60000)

        if "home" in page.url:
            log.info("Login successful.")
            return True
        else:
            log.error(f"Login failed. Current URL: {page.url}")
            return False

    except Exception as e:
        log.error(f"Login exception: {e}")
        return False

def search_posts(page, keyword: str) -> list[dict]:
    encoded = keyword.replace(" ", "%20")
    url = f"https://x.com/search?q={encoded}&f=live"
    log.info(f"Searching: '{keyword}'")
    page.goto(url, wait_until="domcontentloaded")
    human_delay(3, 6)

    for _ in range(4):
        random_scroll(page, 400, 900)
        human_delay(1, 2.5)

    results = []
    cards = page.query_selector_all("article[data-testid='tweet']")
    log.info(f"Found {len(cards)} post cards for '{keyword}'")

    for card in cards[:12]:
        try:
            # Extract ID from the status URL
            a_tags = card.query_selector_all("a[href*='/status/']")
            post_id = ""
            for a in a_tags:
                href = a.get_attribute("href")
                if "/status/" in href:
                    post_id = href.split("/status/")[1].split("?")[0].split("/")[0]
                    break
            
            if not post_id:
                continue

            text_el = card.query_selector("div[data-testid='tweetText']")
            if not text_el:
                continue
            text = text_el.inner_text().strip()

            results.append({
                "id": post_id,
                "text": text,
                "element": card,
                "keyword": keyword,
            })
        except Exception as e:
            log.debug(f"Error parsing card: {e}")

    return results

def post_comment(page, post: dict, comment: str) -> bool:
    card = post["element"]
    try:
        card.scroll_into_view_if_needed()
        human_delay(1, 2)
        move_mouse_randomly(page)

        btn = card.query_selector("button[data-testid='reply']")
        if not btn:
            log.warning("Reply button not found.")
            return False

        btn.click()
        human_delay(2, 3.5)

        box = page.wait_for_selector("div[data-testid='tweetTextarea_0']", timeout=5000)
        box.click()
        human_delay(0.5, 1.0)
        human_type(box, comment)
        human_delay(1, 2)

        submit = page.query_selector("button[data-testid='tweetButton']")
        if submit:
            submit.click()
            human_delay(3, 5)
            log.info("Reply posted successfully.")
            return True
        else:
            page.keyboard.press("Control+Return")
            human_delay(3, 5)
            return True

    except PlaywrightTimeout:
        log.error("Timeout while posting reply.")
        return False
    except Exception as e:
        log.error(f"Error posting reply: {e}")
        return False

def run():
    init_db()

    today_count = get_daily_count("twitter")
    if today_count >= TWITTER_DAILY_LIMIT:
        log.info(f"Daily limit reached ({today_count}/{TWITTER_DAILY_LIMIT}). Done for today.")
        return

    remaining = TWITTER_DAILY_LIMIT - today_count
    log.info(f"Starting Twitter bot. Posted today: {today_count}. Remaining budget: {remaining}.")

    os.makedirs(TWITTER_SESSION, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=TWITTER_SESSION,
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

        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        page.goto("https://x.com", wait_until="domcontentloaded")
        human_delay(2, 4)

        if "home" not in page.url:
            if not login(page):
                ctx.close()
                return

        posted = 0
        keywords = KEYWORDS.copy()
        random.shuffle(keywords)

        for kw in keywords:
            if posted >= remaining:
                break

            posts = search_posts(page, kw)

            for post in posts:
                if posted >= remaining:
                    break

                pid  = post["id"]
                text = post["text"]

                if is_processed(pid, "twitter"):
                    log.debug(f"Already processed: {pid}")
                    continue

                if not is_relevant(text):
                    log.debug("Not relevant, skipping.")
                    continue

                log.info(f"Processing: {text[:100]}...")

                comment = generate_bid(text, "twitter")
                if not comment:
                    log.warning("AI generation failed, skipping post.")
                    continue

                success = post_comment(page, post, comment)

                if success:
                    mark_processed(pid, "twitter", kw, comment)
                    posted += 1
                    total  = today_count + posted
                    log.info(f"Progress: {total}/{TWITTER_DAILY_LIMIT} today.")
                    post_delay()

            search_delay()

        log.info(f"Twitter session done. Posted {posted} comment(s) this run.")
        ctx.close()

if __name__ == "__main__":
    run()
