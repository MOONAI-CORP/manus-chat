"""
MOONAI Chat Widget — Universal AI Backend
Works for ANY Shopify store. Configure via environment variables.
Powered by Claude claude-opus-4-5 / GPT-4.1-mini fallback.
"""

import os, json, re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from collections import defaultdict

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── STORE CONFIG — Set these as environment variables on Vercel ────────────────
# Required
STORE_NAME       = os.environ.get("STORE_NAME",       "Our Store")
STORE_URL        = os.environ.get("STORE_URL",         "https://yourstore.com")
AGENT_NAME       = os.environ.get("AGENT_NAME",        "Aria")
SUPPORT_EMAIL    = os.environ.get("SUPPORT_EMAIL",     "support@yourstore.com")

# Shipping & policies
SHIPPING_POLICY  = os.environ.get("SHIPPING_POLICY",   "FREE shipping on all orders — no minimum required.")
RETURN_POLICY    = os.environ.get("RETURN_POLICY",     "30-day hassle-free returns. Contact us with your order number.")
DELIVERY_TIME    = os.environ.get("DELIVERY_TIME",     "3–7 business days domestic. Ships within 1–3 business days.")

# Sale / promotions
CURRENT_SALE     = os.environ.get("CURRENT_SALE",      "")  # e.g. "15–30% OFF sitewide"

# Brand personality
BRAND_VIBE       = os.environ.get("BRAND_VIBE",        "helpful, friendly, and knowledgeable")
PRODUCT_CATEGORY = os.environ.get("PRODUCT_CATEGORY",  "products")  # e.g. "iPhone cases", "bedding", "bags"

# ── LIVE PRODUCT CATALOG ──────────────────────────────────────────────────────
_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "..", "store_data.json")
try:
    with open(_CATALOG_PATH) as f:
        _STORE_DATA = json.load(f)
    CATALOG = _STORE_DATA.get("catalog", [])
except Exception:
    CATALOG = []

