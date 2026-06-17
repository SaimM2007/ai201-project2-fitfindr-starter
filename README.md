# FitFindr
 
FitFindr is a multi-tool AI agent that helps you find secondhand clothing and figure out how to wear it. You describe what you're looking for in plain English, and the agent searches a dataset of thrift listings, suggests outfits using your existing wardrobe, and generates a shareable caption for the look to share on social media.

## What's Included
 
```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── tests/
│   └── test_tools.py          # Pytest tests for all three tools and their failure modes
├── conftest.py                # Adds project root to Python path so pytest can find tools.py
├── agent.py                   # Planning loop and session state
├── app.py                     # Gradio interface
├── tools.py                   # The three core tools
├── planning.md                # Spec and architecture written before any code implementation
└── requirements.txt           # Python dependencies
```

---

## Setup
 
**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
 
**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```
 
Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```
 
Run the app:
```bash
python app.py
```
 
Then open the URL shown in your terminal (usually `http://localhost:7860`).
 
---

## Tool Inventory
 
### `search_listings(description, size, max_price)`
 
Searches the mock listings dataset for secondhand items that match a text description, optional size, and optional price ceiling. Loads all listings with `load_listings()`, filters by price and size if those parameters are provided, then scores each remaining listing by counting how many keywords from `description` appear across its `title`, `description`, and `style_tags` fields. Listings with a score of zero are dropped, and the rest are returned sorted by relevance score highest first.
 
