# ============================================================
# scripts/ai_generator.py — AI-Powered Bid Generation (Groq)
# ============================================================
# Sends the post content + your skills to Groq's LLM and gets
# back a unique, natural-sounding personalized bid comment.
# ============================================================

import requests
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import OPENROUTER_API_KEY, MY_SKILLS

OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct:free"   # Free OpenRouter model


def generate_bid(post_content: str, platform: str = "linkedin") -> str | None:
    """
    Generate a personalized bid comment for a job post using Groq.

    Args:
        post_content: The full text of the job post
        platform:     'linkedin' or 'twitter' (affects length and tone)

    Returns:
        A string containing the bid comment, or None if generation failed.
    """

    # Twitter needs shorter replies (280-char limit), LinkedIn can be longer
    if platform == "twitter":
        length_rule = "2–3 SHORT sentences. MUST be under 240 characters total."
        tone_rule   = "Casual and direct. No formal language."
    else:
        length_rule = "3–4 sentences. Medium length, not too short or too long."
        tone_rule   = "Friendly and professional. Show genuine interest."

    system_prompt = f"""You are an expert freelancer writing personalized bid comments on social media.
Your goal: write a unique, human-sounding response to a job post.

RULES (follow every one):
1. {length_rule}
2. {tone_rule}
3. Be SPECIFIC to what they asked for — mention their actual need.
4. Mention 1–2 of your relevant skills (from the list below) — not all of them.
5. End with a soft call to action: "Happy to chat!" / "DM me if interested!" / "Feel free to reach out!"
6. NEVER sound like a template. NEVER start with "I" or "Hi there".
7. NEVER mention you are an AI. Sound completely human.
8. NEVER use buzzwords like "synergy", "leverage", "world-class".
9. Each response must be unique and different from any previous one.

YOUR SKILLS:
{MY_SKILLS}
"""

    user_prompt = f"""Write a bid comment for this job post:

---
{post_content[:800]}
---

Output ONLY the bid comment text. No quotes, no preamble, no explanation."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer":  "https://github.com/shivamrk022/Auto_Bidding_Bot", # Required by OpenRouter
        "Content-Type":  "application/json",
    }

    payload = {
        "model":       OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.92,
        "max_tokens":  200,
        "top_p":       0.9,
    }

    # Retry up to 3 times on failure
    for attempt in range(3):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()

            data    = resp.json()
            comment = data["choices"][0]["message"]["content"].strip()

            # Remove any surrounding quotes Groq sometimes adds
            comment = comment.strip('"').strip("'")

            # Twitter hard limit
            if platform == "twitter" and len(comment) > 270:
                comment = comment[:267] + "..."

            print(f"  🤖 AI generated: {comment[:80]}...")
            return comment

        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                wait = (attempt + 1) * 10  # 10s, 20s, 30s
                print(f"  ⚠️ OpenRouter rate limit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  ❌ OpenRouter HTTP error: {e}")
                print(f"  ❌ Response text: {resp.text}")
                break

        except Exception as e:
            print(f"  ❌ OpenRouter error (attempt {attempt+1}): {e}")
            time.sleep(5)

    return None


def test_generation():
    """Quick test to verify Groq integration works."""
    sample_post = """Looking for a Python developer to build a web scraper that collects 
    product prices from 10 e-commerce sites and stores them in a database. 
    Budget: $500. Need it done in 2 weeks. DM if interested!"""

    print("Testing Groq AI generation...\n")

    print("=== LinkedIn bid ===")
    bid = generate_bid(sample_post, "linkedin")
    print(bid or "FAILED")
    print(f"\nLength: {len(bid or '')} chars")

    print("\n=== Twitter bid ===")
    bid = generate_bid(sample_post, "twitter")
    print(bid or "FAILED")
    print(f"\nLength: {len(bid or '')} chars")


if __name__ == "__main__":
    test_generation()