def build_catalog_text():
    """Build a compact, AI-readable product catalog grouped by type."""
    by_type = defaultdict(list)
    for p in CATALOG:
        ptype = p.get("product_type") or "Products"
        by_type[ptype].append(p)

    lines = []
    for ptype, prods in sorted(by_type.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n### {ptype} ({len(prods)} products)")
        for p in prods[:10]:
            price = f"${p['price_min']:.2f}"
            if p.get("compare_price", 0) > p["price_min"]:
                pct = int((1 - p["price_min"] / p["compare_price"]) * 100)
                price += f" (was ${p['compare_price']:.2f}, {pct}% OFF)"
            opts = ""
            if p.get("options"):
                for k, v in list(p["options"].items())[:1]:
                    if k.lower() in ("model", "phone model", "size", "color"):
                        sample = [str(x) for x in v[:4]]
                        opts += f" | {k}: {', '.join(sample)}"
            lines.append(f"- **{p['title']}** — {price}{opts}")
            lines.append(f"  URL: {p['url']}")
    return "\n".join(lines)

CATALOG_TEXT = build_catalog_text()

# ── DYNAMIC SYSTEM PROMPT ─────────────────────────────────────────────────────
def build_system_prompt():
    sale_line = f"\nCurrent Sale: {CURRENT_SALE}" if CURRENT_SALE else ""
    return f"""You are **{AGENT_NAME}**, the AI sales concierge for **{STORE_NAME}**. You are embedded in the store's chat widget. Your sole purpose is to help visitors find the perfect product and convert them into buyers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONALITY & TONE — NON-NEGOTIABLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- You are {BRAND_VIBE} — confident, warm, knowledgeable
- NEVER say "Great question!", "I understand your concern", "As an AI", or any filler phrases
- SHORT messages ONLY: 1–3 sentences for conversational replies. This is a chat, not an email.
- Use 1–2 emojis per message. Natural placement. Never excessive.
- Ask ONLY ONE question per response — never stack questions
- NEVER write bullet points, headers, or paragraphs in your reply text
- Every message ends with either a question OR a clear CTA — never a dead end
- Sales first. Support second. Every message moves toward a purchase.
- Create natural urgency: "This is moving fast", "Sale ends soon", "Only a few left"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STORE KNOWLEDGE — VERIFIED FACTS ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand: {STORE_NAME}
Store: {STORE_URL}
Support: {SUPPORT_EMAIL}{sale_line}
Shipping: {SHIPPING_POLICY}
Delivery: {DELIVERY_TIME}
Returns: {RETURN_POLICY}
Payment: All major credit cards, PayPal, Shop Pay, Apple Pay, Google Pay.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIVE PRODUCT CATALOG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{CATALOG_TEXT}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSATION PHASES — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHASE 1 — OPEN (first message or proactive):
  Always context-aware. NEVER generic. Examples:
  - Homepage: "Hey! 👋 {f'We have {CURRENT_SALE} right now — ' if CURRENT_SALE else ''}what are you looking for today?"
  - Product page: "Love your taste! That's one of our best sellers. Want me to help you grab it?"
  - Collection page: "You're in the right place! What are you shopping for today?"
  - Cart page: "You're so close! 🛒 {SHIPPING_POLICY.split('.')[0]} — any questions before you checkout?"
  - Return visitor: "Welcome back! 👋 Still looking for that perfect {PRODUCT_CATEGORY}? Let me help 🔥"

PHASE 2 — QUALIFY (max 1 question):
  Ask ONE clarifying question to understand what they need.
  If context is clear from their message: SKIP directly to PHASE 3.
  NEVER ask more than 1 qualifying question before recommending.

PHASE 3 — RECOMMEND (ALWAYS include PRODUCT_CARDS):
  - Lead with 1 sentence about why this product fits them
  - Show 2–3 matching products from the catalog
  - Always show sale price + original price + discount % if on sale
  - End with: "Want to grab one or see more options?"
  - ALWAYS include PRODUCT_CARDS block when recommending

PHASE 4 — HANDLE OBJECTIONS:
  - "Too expensive" → Show lower-priced options from catalog with product cards
  - "Not sure" → "No worries! What's your vibe — [option A] or [option B]?"
  - "Need to think" → "Totally get it! Just so you know, sale prices won't last and these move fast 🔥"
  - "Just browsing" → "Of course! Want me to show you what's trending right now?"
  - "Do you have X?" → Check catalog, confirm yes/no, show card if yes

PHASE 5 — CLOSE (after 2+ exchanges about a product):
  - "Ready to grab it? Here's the link — {SHIPPING_POLICY.split('.')[0].lower()}!"
  - Add urgency: "This is moving fast 🔥"
  - Always include the product card again at close

PHASE 6 — UPSELL (after first product recommendation):
  ONE upsell only, framed as complementary:
  - Find a related product from the catalog that pairs well
  - "Most people also grab [related product] — want to see it?"

PHASE 7 — SUPPORT (order tracking, returns, shipping):
  Answer directly in 1–2 sentences. NEVER say "I'll look into that."
  - Tracking: "Check your email for a tracking link — or email {SUPPORT_EMAIL} with your order number!"
  - Returns: "{RETURN_POLICY} Email {SUPPORT_EMAIL} and we'll sort it right away!"
  - Shipping: "{SHIPPING_POLICY} 📦"

PHASE 8 — ESCALATE (frustrated customer):
  Trigger words: "ridiculous", "refund", "terrible", "manager", "lawsuit", "scam", "worst", "angry", "furious"
  Response: "I completely understand your frustration 😔 Let me connect you with our team right away — they'll make this right!"
  Then add ESCALATE:true to your response.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY OUTPUT FORMAT — EVERY RESPONSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Structure your response EXACTLY like this:

[Your 1–3 sentence conversational reply here]

PRODUCT_CARDS:{{"products":[{{"name":"Exact Product Title","price":"$XX.XX","original_price":"$XX.XX","discount":"XX% OFF","rating":"4.9","reviews":"200+","url":"{STORE_URL}/products/exact-handle","badge":"BEST SELLER","image":""}}]}}

CHIPS:["chip 1","chip 2","chip 3"]

RULES:
- ALWAYS include CHIPS in EVERY response — no exceptions
- Include PRODUCT_CARDS whenever you mention or recommend a product
- Leave image field as empty string "" — the system fills it from the catalog
- Use EXACT product URLs from the catalog above — never make up URLs
- Max 3 chips per response
- Chips must be SHORT (3–5 words max) and action-oriented
- NEVER include PRODUCT_CARDS for support/FAQ answers (shipping, returns, tracking)

CHIP EXAMPLES by phase:
- Opening: ["Browse {PRODUCT_CATEGORY}", "What's on sale? 🔥", "I need help choosing"]
- After qualifying: ["Show me options", "See bestsellers", "Filter by price"]
- After recommendation: ["Tell me more", "See more options", "I'll take it 🔥"]
- Objection: ["Show cheaper options", "What's the sale?", "See reviews"]
- Close: ["Complete my order", "Apply discount", "Talk to a human"]
- Support: ["Track my order", "Return policy", "Contact support"]
- Upsell: ["Show me that", "See the bundle", "No thanks"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NEVER give incorrect shipping info — always use: {SHIPPING_POLICY}
- NEVER recommend products not in the catalog
- NEVER write more than 3 sentences in your reply text
- NEVER use bullet points or headers in your reply text
- NEVER ask more than 1 question per response
- NEVER discuss competitors
- NEVER say "I don't know" — redirect to {SUPPORT_EMAIL} if needed
""".strip()

SYSTEM_PROMPT = build_system_prompt()

# ── AI CLIENT SETUP ───────────────────────────────────────────────────────────
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY")

if ANTHROPIC_KEY:
    import anthropic
    _anthropic = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    ENGINE = "claude-opus-4-5"
else:
    from openai import OpenAI
    _openai = OpenAI()
    ENGINE = "gpt-4.1-mini"

# ── PRODUCT SEARCH ────────────────────────────────────────────────────────────
def search_products(query: str, limit: int = 3) -> list:
    query_lower = query.lower()
    keywords = re.findall(r'\w+', query_lower)
    scored = []
    for p in CATALOG:
        score = 0
        text = f"{p['title']} {p.get('product_type','')} {' '.join(p.get('tags','') if isinstance(p.get('tags'), list) else [p.get('tags','')])} {p.get('description','')}".lower()
        for kw in keywords:
            if len(kw) < 3:
                continue
            if kw in p['title'].lower():
                score += 5
            elif kw in text:
                score += 2
        if p.get("available", True):
            score += 1
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]

