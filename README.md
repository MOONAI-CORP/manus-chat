# manus-chat 💬

> iMessage-inspired AI chat widget for Shopify stores — powered by Claude / GPT-4.1

Built by [MOONAI CORP](https://github.com/MOONAI-CORP) for Limited Armor and all brands.

---

## What It Is

A floating chat widget that looks and feels exactly like Apple iMessage (dark mode), with a real AI brain trained on your live Shopify product catalog. Replaces Rep AI with your own hosted solution.

**Features:**
- 🤖 AI agent powered by Claude claude-opus-4-5 (falls back to GPT-4.1-mini)
- 📱 iMessage-authentic UI — dark mode, blue sent bubbles, typing indicator, read receipts
- 🛍️ Swipeable product card carousel — real Shopify CDN images, sale prices, ratings
- ⚡ Proactive sales triggers — fires after 8s or exit intent, page-type aware
- 💬 Dynamic chips — update after every AI reply to guide the next step
- 📸 Agent profile photo + brand logo upload (stored in localStorage)
- 🔄 Live Shopify product sync — 250 products from `iznqza-yx.myshopify.com`
- 📦 Zero external dependencies — pure vanilla JS/CSS, no frameworks

---

## Files

| File | Purpose |
|---|---|
| `chat-widget-v2.html` | Full widget — demo page + Shopify embed snippet |
| `api.py` | FastAPI AI backend — Limited Armor brand brain, product search, proactive endpoint |
| `store_data.json` | 250 live products synced from Shopify |
| `shopify_sync.py` | Re-sync script — run anytime to refresh catalog |

---

## Quick Start

### 1. Deploy the Backend

```bash
pip install fastapi uvicorn anthropic openai
ANTHROPIC_API_KEY=sk-ant-... uvicorn api:app --host 0.0.0.0 --port 8001
```

Recommended hosts: **Railway**, **Render** (free tier), or your own VPS.

### 2. Update the Widget Config

In `chat-widget-v2.html`, find the `IMSG` config block and set:

```js
var IMSG = {
  agentName:   'Armie',
  brandName:   'LIMITED ARMOR',
  brandColor:  '#ff9f0a',
  apiUrl:      'https://YOUR-DEPLOYED-BACKEND-URL'
};
```

### 3. Install in Shopify

1. Shopify Admin → **Online Store → Themes → Edit code → `theme.liquid`**
2. Paste everything from `<style>` to `</script>` just before `</body>`
3. Save — widget appears on every page immediately

### 4. Keep Catalog Fresh

```bash
python3 shopify_sync.py   # re-pulls all 250 products
# then restart the backend
```

---

## AI Brain

The agent (`Armie`) is trained on:
- Full product catalog with real prices and images
- Conversation flow: Open → Discover → Recommend → Handle objections → Close → Upsell
- Upsell chains: iPhone case → Watch band → MagSafe wallet → Keychain
- Escalation triggers → routes to `support@limitedarmor.com`

To use Claude: set `ANTHROPIC_API_KEY`  
To use GPT-4.1-mini: set `OPENAI_API_KEY` (auto-fallback)

---

## Adapting for Other Brands

1. Run `shopify_sync.py` with the new store credentials
2. Update `SYSTEM_PROMPT` in `api.py` with the new brand voice + products
3. Update the `IMSG` config block in the widget (name, color, greeting)
4. Deploy

---

## License

MIT — built by MOONAI CORP
