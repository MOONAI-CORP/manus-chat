"""
Limited Armor — AI Chat Widget Backend
Rep AI-level sales concierge powered by Claude / GPT-4.1-mini
Deploy: pip install fastapi uvicorn anthropic openai
        ANTHROPIC_API_KEY=sk-ant-... uvicorn api:app --host 0.0.0.0 --port 8001
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

# ── LIVE PRODUCT CATALOG ──────────────────────────────────────────────────────
_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "store_data.json")
try:
    with open(_CATALOG_PATH) as f:
        _STORE_DATA = json.load(f)
    CATALOG = _STORE_DATA.get("catalog", [])
except Exception:
    CATALOG = []

def build_catalog_text():
    by_type = defaultdict(list)
    for p in CATALOG:
        ptype = p.get("product_type") or "Cases"
        by_type[ptype].append(p)
    lines = []
    for ptype, prods in sorted(by_type.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n### {ptype} ({len(prods)} products)")
        for p in prods[:6]:
            price = f"${p['price_min']:.2f}"
            if p["compare_price"] > p["price_min"]:
                pct = int((1 - p["price_min"] / p["compare_price"]) * 100)
                price += f" (was ${p['compare_price']:.2f}, {pct}% OFF)"
            opts = ""
            if p.get("options"):
                for k, v in list(p["options"].items())[:2]:
                    opts += f" | {k}: {', '.join(str(x) for x in v[:4])}"
            lines.append(f"- **{p['title']}** — {price}{opts}")
            lines.append(f"  URL: {p['url']}")
    return "\n".join(lines)

CATALOG_TEXT = build_catalog_text()

# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are **Armie**, the AI sales concierge for **Limited Armor** — a premium designer iPhone case and accessories brand. You are the digital face of the brand: confident, stylish, knowledgeable, and laser-focused on converting visitors into buyers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSONALITY & TONE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Confident, sleek, stylish — like a luxury brand associate, NOT a corporate bot
- SHORT messages: 2–3 sentences max. This is a chat, not an email.
- Use 1–2 emojis per message. Keep it premium, not spammy.
- Always end with a question OR a clear CTA to keep the conversation moving
- Create natural urgency: "This is flying off the shelves", "Sale prices won't last"
- Never say "I am an AI" — you ARE Armie, Limited Armor's concierge
- Sales first. Support second. Every message moves toward a purchase.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRAND & STORE KNOWLEDGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand: Limited Armor
Positioning: Premium / designer / luxury iPhone cases & accessories
Store URL: https://limitedarmor.com
Support: support@limitedarmor.com
Current Sale: 15–30% OFF storewide
Shipping: Ships within 1–3 business days. Free shipping on orders over $35.
Returns: 30-day hassle-free returns. Email support@limitedarmor.com.
Tracking: Tracking email sent within 24 hours of shipment.

COLLECTIONS:
- iPhone 17 Series — Latest iPhone 17 Pro Max cases
- iPhone Cases — Full iPhone lineup coverage
- MagSafe Cases — MagSafe-compatible cases
- MagSafe Wallets — Slim card holders ($34.99)
- Samsung Cases — Galaxy series
- Pixel Cases — Google Pixel series
- Watch Bands — Premium Apple Watch bands (steel, braided, bangle, mesh)
- Minimal Series — Clean, everyday carry cases ($28.99)
- Pure Lux Series — Ultra-premium limited edition
- Street Series — Bold graphic streetwear cases
- Keychains — Designer accessories

PRODUCT LINES:
1. Impact+ Series — Premium drop-protection, designer colorways (Pastel Pink, Deep Blue, Cosmic Orange). $33.99 (was $39.99). 15% OFF.
2. Mono Series — Minimalist monochrome. Sleek, understated luxury. $33.99.
3. DR Series — Dual-layer reinforced protection. $33.99.
4. Street Series — Bold graphic streetwear aesthetic. $29.99.
5. Pure Lux Series — Ultra-premium, limited edition. $29.99–$33.99.
6. Minimal Series — Clean, simple, everyday. $28.99.
7. Puffer Signature — Iconic puffer texture, fashion-forward. $29.99.
8. Apple Watch Bands — Premium steel, braided, bangle, mesh. $32.99–$39.99 (was $49.99). 30% OFF.
9. MagSafe Wallets — Slim card holders. $34.99.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LIVE PRODUCT CATALOG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{CATALOG_TEXT}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSATION FLOW — REP AI STYLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — OPEN: Warm greeting, mention sale, ask qualifying question (what phone model?)
PHASE 2 — DISCOVER: Get phone model + style preference (minimal/bold/protective/fashion)
PHASE 3 — RECOMMEND: Show 2–3 specific products with PRODUCT_CARDS. Always show sale price + original price.
PHASE 4 — OBJECTIONS:
  - "Too expensive" → Already 15–30% OFF. Mention Minimal Series at $28.99.
  - "Not sure on color" → Ask their preference, match to colorways.
  - "Need to think" → "These sale prices won't last — Impact+ is our #1 seller and moves fast 🔥"
  - "Do you have X model?" → Check catalog and confirm.
PHASE 5 — CLOSE: Direct link + urgency nudge. "Takes 2 minutes to order — want the link?"
PHASE 6 — UPSELL:
  - iPhone case → suggest matching Apple Watch Band (same colorway)
  - Watch band → suggest matching phone case
  - MagSafe case → suggest MagSafe wallet
  - Any case → suggest keychain

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY OUTPUT FORMAT — FOLLOW EXACTLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Every response MUST include ALL of these:

1. Your conversational reply (2–3 sentences max)

2. PRODUCT_CARDS block (when recommending products):
PRODUCT_CARDS:{{"products":[{{"name":"Product Name","price":"$33.99","original_price":"$39.99","discount":"15% OFF","rating":"4.9","reviews":"312","url":"https://limitedarmor.com/products/handle","badge":"BEST SELLER","image":"https://cdn.shopify.com/..."}}]}}

3. CHIPS block (ALWAYS — every single response):
CHIPS:["chip 1","chip 2","chip 3"]

Contextual chip examples:
- Opening: ["Shop iPhone Cases", "See Watch Bands", "What's on sale?"]
- Discovery: ["I have iPhone 16", "I have iPhone 17", "Show me Samsung"]
- Post-recommendation: ["Tell me more", "See other colors", "Add to cart"]
- Objection: ["Show cheaper options", "What's the sale?", "I'll take it"]
- Support: ["Track my order", "Return policy", "Talk to a human"]

ESCALATION — when customer wants human or is upset:
Say: "Of course! Reach our team at support@limitedarmor.com — they'll take great care of you right away! 💙"
Then add: ESCALATE:true

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES YOU NEVER BREAK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ALWAYS include CHIPS in every single response
- ALWAYS include PRODUCT_CARDS when recommending products
- NEVER write more than 3 sentences in your reply text
- NEVER end without a question or CTA
- NEVER say "I don't know" — redirect to support if needed
- NEVER discuss competitors
- ONLY recommend products that exist in the catalog above
- ALWAYS use the customer's stated phone model in recommendations
""".strip()

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
        text = f"{p['title']} {p.get('product_type','')} {p.get('tags','')} {p.get('description','')}".lower()
        for kw in keywords:
            if len(kw) < 3:
                continue
            if kw in text:
                score += 2
            if kw in p['title'].lower():
                score += 3
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:limit]]