# Build lookup indexes for fast image resolution
_CATALOG_BY_HANDLE = {p["handle"]: p for p in CATALOG}
_CATALOG_BY_TITLE  = {p["title"].lower(): p for p in CATALOG}

def resolve_catalog_image(name: str, url: str = "") -> str:
    """Always resolve product image from catalog — never trust AI-generated URLs."""
    found = _CATALOG_BY_TITLE.get(name.lower())
    if found and found.get("image"):
        return found["image"]
    if url:
        handle = url.rstrip("/").split("/")[-1]
        found = _CATALOG_BY_HANDLE.get(handle)
        if found and found.get("image"):
            return found["image"]
    name_lower = name.lower()
    for title, p in _CATALOG_BY_TITLE.items():
        if name_lower in title or title in name_lower:
            if p.get("image"):
                return p["image"]
    name_words = set(re.findall(r'\w{4,}', name_lower))
    best_score, best_img = 0, ""
    for p in CATALOG:
        if not p.get("image"):
            continue
        t_words = set(re.findall(r'\w{4,}', p["title"].lower()))
        score = len(name_words & t_words)
        if score > best_score:
            best_score, best_img = score, p["image"]
    if best_img:
        return best_img
    for p in CATALOG:
        if p.get("image"):
            return p["image"]
    return ""

def format_product_card(p: dict) -> dict:
    price = f"${p['price_min']:.2f}"
    original = f"${p['compare_price']:.2f}" if p.get('compare_price', 0) > p['price_min'] else None
    discount = None
    if p.get('compare_price', 0) > p['price_min']:
        pct = int((1 - p['price_min'] / p['compare_price']) * 100)
        discount = f"{pct}% OFF"
    image = p.get("image") or resolve_catalog_image(p["title"], p["url"])
    if discount and int(discount.replace("% OFF","")) >= 25:
        badge = f"{discount}"
    elif discount:
        badge = "ON SALE"
    else:
        badge = None
    return {
        "name": p["title"],
        "price": price,
        "original_price": original,
        "discount": discount,
        "badge": badge,
        "image": image,
        "url": p["url"],
        "rating": "4.9",
        "reviews": str(p.get("variant_count", 10) * 20) + "+",
    }

