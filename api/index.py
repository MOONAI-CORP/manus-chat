"""
MOONAI Chat Widget — Deterministic Orchestration Backend v5
Architecture: 4-layer separation per spec
  Layer 1: API / request routing
  Layer 2: Conversation state machine (phase engine — backend owns ALL transitions)
  Layer 3: Product service + knowledge config (deterministic — never LLM)
  Layer 4: LLM copy service (phrasing ONLY — strict schema, low temperature)

The LLM NEVER:
  - chooses phase transitions
  - invents products, prices, or images
  - overrides store facts (shipping, returns, sale)
  - produces arbitrary next steps

The backend ALWAYS:
  - owns phase transitions via state machine
  - selects real products from catalog via keyword scoring
  - reads facts from KNOWLEDGE config
  - validates response schema before returning to frontend
"""

import os, json, re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 3A: KNOWLEDGE CONFIG
# Store facts are NEVER read from LLM memory — always from this config.
# ─────────────────────────────────────────────────────────────────────────────

STORE_KNOWLEDGE: Dict[str, Dict] = {
    "limited_armor": {
        "name": "Limited Armor",
        "url": "https://limitedarmor.com",
        "agent_name": "Armie",
        "agent_initials": "LA",
        "brand_color": "#c9a84c",
        "product_noun": "case",
        "product_category": "designer iPhone cases",
        "tone": "luxury boutique, exclusive, premium — like a personal stylist who knows their stuff",
        "support_email": "support@limitedarmor.com",
        "shipping_copy": "FREE shipping on every single order — no minimum, no catch",
        "delivery_copy": "Ships within 1-2 business days. Arrives in 3-7 business days.",
        "returns_copy": "30-day hassle-free returns. Email support@limitedarmor.com with your order number.",
        "sale_active": True,
        "sale_copy": "15-30% OFF everything right now",
        "sale_urgency": "Sale ends soon — don't miss it",
        "escalation_copy": "Let me connect you with our support team right away. Email support@limitedarmor.com and they will take care of you personally.",
        "catalog_file": "store_data.json",
        "qualify_question": "What iPhone model do you have? I'll find you the perfect case.",
        "objection_price": "Totally get it — let me show you some great options at a lower price point that still look premium.",
        "objection_unsure": "No worries — let me simplify this. Based on what you told me, here are the top 2 picks.",
        "handoff_triggers": ["speak to human", "real person", "talk to agent", "manager", "this is ridiculous", "terrible", "scam", "fraud"],
    },
    "cozy_cloud": {
        "name": "Cozy Cloud Co",
        "url": "https://cozycloudco.com",
        "agent_name": "Cloudy",
        "agent_initials": "CC",
        "brand_color": "#8b5cf6",
        "product_noun": "bedding",
        "product_category": "luxury bedding and home textiles",
        "tone": "warm, cozy, inviting — like a best friend who knows bedding",
        "support_email": "support@cozycloudco.com",
        "shipping_copy": "FREE shipping on every order",
        "delivery_copy": "Ships within 1-2 business days. Arrives in 5-8 business days.",
        "returns_copy": "30-day returns. Email support@cozycloudco.com with your order number.",
        "sale_active": True,
        "sale_copy": "Up to 30% OFF sitewide",
        "sale_urgency": "Limited stock — these sell out fast",
        "escalation_copy": "Let me get our support team on this for you. Email support@cozycloudco.com.",
        "catalog_file": "store_data_cozy_cloud.json",
        "qualify_question": "Are you shopping for yourself or as a gift? And what size bed do you have?",
        "objection_price": "I hear you — let me show you some equally cozy options at a better price point.",
        "objection_unsure": "No pressure! Here are the top 2 picks based on what you are looking for.",
        "handoff_triggers": ["speak to human", "real person", "agent", "manager", "refund", "terrible"],
    },
    "carbon_conceptz": {
        "name": "Carbon Conceptz",
        "url": "https://carbonconceptz.com",
        "agent_name": "Carbon",
        "agent_initials": "CC",
        "brand_color": "#007aff",
        "product_noun": "accessory",
        "product_category": "carbon fiber phone cases and automotive accessories",
        "tone": "performance-focused, technical, enthusiast — like a car guy who knows gear",
        "support_email": "support@carbonconceptz.com",
        "shipping_copy": "FREE shipping on all orders",
        "delivery_copy": "Ships within 1-2 business days. Arrives in 3-7 business days.",
        "returns_copy": "30-day returns. Email support@carbonconceptz.com with your order number.",
        "sale_active": True,
        "sale_copy": "Up to 25% OFF",
        "sale_urgency": "Limited stock on top sellers",
        "escalation_copy": "Let me get our support team on this. Email support@carbonconceptz.com.",
        "catalog_file": "store_data_carbon_conceptz.json",
        "qualify_question": "What phone or car do you have? I will find the perfect fit.",
        "objection_price": "Let me show you some equally premium options at a better price.",
        "objection_unsure": "No worries — here are the top picks based on your setup.",
        "handoff_triggers": ["speak to human", "real person", "agent", "manager"],
    },
    "bagify": {
        "name": "Bagify",
        "url": "https://bagify.com",
        "agent_name": "Bay",
        "agent_initials": "BG",
        "brand_color": "#ff375f",
        "product_noun": "bag",
        "product_category": "premium crossbody bags",
        "tone": "stylish, confident, fashion-forward — like a personal stylist",
        "support_email": "support@bagify.com",
        "shipping_copy": "FREE shipping on every order",
        "delivery_copy": "Ships within 1-2 business days. Arrives in 5-8 business days.",
        "returns_copy": "30-day returns. Email support@bagify.com with your order number.",
        "sale_active": True,
        "sale_copy": "Launch sale — up to 20% OFF",
        "sale_urgency": "Launch pricing will not last long",
        "escalation_copy": "Let me get our support team on this. Email support@bagify.com.",
        "catalog_file": "store_data_bagify.json",
        "qualify_question": "What style are you going for — casual, work, or going out?",
        "objection_price": "Let me show you some equally stylish options at a better price.",
        "objection_unsure": "No worries — here are the top picks based on your style.",
        "handoff_triggers": ["speak to human", "real person", "agent", "manager"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 3B: PRODUCT SERVICE
# All product selection is deterministic. LLM never picks products.
# ─────────────────────────────────────────────────────────────────────────────

_CATALOG_CACHE: Dict[str, List[Dict]] = {}


def load_catalog(store_id: str) -> List[Dict]:
    if store_id in _CATALOG_CACHE:
        return _CATALOG_CACHE[store_id]
    k = STORE_KNOWLEDGE.get(store_id, STORE_KNOWLEDGE["limited_armor"])
    fname = k["catalog_file"]
    base = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(base)
    for search_dir in [parent, base, "/var/task"]:
        fpath = os.path.join(search_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath) as f:
                    raw = json.load(f)
                # Support both formats: list of products OR {"catalog": [...]}
                if isinstance(raw, list):
                    products = raw
                elif isinstance(raw, dict):
                    products = raw.get("catalog", raw.get("products", []))
                else:
                    products = []
                _CATALOG_CACHE[store_id] = products
                print(f"Loaded {len(products)} products for {store_id} from {fpath}")
                return products
            except Exception as e:
                print(f"Error loading {fpath}: {e}")
    _CATALOG_CACHE[store_id] = []
    return []


def normalize_product(p: Dict, store_id: str) -> Dict:
    """Normalize any catalog format into canonical product schema."""
    k = STORE_KNOWLEDGE.get(store_id, STORE_KNOWLEDGE["limited_armor"])
    store_url = k["url"]

    if "price_min" in p:
        # Pre-processed catalog format (shopify_sync.py output)
        price_raw = float(p.get("price_min", 0) or 0)
        compare_raw = float(p.get("compare_price", 0) or 0)
        image = p.get("image", "")
        handle = p.get("handle", "")
        url = p.get("url", f"{store_url}/products/{handle}")
        title = p.get("title", "")

        # Tags: list or stringified list
        raw_tags = p.get("tags", [])
        if isinstance(raw_tags, list):
            tags = [str(t) for t in raw_tags]
        elif isinstance(raw_tags, str) and raw_tags.startswith('['):
            try:
                import ast
                tags = [str(t) for t in ast.literal_eval(raw_tags)]
            except Exception:
                tags = [t.strip().strip("'\"") for t in raw_tags.strip('[]').split(',')]
        elif isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(',') if t.strip()]
        else:
            tags = []

        # Options dict: {'Model': ['iPhone 16 Pro Max', ...]} — add all values as searchable tags
        options = p.get("options", {})
        if isinstance(options, dict):
            for opt_vals in options.values():
                if isinstance(opt_vals, list):
                    tags.extend([str(v) for v in opt_vals])
        elif isinstance(options, str):
            # Stringified dict — extract iPhone model names
            model_matches = re.findall(r'iPhone\s+\d+[\w\s]*', options)
            tags.extend(model_matches)

    else:
        # Raw Shopify API format
        variants = p.get("variants", [])
        price_raw = float(variants[0].get("price", 0)) if variants else 0.0
        compare_raw = float(variants[0].get("compare_at_price") or 0) if variants else 0.0
        images = p.get("images", [])
        image = images[0].get("src", "") if images else ""
        handle = p.get("handle", "")
        url = f"{store_url}/products/{handle}" if handle else store_url
        title = p.get("title", "")
        raw_tags = p.get("tags", [])
        tags = raw_tags if isinstance(raw_tags, list) else [t.strip() for t in str(raw_tags).split(',')]

    tags_lower = [str(t).lower().strip() for t in tags if t]

    # Badge
    badge = ""
    if compare_raw and compare_raw > price_raw:
        pct = int((compare_raw - price_raw) / compare_raw * 100)
        badge = f"{pct}% OFF"
    if any(t in tags_lower for t in ["best-seller", "bestseller", "best seller"]):
        badge = "Best Seller"
    elif any(t in tags_lower for t in ["new", "new-arrival", "new arrival"]):
        badge = badge or "New Arrival"

    return {
        "id": str(p.get("id", "")),
        "title": title,
        "price": f"${price_raw:.2f}",
        "price_raw": price_raw,
        "compareAtPrice": f"${compare_raw:.2f}" if compare_raw and compare_raw > price_raw else None,
        "image": image,
        "url": url,
        "badge": badge,
        "tags": tags_lower,
        "handle": handle,
    }


def score_product(p: Dict, phone_model: str = "", query: str = "", category: str = "") -> int:
    """Deterministic relevance scoring. Higher = more relevant."""
    score = 0
    title_lower = p["title"].lower()
    tags = p["tags"]

    phone_lower = phone_model.lower().strip() if phone_model else ""
    model_clean = re.sub(r'iphone\s*', '', phone_lower).strip()

    if phone_lower:
        if model_clean and model_clean in title_lower:
            score += 100
        elif phone_lower in title_lower:
            score += 80
        elif model_clean and any(model_clean in t for t in tags):
            score += 60
        elif any(phone_lower in t for t in tags):
            score += 50

    if query:
        query_lower = query.lower()
        if query_lower in title_lower:
            score += 30
        elif any(query_lower in t for t in tags):
            score += 20

    if category:
        cat_lower = category.lower()
        if cat_lower in title_lower:
            score += 15
        elif any(cat_lower in t for t in tags):
            score += 10

    if any(t in tags for t in ["best-seller", "bestseller"]):
        score += 8

    return score


def search_products(store_id: str, phone_model: str = "", query: str = "",
                    max_price: float = 0, category: str = "",
                    magsafe_only: bool = False, limit: int = 3) -> List[Dict]:
    """Deterministic product search. Returns real catalog products only."""
    raw = load_catalog(store_id)
    if not raw:
        return []

    products = [normalize_product(p, store_id) for p in raw]
    results = []

    for p in products:
        if magsafe_only and "magsafe" not in p["title"].lower() and not any("magsafe" in t for t in p["tags"]):
            continue
        if max_price > 0 and p["price_raw"] > max_price:
            continue
        s = score_product(p, phone_model, query, category)
        if s > 0 or (not phone_model and not query):
            results.append((s, p))

    results.sort(key=lambda x: (-x[0], x[1]["price_raw"]))
    return [p for _, p in results[:limit]]


def get_cheaper_alternatives(store_id: str, max_price: float, phone_model: str, limit: int = 3) -> List[Dict]:
    return search_products(store_id, phone_model=phone_model, max_price=max_price, limit=limit)


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2: CONVERSATION STATE MACHINE
# Backend owns ALL phase transitions. LLM never decides next phase.
# ─────────────────────────────────────────────────────────────────────────────

PHASE_CHIPS: Dict[str, List[Dict]] = {
    "open": [
        {"id": "shop_now", "label": "Shop now"},
        {"id": "see_sale", "label": "See sale"},
        {"id": "need_help", "label": "Help me choose"},
    ],
    "qualify": [
        {"id": "iphone_16_pro_max", "label": "iPhone 16 Pro Max"},
        {"id": "iphone_16_pro", "label": "iPhone 16 Pro"},
        {"id": "iphone_15_pro", "label": "iPhone 15 Pro"},
        {"id": "other_model", "label": "Different model"},
    ],
    "recommend": [
        {"id": "tell_me_more", "label": "Tell me more"},
        {"id": "cheaper_options", "label": "Cheaper options"},
        {"id": "free_shipping", "label": "Free shipping?"},
        {"id": "i_want_this", "label": "I want this"},
    ],
    "objection": [
        {"id": "show_best_value", "label": "Show best value"},
        {"id": "see_all", "label": "See all options"},
        {"id": "free_shipping", "label": "Shipping info"},
    ],
    "close": [
        {"id": "complete_order", "label": "Complete order"},
        {"id": "see_more", "label": "Show me more"},
        {"id": "free_shipping", "label": "Shipping info"},
    ],
    "upsell": [
        {"id": "add_it", "label": "Add it"},
        {"id": "no_thanks", "label": "No thanks"},
        {"id": "complete_order", "label": "Complete order"},
    ],
    "support": [
        {"id": "track_order", "label": "Track my order"},
        {"id": "start_return", "label": "Start a return"},
        {"id": "contact_support", "label": "Contact support"},
    ],
    "handoff": [
        {"id": "email_support", "label": "Email support"},
        {"id": "continue_shopping", "label": "Keep shopping"},
    ],
}

CHIP_INTENT_MAP: Dict[str, str] = {
    "shop_now": "recommendation_request",
    "see_sale": "recommendation_request",
    "need_help": "recommendation_request",
    "iphone_16_pro_max": "qualify",
    "iphone_16_pro": "qualify",
    "iphone_15_pro": "qualify",
    "iphone_15_pro_max": "qualify",
    "iphone_14_pro": "qualify",
    "iphone_14": "qualify",
    "other_model": "qualify",
    "tell_me_more": "recommendation_request",
    "cheaper_options": "objection_price",
    "free_shipping": "shipping_question",
    "i_want_this": "add_to_cart",
    "show_best_value": "objection_price",
    "see_all": "recommendation_request",
    "complete_order": "add_to_cart",
    "see_more": "recommendation_request",
    "add_it": "accessory_interest",
    "no_thanks": "decline",
    "track_order": "order_help",
    "start_return": "returns_question",
    "contact_support": "order_help",
    "email_support": "order_help",
    "continue_shopping": "recommendation_request",
}

CHIP_PHONE_MAP: Dict[str, str] = {
    "iphone_16_pro_max": "iPhone 16 Pro Max",
    "iphone_16_pro": "iPhone 16 Pro",
    "iphone_15_pro": "iPhone 15 Pro",
    "iphone_15_pro_max": "iPhone 15 Pro Max",
    "iphone_15": "iPhone 15",
    "iphone_14_pro": "iPhone 14 Pro",
    "iphone_14": "iPhone 14",
}


def classify_intent(message: str, current_phase: str) -> str:
    """Deterministic intent classifier using keyword rules."""
    msg = message.lower().strip()

    # Chip ID direct mapping
    if msg in CHIP_INTENT_MAP:
        return CHIP_INTENT_MAP[msg]

    # Handoff
    handoff_words = ["speak to human", "real person", "talk to agent", "talk to someone",
                     "manager", "this is ridiculous", "terrible service", "scam", "fraud",
                     "i want a refund now", "i need help now", "this is unacceptable"]
    if any(w in msg for w in handoff_words):
        return "human_help"

    # Support
    if any(w in msg for w in ["track", "where is my order", "order status", "tracking"]):
        return "order_help"
    if any(w in msg for w in ["return", "refund", "exchange", "send back", "send it back"]):
        return "returns_question"
    if any(w in msg for w in ["shipping", "delivery", "how long", "when will", "free ship", "ship"]):
        return "shipping_question"

    # Objections
    if any(w in msg for w in ["too expensive", "too much", "cheaper", "lower price", "budget", "cant afford", "price"]):
        return "objection_price"
    if any(w in msg for w in ["not sure", "unsure", "don't know", "maybe", "thinking", "hesitant", "idk"]):
        return "objection_unsure"

    # Purchase intent
    if any(w in msg for w in ["add to cart", "buy", "purchase", "checkout", "i want this", "i'll take", "order this"]):
        return "add_to_cart"

    # Accessory
    if any(w in msg for w in ["watch band", "magsafe", "wallet", "screen protector", "accessory", "accessories"]):
        return "accessory_interest"

    # Recommendation
    if any(w in msg for w in ["show me", "recommend", "suggest", "what do you have", "best case",
                               "which case", "what case", "help me choose", "find me", "looking for"]):
        return "recommendation_request"

    # Phone model
    if re.search(r'iphone\s*\d', msg, re.IGNORECASE):
        return "qualify"

    # Greeting
    if any(w in msg for w in ["hi", "hello", "hey", "what's up", "sup", "yo", "good morning", "good evening", "hiya"]):
        return "greeting"

    return "off_topic"


def extract_attributes(message: str, existing: Dict) -> Dict:
    """Extract structured facts from message. Deterministic."""
    attrs = dict(existing)
    msg = message.lower()

    # Phone model from chip
    if message.strip() in CHIP_PHONE_MAP:
        attrs["phoneModel"] = CHIP_PHONE_MAP[message.strip()]

    # Phone model from text
    m = re.search(r'iphone\s*(\d{1,2}\s*(?:pro\s*max|pro|plus)?)', message, re.IGNORECASE)
    if m:
        attrs["phoneModel"] = "iPhone " + m.group(1).strip().title()

    # Price sensitivity
    if any(w in msg for w in ["cheap", "budget", "affordable", "too expensive", "cheaper", "lower price"]):
        attrs["priceSensitivity"] = "high"
    elif any(w in msg for w in ["premium", "best", "luxury", "high end", "top of the line"]):
        attrs["priceSensitivity"] = "low"

    # MagSafe
    if "magsafe" in msg:
        attrs["magsafeInterest"] = True

    # Watch band
    if "watch band" in msg or "apple watch" in msg:
        attrs["watchBandInterest"] = True

    # Frustration
    if any(w in msg for w in ["terrible", "awful", "ridiculous", "scam", "fraud", "angry", "frustrated"]):
        attrs["frustrationLevel"] = attrs.get("frustrationLevel", 0) + 1

    # Upsell shown flag
    if message.strip() in ["add_it", "no_thanks"]:
        attrs["upsellResponded"] = True

    return attrs


def next_phase(current: str, intent: str, attrs: Dict) -> str:
    """
    State machine transition table.
    Backend owns this entirely. LLM never calls this.
    """
    frustration = attrs.get("frustrationLevel", 0)
    has_phone = bool(attrs.get("phoneModel"))

    # Handoff always wins
    if intent == "human_help" or frustration >= 2:
        return "handoff"

    # Support intents
    if intent in ["shipping_question", "returns_question", "order_help"]:
        return "support"

    # Accessory → upsell
    if intent == "accessory_interest":
        return "upsell"

    # Add to cart → close
    if intent == "add_to_cart":
        return "close"

    # Objections
    if intent in ["objection_price", "objection_unsure"]:
        return "objection"

    # Recommendation request
    if intent == "recommendation_request":
        return "recommend" if has_phone else "qualify"

    # Qualify: got phone → recommend
    if intent == "qualify" and has_phone:
        return "recommend"
    if intent == "qualify":
        return "qualify"

    # Greeting
    if intent == "greeting":
        return "open"

    # Decline upsell
    if intent == "decline":
        return "close"

    # Stay in current phase
    return current if current in PHASE_CHIPS else "open"


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 4: LLM COPY SERVICE
# LLM writes short copy ONLY. All data is pre-determined by layers 2 & 3.
# ─────────────────────────────────────────────────────────────────────────────

def get_llm_client():
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            import anthropic
            return "anthropic", anthropic.Anthropic()
        except ImportError:
            pass
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            return "openai", OpenAI()
        except ImportError:
            pass
    return None, None


def llm_write_copy(store_id: str, phase: str, intent: str, attrs: Dict,
                   products: List[Dict], user_message: str) -> str:
    """
    LLM writes ONE short message (1-3 sentences).
    Receives: phase goal, known facts, pre-selected products.
    Returns: plain text string only.
    """
    k = STORE_KNOWLEDGE.get(store_id, STORE_KNOWLEDGE["limited_armor"])
    engine, client = get_llm_client()

    if not client:
        return get_deterministic_copy(store_id, phase, intent, attrs, products)

    phone = attrs.get("phoneModel", "")
    price_sens = attrs.get("priceSensitivity", "unknown")
    agent = k["agent_name"]
    tone = k["tone"]
    sale = k["sale_copy"]
    shipping = k["shipping_copy"]
    returns = k["returns_copy"]
    escalation = k["escalation_copy"]
    qualify_q = k["qualify_question"]
    obj_price = k["objection_price"]
    obj_unsure = k["objection_unsure"]

    # Product context — pre-selected by backend
    prod_ctx = ""
    if products:
        prod_ctx = "Products already selected by backend (reference these, do not invent others):\n"
        for p in products:
            prod_ctx += f"- {p['title']} at {p['price']}"
            if p.get("badge"):
                prod_ctx += f" [{p['badge']}]"
            prod_ctx += "\n"

    # Phase-specific goal
    phase_goals = {
        "open": f"Greet warmly. Mention '{sale}'. Ask: '{qualify_q}' (one question only).",
        "qualify": f"Phone model is {'known: ' + phone if phone else 'unknown'}. {'Confirm and say you will find the perfect case.' if phone else 'Ask: ' + qualify_q}",
        "recommend": f"Briefly explain why these products are perfect for {phone or 'them'}. Be specific. Mention '{sale}'. No bullet points.",
        "objection": f"{'Use this response: ' + obj_price if intent == 'objection_price' else 'Use this response: ' + obj_unsure} Then reference the cheaper products shown.",
        "close": f"Create urgency with '{sale}'. Give a direct CTA. One sentence.",
        "upsell": f"Suggest one complementary accessory. Keep it to one sentence. Reference the product shown.",
        "support": f"{'Answer: ' + shipping if intent == 'shipping_question' else 'Answer: ' + returns if intent == 'returns_question' else 'Help with their order question.'} Be direct.",
        "handoff": f"Use exactly: '{escalation}'",
    }

    system = f"""You are {agent}, a sales assistant for {k['name']}.
Tone: {tone}
Write ONE message (1-3 sentences MAX). Plain text only. No JSON. No markdown. No quotes around your response.
NEVER say: "Great question", "I understand", "As an AI", "I think", "I believe", "maybe", "probably".
NEVER invent products, prices, policies, or images.
NEVER ask more than one question.
NEVER use bullet points or line breaks."""

    user_prompt = f"""Phase: {phase}
Intent: {intent}
Customer said: "{user_message}"
Phone model: {phone or 'unknown'}
Price sensitivity: {price_sens}
{prod_ctx}
Store facts (use EXACTLY as written, do not paraphrase):
- Shipping: {shipping}
- Returns: {returns}
- Sale: {sale}
- Escalation path: {escalation}

Goal for this message: {phase_goals.get(phase, 'Be helpful and move toward a purchase.')}

Write the message now:"""

    try:
        if engine == "anthropic":
            resp = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=100,
                temperature=0.35,
                system=system,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return resp.content[0].text.strip()
        else:
            resp = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=100,
                temperature=0.35,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM error: {e}")
        return get_deterministic_copy(store_id, phase, intent, attrs, products)


def get_deterministic_copy(store_id: str, phase: str, intent: str, attrs: Dict, products: List[Dict]) -> str:
    """100% deterministic fallback copy. No LLM required."""
    k = STORE_KNOWLEDGE.get(store_id, STORE_KNOWLEDGE["limited_armor"])
    phone = attrs.get("phoneModel", "")
    agent = k["agent_name"]
    sale = k["sale_copy"]
    shipping = k["shipping_copy"]
    returns = k["returns_copy"]
    escalation = k["escalation_copy"]
    qualify_q = k["qualify_question"]

    copies = {
        "open": f"Hey! Welcome to {k['name']} — {sale} right now. {qualify_q}",
        "qualify": f"{qualify_q}",
        "recommend": f"Here are my top picks{' for your ' + phone if phone else ''} — all {sale}. Tap any to shop.",
        "objection": k["objection_price"] if intent == "objection_price" else k["objection_unsure"],
        "close": f"Great choice! {sale} — grab it before the sale ends.",
        "upsell": f"Customers who bought this also loved our accessories. Want to add one?",
        "support": shipping if intent == "shipping_question" else returns if intent == "returns_question" else "I can help with that! What do you need?",
        "handoff": escalation,
    }
    return copies.get(phase, f"How can I help you today?")


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1: API ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    store_id: str = "limited_armor"
    message: str
    current_phase: Optional[str] = "open"
    known_attributes: Optional[Dict] = {}
    page_type: Optional[str] = "homepage"
    page_title: Optional[str] = ""
    upsell_shown: Optional[bool] = False
    # Legacy compat
    messages: Optional[List[Dict]] = []


class ProactiveRequest(BaseModel):
    store_id: str = "limited_armor"
    page_type: Optional[str] = "homepage"
    page_title: Optional[str] = ""
    is_return_visitor: Optional[bool] = False
    cart_present: Optional[bool] = False


def build_product_cards(products: List[Dict]) -> List[Dict]:
    """Build product card payloads from pre-selected real catalog products."""
    cards = []
    for p in products:
        card = {
            "title": p["title"],
            "price": p["price"],
            "image": p["image"],
            "url": p["url"],
            "badge": p.get("badge", ""),
        }
        if p.get("compareAtPrice"):
            card["compareAtPrice"] = p["compareAtPrice"]
        cards.append(card)
    return cards


def build_response(phase: str, message: str, products: List[Dict],
                   attrs: Dict, store_id: str, cta: Dict = None) -> Dict:
    """Build and validate the strict response schema."""
    chips = PHASE_CHIPS.get(phase, PHASE_CHIPS["open"])
    product_cards = build_product_cards(products)

    resp = {
        "phase": phase,
        "message": message,
        "chips": chips,
        "productCards": product_cards,
        "knownAttributes": attrs,
    }
    if cta:
        resp["cta"] = cta

    # Schema validation — never return invalid response
    assert isinstance(resp["message"], str) and len(resp["message"]) > 0, "Empty message"
    assert isinstance(resp["chips"], list), "Invalid chips"
    assert isinstance(resp["productCards"], list), "Invalid product cards"

    return resp


@app.post("/chat")
async def chat(req: ChatRequest):
    store_id = req.store_id if req.store_id in STORE_KNOWLEDGE else "limited_armor"
    k = STORE_KNOWLEDGE[store_id]

    # Extract attributes (deterministic)
    attrs = extract_attributes(req.message, req.known_attributes or {})

    # Classify intent (deterministic)
    intent = classify_intent(req.message, req.current_phase or "open")

    # Determine next phase (state machine — deterministic)
    phase = next_phase(req.current_phase or "open", intent, attrs)

    # Select products (deterministic — real catalog only)
    products = []
    phone = attrs.get("phoneModel", "")
    high_price_sens = attrs.get("priceSensitivity") == "high"

    if phase == "recommend":
        products = search_products(store_id, phone_model=phone, limit=3)

    elif phase == "objection" and intent == "objection_price":
        # Show cheaper alternatives — max price $30 for high sensitivity
        max_p = 30.0 if high_price_sens else 35.0
        products = get_cheaper_alternatives(store_id, max_price=max_p, phone_model=phone, limit=3)
        if not products:
            products = search_products(store_id, phone_model=phone, limit=3)

    elif phase == "upsell" and not req.upsell_shown:
        # Upsell: watch bands or MagSafe wallets
        products = search_products(store_id, query="watch band", phone_model=phone, limit=1)
        if not products:
            products = search_products(store_id, query="magsafe wallet", limit=1)
        if not products:
            products = search_products(store_id, query="accessory", limit=2)

    # Build CTA for recommend phase
    cta = None
    if phase == "recommend" and phone:
        phone_slug = phone.lower().replace(" ", "-")
        cta = {
            "label": f"View all {phone} cases",
            "url": f"{k['url']}/collections/{phone_slug}-cases"
        }

    # LLM writes copy (phrasing only — all data already determined above)
    message_text = llm_write_copy(store_id, phase, intent, attrs, products, req.message)

    return build_response(phase, message_text, products, attrs, store_id, cta)


@app.post("/proactive")
async def proactive(req: ProactiveRequest):
    store_id = req.store_id if req.store_id in STORE_KNOWLEDGE else "limited_armor"
    k = STORE_KNOWLEDGE[store_id]
    agent = k["agent_name"]
    sale = k["sale_copy"]
    urgency = k["sale_urgency"]
    shipping = k["shipping_copy"]

    page_type = req.page_type or "homepage"
    page_title = req.page_title or ""
    is_return = req.is_return_visitor
    cart = req.cart_present

    # Deterministic proactive messages — no LLM needed
    if cart:
        message = f"Still thinking? Your cart is waiting — and {sale}. Need help deciding?"
        chips = [
            {"id": "complete_order", "label": "Complete order"},
            {"id": "free_shipping", "label": "Free shipping?"},
            {"id": "need_help", "label": "I have a question"},
        ]
    elif page_type == "product" and page_title:
        message = f"Love your taste! The {page_title} is one of our best — {sale}. Want help deciding?"
        chips = [
            {"id": "tell_me_more", "label": "Tell me more"},
            {"id": "cheaper_options", "label": "Cheaper options?"},
            {"id": "free_shipping", "label": "Free shipping?"},
        ]
    elif page_type == "collection":
        message = f"Finding something you love? I can help narrow it down — {sale} right now."
        chips = [
            {"id": "need_help", "label": "Help me choose"},
            {"id": "see_sale", "label": "What's on sale?"},
            {"id": "free_shipping", "label": "Free shipping?"},
        ]
    elif page_type == "cart":
        message = f"Don't leave your cart! {urgency}. {shipping}."
        chips = [
            {"id": "complete_order", "label": "Complete order"},
            {"id": "free_shipping", "label": "Shipping info"},
            {"id": "need_help", "label": "I have a question"},
        ]
    elif is_return:
        message = f"Welcome back! {urgency}. Want me to pick up where we left off?"
        chips = [
            {"id": "shop_now", "label": "Show me new arrivals"},
            {"id": "see_sale", "label": "What's on sale?"},
            {"id": "need_help", "label": "Help me choose"},
        ]
    else:
        message = f"Hey! {sale} — I'm {agent}, your personal stylist. What phone do you have?"
        chips = [
            {"id": "shop_now", "label": "Shop now"},
            {"id": "see_sale", "label": "See sale"},
            {"id": "need_help", "label": "Help me choose"},
        ]

    return {"message": message, "chips": chips, "phase": "open"}


@app.get("/health")
async def health():
    stores_status = {}
    for sid in STORE_KNOWLEDGE:
        catalog = load_catalog(sid)
        stores_status[sid] = {
            "name": STORE_KNOWLEDGE[sid]["name"],
            "agent": STORE_KNOWLEDGE[sid]["agent_name"],
            "products": len(catalog),
        }
    return {
        "status": "ok",
        "engine": "claude-opus-4-5" if os.environ.get("ANTHROPIC_API_KEY") else "gpt-4.1-mini",
        "stores": stores_status,
    }


@app.get("/config/{store_id}")
async def get_config(store_id: str):
    """Frontend fetches this to get brand config."""
    if store_id not in STORE_KNOWLEDGE:
        store_id = "limited_armor"
    k = STORE_KNOWLEDGE[store_id]
    return {
        "store_id": store_id,
        "name": k["name"],
        "agent_name": k["agent_name"],
        "agent_initials": k["agent_initials"],
        "brand_color": k["brand_color"],
        "greeting": f"Hey! Welcome to {k['name']} — {k['sale_copy']}. {k['qualify_question']}",
        "quick_replies": PHASE_CHIPS["open"],
    }
