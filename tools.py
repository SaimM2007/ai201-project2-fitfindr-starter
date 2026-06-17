"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    """
    listings = load_listings()

    # filter by price
    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]

    # filter by size (case-insensitive, partial match so "M" matches "S/M")
    if size is not None:
        size_lower = size.lower()
        listings = [l for l in listings if size_lower in l["size"].lower()]

    # score by keyword overlap across title, description, and style_tags
    keywords = description.lower().split()

    def score(listing):
        text = " ".join([
            listing["title"].lower(),
            listing["description"].lower(),
            " ".join(listing["style_tags"]),
        ])
        return sum(1 for kw in keywords if kw in text)

    scored = [(listing, score(listing)) for listing in listings]
    scored = [(listing, s) for listing, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [listing for listing, _ in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1-2 complete outfits.
    """
    try:
        client = _get_groq_client()
        item_summary = (
            f"Item: {new_item['title']}\n"
            f"Category: {new_item['category']}\n"
            f"Colors: {', '.join(new_item['colors'])}\n"
            f"Style tags: {', '.join(new_item['style_tags'])}\n"
            f"Condition: {new_item['condition']}\n"
            f"Price: ${new_item['price']}"
        )

        if not wardrobe.get("items"):
            prompt = (
                f"A user is considering buying this secondhand item:\n\n{item_summary}\n\n"
                "They haven't told you what's in their wardrobe yet. Give them 1-2 outfit ideas "
                "describing what kinds of pieces would pair well with this item and what aesthetic "
                "or vibe it suits. Be specific about silhouettes, colors, and vibes rather than "
                "just saying 'jeans and a top'. Keep it to 3-4 sentences."
            )
        else:
            wardrobe_lines = "\n".join(
                f"- {item['name']} ({item['category']}, {', '.join(item['colors'])})"
                for item in wardrobe["items"]
            )
            prompt = (
                f"A user is considering buying this secondhand item:\n\n{item_summary}\n\n"
                f"Here's what they already own:\n{wardrobe_lines}\n\n"
                "Suggest 1-2 complete outfits that pair the new item with specific pieces from "
                "their wardrobe. Name the wardrobe pieces by name. Describe the overall vibe of "
                "each outfit and include one styling tip. Keep it to 4-5 sentences total."
            )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7,
        )
        result = response.choices[0].message.content.strip()
        return result if result else _suggest_fallback()

    except Exception:
        return _suggest_fallback()

def _suggest_fallback() -> str:
    return (
        "Couldn't generate an outfit suggestion right now. "
        "This item would pair well with classic basics like straight-leg jeans "
        "and clean sneakers as a starting point."
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    """
    if not outfit or not outfit.strip():
        return (
            "Couldn't generate a fit card because the outfit description was missing. "
            "Try running the search again."
        )

    try:
        client = _get_groq_client()
        prompt = (
            f"Write a 2-4 sentence Instagram or TikTok OOTD caption for this thrifted outfit.\n\n"
            f"Item: {new_item['title']}\n"
            f"Price: ${new_item['price']}\n"
            f"Platform: {new_item['platform']}\n"
            f"Outfit: {outfit}\n\n"
            "Rules: write in casual first-person, mention the item name once, the price once, "
            "and the platform once, all naturally woven in. Capture the specific vibe of the outfit "
            "rather than just describing what it is. Do not use hashtags. Sound like a real person "
            "posting, not a brand."
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.95,
        )
        result = response.choices[0].message.content.strip()
        return result if result else _fitcard_fallback(new_item)

    except Exception:
        return _fitcard_fallback(new_item)


def _fitcard_fallback(new_item: dict) -> str:
    return (
        f"Fit card unavailable right now, but here's the short version: "
        f"{new_item['title']} from {new_item['platform']} for ${new_item['price']}."
    )

# ── Tool 4: price_comparison ──────────────────────────────────────────────────

def price_comparison(item: dict) -> str:
    """
    Estimate whether the item's price is fair based on comparable listings
    in the dataset. Comparables are listings in the same category with at
    least one overlapping style_tag, excluding the item itself.
    """
    all_listings = load_listings()

    item_tags = set(item.get("style_tags", []))
    item_category = item.get("category", "")
    item_id = item.get("id", "")

    comparables = [
        l for l in all_listings
        if l["id"] != item_id
        and l["category"] == item_category
        and item_tags & set(l.get("style_tags", []))
    ]

    if len(comparables) < 2:
        return "Not enough comparable listings to estimate price fairness."

    avg_price = sum(l["price"] for l in comparables) / len(comparables)
    item_price = item["price"]
    direction = "below" if item_price < avg_price else "above"

    return (
        f"This ${item_price:.2f} {item_category.rstrip('s')} is priced {direction} the average "
        f"of ${avg_price:.2f} for similar {', '.join(item_tags)} items in the dataset "
        f"({len(comparables)} comparables found)."
    )