# ── MODELS ────────────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    store_context: Optional[str] = ""
    page_type: Optional[str] = "homepage"
    page_title: Optional[str] = ""

class ChatResponse(BaseModel):
    reply: str
    product_cards: Optional[List[dict]] = None
    chips: Optional[List[str]] = None
    escalate: Optional[bool] = False
    engine: str

class ProactiveRequest(BaseModel):
    page_type: Optional[str] = "homepage"
    page_title: Optional[str] = ""
    is_return_visitor: Optional[bool] = False

# ── HELPERS ───────────────────────────────────────────────────────────────────
def enforce_alternating(messages: List[Message]):
    out = []
    for m in messages:
        role = "user" if m.role == "user" else "assistant"
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n" + m.content
        else:
            out.append({"role": role, "content": m.content})
    if not out or out[0]["role"] != "user":
        out.insert(0, {"role": "user", "content": "Hello"})
    return out

def build_system(page_type=None, page_title=None, store_context=None):
    prompt = SYSTEM_PROMPT
    extras = []
    if page_type:
        extras.append(f"SHOPPER IS ON: {page_type} page")
    if page_title:
        extras.append(f"PAGE TITLE: {page_title}")
    if store_context:
        extras.append(f"CONTEXT: {store_context}")
    if extras:
        prompt += "\n\n## CURRENT SHOPPER CONTEXT\n" + "\n".join(extras)
    return prompt

def parse_response(raw: str):
    reply = raw
    product_cards = None
    chips = None
    escalate = False

    pc_match = re.search(r'PRODUCT_CARDS:\s*(\{[\s\S]*?\})\s*(?=CHIPS:|ESCALATE:|$)', raw)
    if not pc_match:
        pc_match = re.search(r'PRODUCT_CARDS:(\{[\s\S]*\})', raw)
    if pc_match:
        try:
            pc_data = json.loads(pc_match.group(1))
            raw_cards = pc_data.get("products", [])
            resolved_cards = []
            for card in raw_cards:
                card["image"] = resolve_catalog_image(
                    card.get("name", ""), card.get("url", "")
                )
                resolved_cards.append(card)
            if resolved_cards:
                product_cards = resolved_cards
            reply = reply[:pc_match.start()].strip() + reply[pc_match.end():].strip()
        except Exception:
            pass

    chips_match = re.search(r'CHIPS:\s*(\[[\s\S]*?\])', reply)
    if chips_match:
        try:
            chips = json.loads(chips_match.group(1))
            reply = reply[:chips_match.start()].strip() + reply[chips_match.end():].strip()
        except Exception:
            pass

    if "ESCALATE:true" in reply or "ESCALATE: true" in reply:
        escalate = True
        reply = re.sub(r'ESCALATE:\s*true', '', reply).strip()

    reply = reply.strip()

    if not chips:
        chips = [f"Browse {PRODUCT_CATEGORY}", "What's on sale? 🔥", "I need help choosing"]

    return reply, product_cards, chips, escalate

def call_ai(system: str, messages: list) -> str:
    if ANTHROPIC_KEY:
        cleaned = []
        for m in messages:
            if cleaned and cleaned[-1]["role"] == m["role"]:
                cleaned[-1]["content"] += "\n" + m["content"]
            else:
                cleaned.append({"role": m["role"], "content": m["content"]})
        if not cleaned or cleaned[0]["role"] != "user":
            cleaned.insert(0, {"role": "user", "content": "Hello"})
        resp = _anthropic.messages.create(
            model="claude-opus-4-5",
            max_tokens=500,
            system=system,
            messages=cleaned,
        )
        return resp.content[0].text
    else:
        msgs = [{"role": "system", "content": system}] + messages
        resp = _openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=msgs,
            max_tokens=500,
            temperature=0.72,
        )
        return resp.choices[0].message.content

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "engine": ENGINE,
        "products": len(CATALOG),
        "brand": STORE_NAME,
        "store_url": STORE_URL,
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    system = build_system(req.page_type, req.page_title, req.store_context)
    messages = enforce_alternating(req.messages)

    try:
        raw = call_ai(system, messages)
    except Exception as e:
        return ChatResponse(
            reply="I'm having a quick connection issue — please try again in a moment! 🙏",
            product_cards=[], chips=["Try again", f"Browse {PRODUCT_CATEGORY}", "Contact us"],
            escalate=False, engine=ENGINE
        )

    reply, product_cards, chips, escalate = parse_response(raw)

    # Auto-inject product cards if AI recommended products but forgot the PRODUCT_CARDS block
    if not product_cards and req.messages:
        last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        trigger_words = ["show me", "recommend", "best", "looking for", "what do you have",
                         "i have", "my phone", "i want", "do you have", "can i get",
                         "what's good", "help me find", "suggest"]
        if any(kw in last_user.lower() for kw in trigger_words):
            found = search_products(last_user, limit=3)
            if found:
                product_cards = [format_product_card(p) for p in found]

    return ChatResponse(
        reply=reply,
        product_cards=product_cards or [],
        chips=chips or [f"Browse {PRODUCT_CATEGORY}", "What's on sale? 🔥", "I need help choosing"],
        escalate=escalate,
        engine=ENGINE,
    )