# Build a lookup index for fast image resolution by handle and title
_CATALOG_BY_HANDLE = {p["handle"]: p for p in CATALOG}
_CATALOG_BY_TITLE  = {p["title"].lower(): p for p in CATALOG}

def resolve_catalog_image(name: str, url: str = "") -> str:
    """Always return a real Shopify CDN image URL from the catalog.
    Tries: exact title match → handle from URL → fuzzy title match → first catalog image."""
    # 1. Exact title match
    found = _CATALOG_BY_TITLE.get(name.lower())
    if found and found.get("image"):
        return found["image"]
    # 2. Extract handle from URL and look up
    if url:
        handle = url.rstrip("/").split("/")[-1]
        found = _CATALOG_BY_HANDLE.get(handle)
        if found and found.get("image"):
            return found["image"]
    # 3. Fuzzy: find catalog product whose title is most similar
    name_lower = name.lower()
    for title, p in _CATALOG_BY_TITLE.items():
        if name_lower in title or title in name_lower:
            if p.get("image"):
                return p["image"]
    # 4. Keyword overlap fallback
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
    # 5. Absolute fallback — first product image in catalog
    for p in CATALOG:
        if p.get("image"):
            return p["image"]
    return ""

def format_product_card(p: dict) -> dict:
    price = f"${p['price_min']:.2f}"
    original = f"${p['compare_price']:.2f}" if p['compare_price'] > p['price_min'] else None
    discount = None
    if p['compare_price'] > p['price_min']:
        pct = int((1 - p['price_min'] / p['compare_price']) * 100)
        discount = f"{pct}% OFF"
    # Always resolve image from catalog — never trust AI-generated URLs
    image = p.get("image") or resolve_catalog_image(p["title"], p["url"])
    return {
        "name": p["title"],
        "price": price,
        "original_price": original,
        "discount": discount,
        "badge": "BEST SELLER" if CATALOG and p["id"] == CATALOG[0]["id"] else ("ON SALE" if discount else None),
        "image": image,
        "url": p["url"],
        "rating": "4.9",
        "reviews": "200+",
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
        extras.append(f"Current page type: {page_type}")
    if page_title:
        extras.append(f"Current page: {page_title}")
    if store_context:
        extras.append(f"Context: {store_context}")
    if extras:
        prompt += "\n\n## CURRENT SHOPPER CONTEXT\n" + "\n".join(extras)
    return prompt

def parse_response(raw: str):
    reply = raw
    product_cards = None
    chips = None
    escalate = False

    # Extract PRODUCT_CARDS
    pc_match = re.search(r'PRODUCT_CARDS:(\{.*?\}\s*\]?\s*\})', raw, re.DOTALL)
    if pc_match:
        try:
            pc_data = json.loads(pc_match.group(1))
            raw_cards = pc_data.get("products", [])
            # Always resolve images from catalog — override any AI-hallucinated image URLs
            for card in raw_cards:
                card["image"] = resolve_catalog_image(
                    card.get("name", ""), card.get("url", "")
                )
            product_cards = raw_cards
            reply = reply.replace("PRODUCT_CARDS:" + pc_match.group(1), "").strip()
        except Exception:
            pass

    # Extract CHIPS
    chips_match = re.search(r'CHIPS:(\[.*?\])', raw, re.DOTALL)
    if chips_match:
        try:
            chips = json.loads(chips_match.group(1))
            reply = reply.replace("CHIPS:" + chips_match.group(1), "").strip()
        except Exception:
            pass

    # Extract ESCALATE
    if "ESCALATE:true" in raw:
        escalate = True
        reply = reply.replace("ESCALATE:true", "").strip()

    reply = reply.strip()

    if not chips:
        chips = ["Shop iPhone Cases", "See Watch Bands", "What's on sale?"]

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
            max_tokens=450,
            system=system,
            messages=cleaned,
        )
        return resp.content[0].text
    else:
        msgs = [{"role": "system", "content": system}] + messages
        resp = _openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=msgs,
            max_tokens=450,
            temperature=0.75,
        )
        return resp.choices[0].message.content

