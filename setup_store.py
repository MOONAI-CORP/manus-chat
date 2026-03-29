#!/usr/bin/env python3
"""
MOONAI Chat Widget — Store Setup & Sync Script
Run this once per store to:
  1. Pull all products, collections, and policies from Shopify
  2. Generate store_data.json (the AI catalog)
  3. Generate a .env file ready to paste into Vercel
  4. Generate the Shopify theme.liquid embed snippet

Usage:
  python3 setup_store.py

You will be prompted for:
  - Shopify store domain (e.g. mystore.myshopify.com)
  - Shopify Admin API access token (shpat_...)
  - Store display name, agent name, support email, etc.
"""

import requests, json, os, sys, re

# ─── PROMPTS ──────────────────────────────────────────────────────────────────
def ask(prompt, default=""):
    val = input(f"{prompt} [{default}]: ").strip() if default else input(f"{prompt}: ").strip()
    return val if val else default

print("\n" + "═"*60)
print("  MOONAI Chat Widget — Store Setup")
print("═"*60 + "\n")

SHOP_DOMAIN    = ask("Shopify store domain (e.g. iznqza-yx.myshopify.com)")
ACCESS_TOKEN   = ask("Shopify Admin API access token (shpat_...)")
STORE_NAME     = ask("Store display name (e.g. Limited Armor)")
STORE_URL      = ask("Public store URL (e.g. https://limitedarmor.com)")
AGENT_NAME     = ask("AI agent name (e.g. Armie)", "Aria")
AGENT_INITIALS = ask("Agent initials for avatar fallback (e.g. LA)", "AI")
SUPPORT_EMAIL  = ask("Support email", f"support@{STORE_URL.replace('https://','').replace('http://','').split('/')[0]}")
PRODUCT_CAT    = ask("Product category (e.g. iPhone cases, bedding, bags)", "products")
BRAND_VIBE     = ask("Brand personality (e.g. luxury boutique, friendly, bold)", "helpful, friendly, and knowledgeable")
BRAND_COLOR    = ask("Brand color hex (e.g. #ff9f0a)", "#007aff")
ACCENT_COLOR   = ask("Accent color hex (gradient end)", "#0a84ff")
CURRENT_SALE   = ask("Current sale/promo (leave blank if none)", "")
SHIPPING_POLICY = ask("Shipping policy", "FREE shipping on all orders — no minimum required.")
RETURN_POLICY  = ask("Return policy", "30-day hassle-free returns. Contact us with your order number.")
DELIVERY_TIME  = ask("Delivery time", "3–7 business days domestic. Ships within 1–3 business days.")
VERCEL_URL     = ask("Your Vercel deployment URL (e.g. https://my-chat.vercel.app)", "https://your-deployment.vercel.app")

HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}
BASE = f"https://{SHOP_DOMAIN}/admin/api/2024-01"

# ─── PULL PRODUCTS ────────────────────────────────────────────────────────────
print("\n📦 Pulling products from Shopify...")
all_products = []
url = f"{BASE}/products.json?limit=250&fields=id,title,handle,product_type,tags,variants,images,status"
while url:
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code != 200:
        print(f"  ❌ Error {resp.status_code}: {resp.text[:200]}")
        sys.exit(1)
    data = resp.json()
    batch = data.get("products", [])
    all_products.extend(batch)
    print(f"  ✓ {len(all_products)} products fetched...")
    # Pagination via Link header
    link = resp.headers.get("Link", "")
    next_url = None
    for part in link.split(","):
        if 'rel="next"' in part:
            match = re.search(r'<([^>]+)>', part)
            if match:
                next_url = match.group(1)
    url = next_url

print(f"  ✅ {len(all_products)} total products pulled")