**Parameters:**
- `description` (str): keywords describing the item, like `"vintage graphic tee"`
- `size` (str or None): size string like `"M"` or `"W30"`, matched case-insensitively; `None` skips size filtering
- `max_price` (float or None): price ceiling in dollars, inclusive; `None` skips price filtering
**Returns:** a list of listing dicts sorted by relevance, each containing `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. Returns an empty list if nothing matches — never raises an exception.

---

### `suggest_outfit(new_item, wardrobe)`
 
Takes the thrifted item the user is considering and their existing wardrobe, then calls the LLM to suggest one or two complete outfits that incorporate the new piece alongside things they already own. If the wardrobe is empty, it calls the LLM with a different prompt asking for general styling advice instead of specific pairings.
 
**Parameters:**
- `new_item` (dict): a listing dict from `search_listings`
- `wardrobe` (dict): a wardrobe dict with an `items` key containing a list of wardrobe item dicts; the list may be empty
**Returns:** a non-empty string with outfit suggestions naming specific wardrobe pieces, or general styling advice if the wardrobe is empty. Always returns a string — never raises an exception.
 
---
 
### `create_fit_card(outfit, new_item)`
 
Generates a short, casual Instagram or TikTok-style caption for the thrifted outfit. Uses a higher LLM temperature (0.95) so the output feels varied across different inputs rather than templated.
 
**Parameters:**
- `outfit` (str): the outfit suggestion string returned by `suggest_outfit`
- `new_item` (dict): the listing dict for the thrifted item
**Returns:** a 2 to 4 sentence string in casual first-person voice that mentions the item name, price, and platform once each. If `outfit` is empty or whitespace, returns an error message string instead of calling the LLM. Never raises an exception.
 
---
 
### `price_comparison(item)` — stretch feature
 
Estimates whether the selected item's price is fair by finding comparable listings in the same category with at least one overlapping style tag, then comparing prices. Runs automatically after `search_listings` finds a result and stores the output in `session["price_comparison"]`.
 
**Parameters:**
- `item` (dict): a listing dict for the item the user is considering; uses `id`, `category`, `style_tags`, and `price`
**Returns:** a string estimating whether the price is fair relative to similar listings, like "This $18.00 top is priced below the average of $22.00 for similar vintage, y2k items in the dataset (14 comparables found)." Returns "Not enough comparable listings to estimate price fairness." if fewer than two comparables exist. Never raises an exception.
 
---
 
## Stretch Features
 
### Price Comparison
 
`price_comparison(item)` is implemented in `tools.py` and wired into the planning loop in `agent.py` at Step 4b, right after the top search result is selected. It loads all listings, finds ones in the same category with at least one overlapping style tag, excludes the item itself by id, and computes the average price of comparables. The result is stored in `session["price_comparison"]` and displayed in the Gradio UI alongside the listing details.
 
### Retry Logic with Fallback
 
If `search_listings` returns an empty list and a size was provided in the query, the planning loop automatically retries with `size=None` and stores a notice in `session["size_notice"]` so the user knows the filter was removed. If the retry also returns empty, the agent sets `session["error"]` and returns early as normal. This logic lives in `run_agent()` in `agent.py` at Step 3.
 
Example from testing: querying "vintage graphic tee size XXL" returned no results on the first pass since no listings are size XXL, then retried without the size filter and found the Y2K Baby Tee, printing "No results found for size 'XXL', so the size filter was removed. Showing the closest matches instead."
 
---

## Planning Loop
 
The agent runs as a single linear pass through a session dict with two possible early-exit points. The loop does not retry or branch based on content — it makes one decision at each step: whether to continue or stop.
 
Here is the exact logic:
 
1. The session is initialized with the user's query and wardrobe stored as fixed keys.
2. The query is sent to the LLM, which extracts three structured fields: a description string, a size string or null, and a max price as a float or null. If parsing fails or returns an empty description, the agent sets `session["error"]` and returns immediately.
3. `search_listings` is called with the extracted parameters. If the result is an empty list and a size was provided, the agent retries with `size=None` (stretch feature). If still empty, the agent sets a specific error message in `session["error"]` and returns immediately without calling the remaining tools.
4. The top result from the list is stored in `session["selected_item"]`. `price_comparison` is called on it immediately after (stretch feature).
5. `suggest_outfit` is called with `selected_item` and the wardrobe. This tool always returns a non-empty string, so the loop always continues after this step.
6. `create_fit_card` is called with the outfit suggestion string and `selected_item`. This tool also always returns something.
7. The completed session is returned with `session["error"]` set to None.
The key decision the loop makes is at step 3: if search returns nothing even after a retry, the interaction ends there. The agent never calls the styling tools with empty input.
 
---
 
## State Management
 
All state lives in a single session dict created by `_new_session()` at the start of each run. The keys are: `query` (the original input, never modified), `parsed` (the extracted description, size, and max_price), `search_results` (the full list of matching listings), `selected_item` (the single listing dict passed into the remaining tools), `wardrobe` (the wardrobe dict passed in at the start), `outfit_suggestion` (the string from `suggest_outfit`), `fit_card` (the string from `create_fit_card`), `price_comparison` (the string from the stretch tool), `size_notice` (set if the size filter was removed on retry), and `error` (a message string or None).
 
The tools themselves are stateless functions — they receive inputs and return outputs and never touch the session directly. The planning loop is the only thing that reads from and writes to the session dict. Information flows forward: `selected_item` is set after search and passed into both `suggest_outfit` and `create_fit_card`, and `outfit_suggestion` is set after suggest and passed into `create_fit_card`. The user never has to re-enter anything between steps.
 
---

## Interaction Walkthrough
 
**User query:** "looking for a vintage graphic tee under $30"
 
**Step 1 — Tool called: `search_listings`**
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0`
- Why this tool: the agent always searches first — there's nothing to style until a real listing exists
- Output: a ranked list of matching listings; top result is "Y2K Baby Tee — Butterfly Print", $18, size S, Depop
**Step 2 — Tool called: `suggest_outfit`**
- Input: the Y2K Baby Tee listing dict, the example wardrobe with 10 items
- Why this tool: search returned a result, so the agent proceeds to styling using the top match and the user's wardrobe
- Output: "The Y2K Baby Tee can be paired with the Baggy straight-leg jeans and Chunky white sneakers for a casual, vintage-inspired look. For a grungier take, try layering the Vintage black denim jacket over the tee."
**Step 3 — Tool called: `create_fit_card`**
- Input: the outfit suggestion string from step 2, the Y2K Baby Tee listing dict
- Why this tool: outfit suggestion succeeded, so the agent generates a shareable caption using the outfit context and item details
- Output: "I'm totally obsessing over my new Y2K Baby Tee that I scored on depop for $18 — it's giving me all the nostalgic feels. Paired it with baggy jeans and chunky sneakers for everyday vibes."
**Final output to user:** three panels in the Gradio UI — listing details with price comparison (title, price, size, condition, platform, price fairness estimate), the outfit suggestion with specific wardrobe pairings, and the fit card caption ready to copy and post.
 
