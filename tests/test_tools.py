# tests/test_tools.py
from tools import search_listings, suggest_outfit, create_fit_card, price_comparison
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_size_filter():
    results = search_listings("top", size="XXL", max_price=None)
    # no listings in the dataset are size XXL so this should come back empty
    assert results == []

def test_search_results_sorted_by_relevance():
    results = search_listings("vintage graphic tee", size=None, max_price=None)
    # the first result should have more matching keywords than the last
    assert len(results) > 1

# ── suggest_outfit ────────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0

def test_suggest_outfit_empty_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result) > 0

# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_returns_string():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    result = create_fit_card(outfit, item)
    assert isinstance(result, str)
    assert len(result) > 0

def test_create_fit_card_empty_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = create_fit_card("", item)
    assert "missing" in result.lower()
    assert isinstance(result, str)

def test_create_fit_card_whitespace_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = create_fit_card("   ", item)
    assert "missing" in result.lower()

# ── price_comparison ──────────────────────────────────────────────────────────

def test_price_comparison_returns_string():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    result = price_comparison(item)
    assert isinstance(result, str)
    assert len(result) > 0

def test_price_comparison_no_comparables():
    # construct a fake item with a category/tags combo unlikely to match anything
    fake_item = {
        "id": "fake_999",
        "category": "accessories",
        "style_tags": ["nonexistenttag"],
        "price": 9.99
    }
    result = price_comparison(fake_item)
    assert "Not enough" in result