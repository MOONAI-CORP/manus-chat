# iMessage Chat Widget — Shopify Installation Guide

## What You Get

A pixel-perfect **iMessage-inspired floating chat widget** built for your 4 Shopify stores. It features:

- Authentic iMessage dark UI with blue/green bubbles, typing indicators, and read receipts
- Floating launcher button with notification badge
- Quick-reply chips for common customer questions
- Featured product card auto-displayed in chat
- Smooth spring animations (open/close/message entrance)
- Fully mobile-responsive (full-screen on phones)
- Zero dependencies — pure HTML/CSS/JS, no external libraries

---

## Files Included

| File | Purpose |
|---|---|
| `chat-widget.html` | Full demo page — open in browser to preview |
| `shopify-embed.html` | The actual snippet to paste into Shopify |
| `INSTALL.md` | This installation guide |

---

## Quick Start — 5 Minutes to Live

### Step 1 — Preview the Widget

Open `chat-widget.html` in your browser to see the full demo with all 4 brand tabs.

### Step 2 — Customize for Your Store

Open `shopify-embed.html` and edit the `IMSG_CONFIG` block at the top of the `<script>` section:

```javascript
var IMSG_CONFIG = {
  agentName: "Carbon Conceptz",          // Your store/brand name
  agentAvatar: "CC",                     // 1-2 letter initials shown in avatar
  brandColor: "#007aff",                 // Primary color (iMessage blue default)
  accentColor: "#0a84ff",               // Slightly lighter shade for gradient
  greeting: "Hey! 👋 Welcome to Carbon Conceptz...",  // Opening message
  quickReplies: ["Track my order", "Return policy", "Product info", "Talk to a human"],
  featuredProduct: {
    name: "Carbon Fiber iPhone 16 Case",
    price: "$34.99",
    emoji: "📱",                         // Or use an image URL
    url: "/products/carbon-fiber-case"   // Shopify product handle URL
  }
};
```

### Step 3 — Install in Shopify

**Method A: Theme Editor (Recommended — No Code)**

1. Go to **Shopify Admin → Online Store → Themes**
2. Click **Customize** on your active theme
3. Click **Edit code** (or go to **Actions → Edit code**)
4. Open `layout/theme.liquid`
5. Find the closing `</body>` tag near the bottom
6. Paste the entire contents of `shopify-embed.html` **just before** `</body>`
7. Click **Save**

**Method B: Theme Settings (Dawn / Debut themes)**

1. Go to **Online Store → Themes → Customize**
2. Click **Theme settings → Custom CSS / Custom HTML**
3. Paste the snippet there

**Method C: App Blocks (OS 2.0 themes)**

1. Go to **Online Store → Themes → Customize**
2. Click **Add section → Custom Liquid**
3. Paste the snippet

---

## Per-Brand Configuration

Since you have 4 stores, use these configs for each:

### Carbon Conceptz
```javascript
agentName: "Carbon Conceptz",
agentAvatar: "CC",
brandColor: "#007aff",
accentColor: "#0a84ff",
greeting: "Hey! 👋 Welcome to Carbon Conceptz. Need help with carbon fiber cases or auto accessories?",
quickReplies: ["Track my order", "Carbon fiber cases", "Automotive accessories", "Return policy"],
```

### Cozy Cloud Co
```javascript
agentName: "Cozy Cloud Co",
agentAvatar: "CZ",
brandColor: "#5e5ce6",
accentColor: "#6e6cf6",
greeting: "Hi there! ☁️ Welcome to Cozy Cloud Co. Discover our monofloral bedding & luxury textiles.",
quickReplies: ["Track my order", "Monofloral bedding", "Bamboo collection", "Size guide"],
```

### Limited Armor
```javascript
agentName: "Limited Armor",
agentAvatar: "LA",
brandColor: "#ff9f0a",
accentColor: "#ffb340",
greeting: "Welcome to Limited Armor 🛡️ — premium designer iPhone cases. How can I help?",
quickReplies: ["Track my order", "Designer cases", "Limited drops", "Custom engraving"],
```

### Bagify
```javascript
agentName: "Bagify",
agentAvatar: "BG",
brandColor: "#ff375f",
accentColor: "#ff6b81",
greeting: "Hey! 👜 Welcome to Bagify — premium crossbody bags. We just launched! What can I help you with?",
quickReplies: ["New arrivals", "Track my order", "Bag materials", "Shipping info"],
```

---

## Connecting to a Real Chat Backend

The widget currently uses a smart auto-reply bot. To connect it to a real agent platform:

### Option A — Gorgias (Recommended for your setup)
Replace the `imsgBotReply` function with a Gorgias Chat SDK call. Gorgias integrates natively with Shopify and handles all 4 stores from one dashboard.

### Option B — Tidio
Swap the widget launcher to trigger Tidio's chat window instead. Use Tidio's JavaScript API:
```javascript
function imsgToggle() { tidioChatApi.open(); }
```

### Option C — Custom Webhook
Point replies to your own backend:
```javascript
fetch('/apps/chat', {
  method: 'POST',
  body: JSON.stringify({ message: text, shop: Shopify.shop })
}).then(r => r.json()).then(d => imsgAddMsg(d.reply, 'recv'));
```

---

## Customization Reference

| Property | What it controls |
|---|---|
| `brandColor` | Launcher button, send button, quick-reply borders |
| `accentColor` | Gradient highlight on launcher and avatar |
| `agentAvatar` | Initials shown in the header avatar circle |
| `greeting` | First message shown when chat opens |
| `quickReplies` | Array of chip buttons shown below messages |
| `featuredProduct.url` | Links to a Shopify product page |

---

## Performance Notes

- **No external requests** on page load — widget is fully inline
- **CSS is namespaced** with `imsg-` prefix to avoid conflicts with theme styles
- **JavaScript is namespaced** with `imsg` prefix — no global variable pollution
- Total weight: **~8KB** (unminified) — negligible impact on Core Web Vitals

---

*Built for Alpha's stores — Carbon Conceptz, Cozy Cloud Co, Limited Armor, Bagify*