# ── ENDPOINTS ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "engine": ENGINE, "products": len(CATALOG), "brand": "Limited Armor"}

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    system = build_system(req.page_type, req.page_title, req.store_context)
    messages = enforce_alternating(req.messages)

    try:
        raw = call_ai(system, messages)
    except Exception as e:
        return ChatResponse(
            reply="I'm having a quick connection issue — please try again in a moment! 🙏",
            product_cards=[], chips=["Try again", "Shop Cases", "Contact us"],
            escalate=False, engine=ENGINE
        )

    reply, product_cards, chips, escalate = parse_response(raw)

    # Auto-inject product cards if AI didn't return them but user is asking about products
    if not product_cards and req.messages:
        last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        trigger_words = ["show me", "recommend", "best", "case", "band", "wallet", "looking for",
                         "what do you have", "iphone", "samsung", "pixel", "magsafe", "watch"]
        if any(kw in last_user.lower() for kw in trigger_words):
            found = search_products(last_user, limit=2)
            if found:
                product_cards = [format_product_card(p) for p in found]

    return ChatResponse(
        reply=reply,
        product_cards=product_cards or [],
        chips=chips or ["Shop iPhone Cases", "See Watch Bands", "What's on sale?"],
        escalate=escalate,
        engine=ENGINE,
    )

@app.post("/proactive")
async def proactive(req: ProactiveRequest):
    page_type = req.page_type or "homepage"
    page_title = req.page_title or ""

    prompts = {
        "product": f"Generate a proactive chat opener for a customer viewing '{page_title}' on Limited Armor. Be specific, mention the sale. Return JSON: {{\"message\": \"...\", \"chips\": [\"...\", \"...\", \"...\"]}}",
        "collection": f"Generate a proactive chat opener for a customer browsing the '{page_title}' collection on Limited Armor. Return JSON: {{\"message\": \"...\", \"chips\": [\"...\", \"...\", \"...\"]}}",
        "cart": "Generate a proactive chat opener for a customer with items in their cart on Limited Armor. Encourage checkout, mention free shipping over $35. Return JSON: {\"message\": \"...\", \"chips\": [\"...\", \"...\", \"...\"]}",
        "homepage": "Generate a proactive chat opener for a new visitor to Limited Armor (premium iPhone cases). Mention 15-30% OFF sale. Return JSON: {\"message\": \"...\", \"chips\": [\"...\", \"...\", \"...\"]}",
    }

    prompt_text = prompts.get(page_type, prompts["homepage"])
    system = f"You are Armie, AI concierge for Limited Armor. {prompt_text}\nKeep message under 12 words. Chips max 4 words each. Return ONLY valid JSON."

    try:
        raw = call_ai(system, [{"role": "user", "content": "Generate proactive message"}])
        json_match = re.search(r'\{[\s\S]*\}', raw.strip())
        if json_match:
            data = json.loads(json_match.group())
            return {
                "message": data.get("message", "Hey! 15–30% OFF everything right now ⚡"),
                "chips": data.get("chips", ["Shop Cases", "See Sale", "Get Help"]),
            }
    except Exception:
        pass

    fallbacks = {
        "product": {"message": f"This one's on sale right now 🔥 Want to see more?", "chips": ["See more colors", "Check compatibility", "Add to cart"]},
        "cart": {"message": "You're almost there! Free shipping over $35 🚀", "chips": ["Complete order", "Add more", "Need help?"]},
        "homepage": {"message": "Hey! 15–30% OFF everything today ⚡", "chips": ["Shop iPhone Cases", "See Watch Bands", "What's popular?"]},
        "collection": {"message": "Need help finding the perfect case? 👀", "chips": ["Filter by phone", "See bestsellers", "Chat with me"]},
    }
    return fallbacks.get(page_type, fallbacks["homepage"])