@app.post("/proactive")
async def proactive(req: ProactiveRequest):
    page_type = req.page_type or "homepage"
    page_title = req.page_title or ""
    is_return = req.is_return_visitor or False
    sale_note = f" Mention {CURRENT_SALE} sale." if CURRENT_SALE else ""

    if page_type == "product" and page_title:
        prompt = f"Generate a proactive chat opener for a customer viewing '{page_title}' on {STORE_NAME}.{sale_note} Be specific to this product. Keep message under 15 words."
        default_chips = ["Tell me more", "Check my size", "See similar"]
    elif page_type == "collection":
        prompt = f"Generate a proactive chat opener for a customer browsing the '{page_title or PRODUCT_CATEGORY}' collection on {STORE_NAME}.{sale_note} Keep message under 15 words."
        default_chips = ["Help me choose", "See bestsellers", "Filter by price"]
    elif page_type == "cart":
        prompt = f"Generate a proactive chat opener for a customer with items in their cart on {STORE_NAME}. Encourage checkout, mention free shipping. Keep message under 15 words."
        default_chips = ["Complete my order", "Apply discount", "I have a question"]
    elif is_return:
        prompt = f"Generate a proactive chat opener for a RETURN visitor to {STORE_NAME}. Welcome them back warmly.{sale_note} Keep message under 15 words."
        default_chips = ["Show new arrivals", "See my favorites", "Get help"]
    else:
        prompt = f"Generate a proactive chat opener for a new visitor to {STORE_NAME} ({PRODUCT_CATEGORY} store).{sale_note} Keep message under 15 words."
        default_chips = [f"Browse {PRODUCT_CATEGORY}", "What's on sale? 🔥", "I need help choosing"]

    system = f"""You are {AGENT_NAME}, AI concierge for {STORE_NAME}. Generate a proactive bubble message.
Return ONLY valid JSON in this exact format:
{{"message": "Your short message here (under 15 words)", "chips": ["Chip 1", "Chip 2", "Chip 3"]}}
Chips must be 3-4 words max. Message must be warm, specific, and create curiosity."""

    try:
        raw = call_ai(system, [{"role": "user", "content": prompt}])
        json_match = re.search(r'\{[\s\S]*\}', raw.strip())
        if json_match:
            data = json.loads(json_match.group())
            msg = data.get("message", "")
            chips = data.get("chips", default_chips)
            if msg:
                return {"message": msg, "chips": chips[:3]}
    except Exception:
        pass

    # Fallback messages
    sale_fallback = f" {CURRENT_SALE} right now ⚡" if CURRENT_SALE else ""
    fallbacks = {
        "product": {"message": f"Love your taste! This one's trending right now 🔥", "chips": ["Tell me more", "See more options", "Add to cart"]},
        "cart": {"message": f"You're so close! 🛒 {SHIPPING_POLICY.split('.')[0]}!", "chips": ["Complete my order", "Apply discount", "Need help?"]},
        "collection": {"message": f"Need help finding the perfect {PRODUCT_CATEGORY}? 👀", "chips": ["Help me choose", "See bestsellers", "Filter by price"]},
        "homepage": {"message": f"Hey! 👋{sale_fallback} How can I help you today?", "chips": [f"Browse {PRODUCT_CATEGORY}", "What's on sale?", "I need help"]},
    }
    return fallbacks.get(page_type, fallbacks["homepage"])
