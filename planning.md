# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ...
- `size` (str): ...
- `max_price` (float): ...

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ...
- `wardrobe` (dict): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): ...
- `new_item` (dict): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     Use ASCII art or a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html).
     Do NOT embed an image — graders need to read your diagram directly in the file;
     an embedded image or screenshot cannot be evaluated.
     You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

**Milestone 4 — Planning loop and state management:**

---

## A Complete Interaction (Step by Step)

FitFindr is an AI thrift-shopping assistant that uses three tools in sequence to help users find secondhand clothing and style it. A search tool finds matching listings from the mock dataset; an outfit suggestion tool uses the top result and the user's existing wardrobe to suggest complete looks; and a fit card tool generates a shareable social-media-style caption that the user could use. If the search returns nothing, the agent stops immediately and tells the user what to try differently instead of passing empty data to the next tool.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query to extract keywords ("vintage graphic tee"), no explicit size, and a max price of $30. It calls `search_listings(description="vintage graphic tee", size=None, max_price=30.0)`. The tool filters listings.json, keeping only items priced at or under $30, then scores each by how many keywords from the description appear in the title, description, and style_tags. It returns a ranked list. The top result is lst_006: "Graphic Tee, 2003 Tour Bootleg Style", $24, size L, on Depop, with style_tags ["graphic tee", "vintage", "grunge", "streetwear", "band tee"]. The agent stores this in `session["search_results"]` and sets `session["selected_item"]` to lst_006.

**Step 2:**
With the selected item, the agent calls `suggest_outfit(new_item=lst_006, wardrobe=get_example_wardrobe())`. The wardrobe has 10 items including baggy dark-wash jeans (w_001), chunky white sneakers (w_007), black combat boots (w_008), and a vintage black denim jacket (w_006). The LLM receives both the item details and the wardrobe list and returns something like: "Pair this boxy graphic tee with your baggy dark-wash jeans and chunky white sneakers for a classic 90s streetwear look, and tuck the front corner slightly to add shape. For a grungier take, swap the sneakers for your black combat boots and throw the vintage denim jacket on top." The agent stores this in `session["outfit_suggestion"]`.

**Step 3:**
The agent calls `create_fit_card(outfit=session["outfit_suggestion"], new_item=lst_006)`. The LLM receives the outfit description and the item's title, price, and platform, and generates a short casual caption. It returns something like: "found this faded bootleg tee on depop for $24 and it was made for my baggy jeans era 🖤 styled it two ways: chunky sneakers for day, combat boots and a denim jacket when the sun goes down. thrift, don't buy new." The agent stores this in `session["fit_card"]`.

**Final output to user:**
The Gradio UI displays three panels: (1) the top listing: title, price, condition, size, platform; (2) the outfit suggestion with specific wardrobe pairings; (3) the fit card caption ready to copy and post.