# ─── BUILD CATALOG ────────────────────────────────────────────────────────────
catalog = []
for p in all_products:
    if p.get("status", "active") != "active":
        continue
    variants = p.get("variants", [])
    prices = [float(v["price"]) for v in variants if v.get("price")]
    compare_prices = [float(v["compare_at_price"]) for v in variants if v.get("compare_at_price")]
    price_min = min(prices) if prices else 0.0
    compare_price = max(compare_prices) if compare_prices else 0.0
    image = ""
    if p.get("images"):
        image = p["images"][0].get("src", "")
    options = {}
    for v in variants[:20]:
        opt1 = v.get("option1")
        if opt1 and opt1 != "Default Title":
            options.setdefault("Model", [])
            if opt1 not in options["Model"]:
                options["Model"].append(opt1)
    tags = p.get("tags", "")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    catalog.append({
        "id": p["id"],
        "title": p["title"],
        "handle": p["handle"],
        "product_type": p.get("product_type", ""),
        "tags": tags,
        "price_min": price_min,
        "compare_price": compare_price,
        "image": image,
        "url": f"{STORE_URL}/products/{p['handle']}",
        "available": any(v.get("available", True) for v in variants),
        "variant_count": len(variants),
        "options": options,
    })

store_data = {
    "store_name": STORE_NAME,
    "store_url": STORE_URL,
    "catalog": catalog,
}

with open("store_data.json", "w") as f:
    json.dump(store_data, f, indent=2)
print(f"\n✅ store_data.json written — {len(catalog)} active products")

# ─── GENERATE .env FILE ───────────────────────────────────────────────────────
env_content = f"""# MOONAI Chat Widget — Vercel Environment Variables
# Paste these into: Vercel Dashboard > Your Project > Settings > Environment Variables

STORE_NAME={STORE_NAME}
STORE_URL={STORE_URL}
AGENT_NAME={AGENT_NAME}
SUPPORT_EMAIL={SUPPORT_EMAIL}
PRODUCT_CATEGORY={PRODUCT_CAT}
BRAND_VIBE={BRAND_VIBE}
SHIPPING_POLICY={SHIPPING_POLICY}
RETURN_POLICY={RETURN_POLICY}
DELIVERY_TIME={DELIVERY_TIME}
CURRENT_SALE={CURRENT_SALE}

# AI Keys — add at least one
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
"""

with open(".env.example", "w") as f:
    f.write(env_content)
print("✅ .env.example written — paste these into Vercel env vars")

# ─── GENERATE THEME EDITOR DEFAULTS ──────────────────────────────────────────
theme_defaults = {
    "brand_name": STORE_NAME,
    "agent_name": AGENT_NAME,
    "agent_initials": AGENT_INITIALS,
    "brand_color": BRAND_COLOR,
    "accent_color": ACCENT_COLOR,
    "api_url": VERCEL_URL,
    "greeting": f"Hey! 👋 Welcome to {STORE_NAME}! {f'We have {CURRENT_SALE} right now — ' if CURRENT_SALE else ''}How can I help you today?",
    "proactive_delay": 8,
}

with open("theme_defaults.json", "w") as f:
    json.dump(theme_defaults, f, indent=2)
print("✅ theme_defaults.json written — use these as defaults in Shopify Theme Editor")

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
print("\n" + "═"*60)
print("  Setup Complete!")
print("═"*60)
print(f"""
Next steps:
  1. Deploy backend to Vercel:
     - Push this repo to GitHub
     - Import to Vercel at vercel.com/new
     - Add env vars from .env.example
     - Set ANTHROPIC_API_KEY=sk-ant-...

  2. Install widget in Shopify:
     - Go to Shopify Admin > Online Store > Themes > Customize
     - Add the "MOONAI Chat Widget" block to your theme
     - Set the API URL to: {VERCEL_URL}
     - Upload your agent photo and brand logo
     - Set brand color to: {BRAND_COLOR}

  3. Test the widget:
     - Open your store and wait {8}s for the proactive bubble
     - Click to open and chat with {AGENT_NAME}

  Store: {STORE_URL}
  Products: {len(catalog)} active products loaded
""")
