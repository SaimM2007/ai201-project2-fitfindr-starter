"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

from tools import search_listings, suggest_outfit, create_fit_card, price_comparison

load_dotenv()


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set.")
    return Groq(api_key=api_key)


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "price_comparison": None,    # string returned by price_comparison (stretch feature)
        "size_notice": None,         # set if size filter was removed on retry (stretch feature)
        "error": None,               # set if the interaction ended early
    }


# Helper function to parse the query using the LLM. This is separate from the main agent loop so we can test it in isolation and keep the main loop cleaner.
def _parse_query(query: str) -> dict:
    """
    Ask the LLM to extract description, size, and max_price from the user's query.
    Returns a dict with keys: description (str), size (str or None), max_price (float or None).
    Falls back to using the full query as the description if parsing fails.
    """
    try:
        client = _get_groq_client()
        prompt = (
            "Extract search parameters from this thrift shopping query. "
            "Return ONLY a JSON object with exactly these keys:\n"
            '- "description": the item being searched for (str)\n'
            '- "size": clothing size if mentioned, otherwise null\n'
            '- "max_price": maximum price as a number if mentioned, otherwise null\n\n'
            f'Query: "{query}"\n\n'
            "Return only the JSON object, no explanation."
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1,
        )
        text = response.choices[0].message.content.strip()
        # strip markdown code fences if the LLM added them
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        return {
            "description": parsed.get("description", query),
            "size": parsed.get("size", None),
            "max_price": parsed.get("max_price", None),
        }
    except Exception:
        # fall back to using the raw query as the description
        return {"description": query, "size": None, "max_price": None}


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """
    # Step 1: initialize session
    session = _new_session(query, wardrobe)

    # Step 2: parse the query to extract description, size, and max_price
    parsed = _parse_query(query)
    session["parsed"] = parsed

    description = parsed.get("description", "").strip()
    if not description:
        session["error"] = (
            "Couldn't understand your query. "
            "Try something like: 'vintage graphic tee under $30, size M'."
        )
        return session

    size = parsed.get("size")
    max_price = parsed.get("max_price")

    # Step 3: call search_listings() with the parsed parameters.
    # If no results and a size was provided, retry with size=None and notify the user.
    # (stretch feature: retry logic with fallback)
    # If still no results: set session["error"] and return early.
    # Do NOT proceed to suggest_outfit with empty input.
    results = search_listings(description, size=size, max_price=max_price)

    if not results and size is not None:
        # retry with size filter removed
        results = search_listings(description, size=None, max_price=max_price)
        if results:
            session["size_notice"] = (
                f"No results found for size '{size}', so the size filter was removed. "
                "Showing the closest matches instead."
            )
            session["parsed"]["size"] = None
            size = None

    session["search_results"] = results

    if not results:
        parts = [f"No listings found for '{description}'"]
        if size:
            parts.append(f"in size {size}")
        if max_price:
            parts.append(f"under ${max_price}")
        session["error"] = (
            " ".join(parts) + ". Try broadening your search by removing the size "
            "filter, raising your price limit, or using different keywords."
        )
        return session

    # Step 4: select the item to use (top result)
    session["selected_item"] = results[0]

    # Step 4b: run price comparison on the selected item (stretch feature)
    session["price_comparison"] = price_comparison(session["selected_item"])

    # Step 5: call suggest_outfit() with the selected item and wardrobe
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], wardrobe
    )

    # Step 6: call create_fit_card() with the outfit suggestion and selected item
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: return the completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"Price comparison: {session['price_comparison']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"fit_card is None: {session2['fit_card'] is None}")

    print("\n\n=== Retry path: specific size that won't match ===\n")
    session3 = run_agent(
        query="vintage graphic tee size XXL",
        wardrobe=get_example_wardrobe(),
    )
    if session3["size_notice"]:
        print(f"Notice: {session3['size_notice']}")
    if session3["error"]:
        print(f"Error: {session3['error']}")
    else:
        print(f"Found: {session3['selected_item']['title']}")
        print(f"Price comparison: {session3['price_comparison']}")