---
 
## Error Handling and Fail Points
 
| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match the description, size, and price filters (including after retry with size removed) | Sets `session["error"]` to "No listings found for '[description]' in size [size] under $[price]. Try broadening your search by removing the size filter, raising your price limit, or using different keywords." Returns the session immediately without calling the remaining tools. |
| `suggest_outfit` | Wardrobe is empty (`wardrobe["items"] == []`) | Calls the LLM with a general styling prompt that omits the wardrobe items list entirely, returning advice about what kinds of pieces and aesthetics pair well with the item instead of naming specific wardrobe pieces. Never crashes. |
| `create_fit_card` | `outfit` argument is empty or whitespace | Returns "Couldn't generate a fit card because the outfit description was missing. Try running the search again." without calling the LLM. Never raises an exception. |
| `price_comparison` | Fewer than two comparable listings exist | Returns "Not enough comparable listings to estimate price fairness." and never raises. The agent stores this string and continues normally. |
 
**Concrete example from testing:** running `create_fit_card('', results[0])` directly in the terminal returned the error string immediately without making an API call. Running the full agent with "designer ballgown size XXS under $5" returned the no-results error message with specific suggestions, and `session["fit_card"]` was confirmed as `None` — meaning `suggest_outfit` and `create_fit_card` were never called.
 
---

## AI Tool Usage
 
**Instance 1 - implementing `search_listings`:** I gave Claude the Tool 1 block from planning.md, including the input parameters, return value description, and failure mode, and asked it to implement the function using `load_listings()` from the data loader. It produced a working implementation. Before using it I checked that it filtered by all three parameters independently, scored by keyword overlap across `title`, `description`, and `style_tags`, dropped zero-score listings, and returned an empty list rather than raising when nothing matched. I then verified with three pytest test cases before moving on.
 
**Instance 2 - implementing the planning loop:** I gave Claude the Planning Loop section, the State Management section, and the Mermaid architecture diagram from planning.md and asked it to implement `run_agent()` in agent.py. The generated code matched the spec closely. One thing I verified manually before trusting it was that the early-exit after an empty search result was actually present and that `suggest_outfit` was not being called on that path. I confirmed this by running the no-results CLI test case in agent.py and checking that `fit_card is None: True` printed correctly.

---

## Spec Reflection
 
**One way planning.md helped during implementation:** Writing out the exact conditional logic in the Planning Loop section before writing any code meant I could give Claude a precise spec for `run_agent()` rather than a vague description. The Mermaid diagram in particular made the early-exit branches unambiguous. Without it, the no-results early exit would have been easy to accidentally leave out or put in the wrong place, and I had a concrete spec to check the generated code against before running it.
 
**One divergence from your spec, and why:** The spec described the query parsing step as extracting parameters from the user's natural language input, but didn't nail down whether to use the LLM or a simpler string-matching approach. The implementation uses the LLM to parse the query with a fallback to using the raw query string as the description if parsing fails. This is more robust than keyword matching because natural language queries don't follow a predictable format ("looking for something vintage under thirty bucks" would break a regex but not an LLM parse), and the fallback means the agent still produces results even when the parse step fails completely.