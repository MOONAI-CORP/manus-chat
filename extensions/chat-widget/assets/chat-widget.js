/* MOONAI Chat Widget JS — config driven by Shopify Theme Editor */

/* ══════════════════════════════════════════════════════════════════
   ⚙  CONFIG — Reads from Shopify Theme Editor block data attributes
      Set all values in: Shopify Admin > Themes > Customize > MOONAI Chat Widget
   ══════════════════════════════════════════════════════════════════ */
(function() {
  var root = document.getElementById('imsg-root');
  function get(k, def) { return (root && root.dataset[k]) ? root.dataset[k] : def; }

  window.IMSG = {
    agentName:       get('agentName',    'Support'),
    brandName:       get('brandName',    'MY STORE'),
    brandColor:      get('brandColor',   '#007aff'),
    accentColor:     get('accentColor',  '#0a84ff'),
    launcherBg:      get('launcherBg',   'gradient'),
    greeting:        get('greeting',     "Hey! \u{1F44B} Welcome! How can I help you today?"),
    agentPhoto:      get('agentPhoto',   ''),
    brandLogo:       get('brandLogo',    ''),
    quickReplies:    ['Browse Products \uD83D\uDECD\uFE0F', "What's on sale? \uD83D\uDD25", 'Track my order \uD83D\uDCE6', 'I need help choosing \u2728'],
    proactiveDelay:  parseInt(get('proactiveDelay', '8')) * 1000,
    proactiveEnabled: true,
    apiUrl:          get('apiUrl', 'https://imessage-chat-widget.vercel.app')
  };
})();
/* ══════════════════════════════════════════════════════════════════ */

var imsgIsOpen         = false;
var imsgMsgCount       = 0;
var imsgPendingImg     = null;
var imsgHistory        = [];
var imsgTypingLock     = false;
var imsgProactiveShown = false;
var imsgProactiveTimer = null;

var IMSG_API_URL       = IMSG.apiUrl + '/chat';
var IMSG_PROACTIVE_URL = IMSG.apiUrl + '/proactive';

/* ── INIT ─────────────────────────────────────────────────────────── */
// Run after DOM is fully ready so #imsg-msgs exists for session restore
var imsgSessionRestored = false;

function imsgInit() {
  applyBrandColor(IMSG.brandColor, IMSG.accentColor);
  document.getElementById('imsg-agent-name').textContent = IMSG.agentName;
  document.getElementById('imsg-avatar-initials').textContent = getInitials(IMSG.agentName);
  document.getElementById('imsg-brand-logo-text').textContent = IMSG.brandName;
  setQRs(IMSG.quickReplies);

  // Apply images from Shopify Theme Editor settings (data attributes on #imsg-root)
  if (IMSG.agentPhoto) applyAvatar(IMSG.agentPhoto);
  if (IMSG.brandLogo)  applyLogo(IMSG.brandLogo);

  // ── PERSISTENT CHAT: restore history from localStorage ──
  // DOM is ready here so innerHTML restore works correctly
  imsgSessionRestored = imsgRestoreSession();

  // ── REP AI PROACTIVE TRIGGERS ──
  if (IMSG.proactiveEnabled) {
    // Track visit count for repeat visitor detection
    var visitCount = parseInt(localStorage.getItem('imsg_visits') || '0') + 1;
    localStorage.setItem('imsg_visits', visitCount);
    var isRepeatVisitor = visitCount > 1;

    // Repeat visitors get proactive faster (4s vs 8s)
    var delay = isRepeatVisitor ? 4000 : IMSG.proactiveDelay;
    imsgProactiveTimer = setTimeout(imsgShowProactive, delay);

    // Exit intent (mouse leaves top of viewport)
    document.addEventListener('mouseleave', function(e) {
      if (e.clientY <= 0 && !imsgProactiveShown && !imsgIsOpen) {
        clearTimeout(imsgProactiveTimer);
        imsgShowProactive();
      }
    });

    // Scroll depth trigger — fires at 50% scroll
    var scrollFired = false;
    window.addEventListener('scroll', function() {
      if (scrollFired || imsgProactiveShown || imsgIsOpen) return;
      var scrollPct = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
      if (scrollPct >= 50) {
        scrollFired = true;
        clearTimeout(imsgProactiveTimer);
        setTimeout(imsgShowProactive, 1200);
      }
    }, { passive: true });

    // Idle detection — 45s no mouse movement
    var idleTimer;
    var idleFired = false;
    function resetIdle() {
      clearTimeout(idleTimer);
      if (!idleFired && !imsgProactiveShown && !imsgIsOpen) {
        idleTimer = setTimeout(function() {
          idleFired = true;
          clearTimeout(imsgProactiveTimer);
          imsgShowProactive();
        }, 45000);
      }
    }
    document.addEventListener('mousemove', resetIdle, { passive: true });
    document.addEventListener('keydown', resetIdle, { passive: true });
    resetIdle();

    // Cart abandonment — if cart page, fire proactive in 5s
    if (imsgDetectPageType() === 'cart') {
      clearTimeout(imsgProactiveTimer);
      imsgProactiveTimer = setTimeout(imsgShowProactive, 5000);
    }
  }
}

// Wait for DOM to be ready before initialising
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', imsgInit);
} else {
  imsgInit();
}

function applyBrandColor(color, accent) {
  var launcher = document.getElementById('imsg-launcher');
  var bg = (window.IMSG && IMSG.launcherBg) ? IMSG.launcherBg : 'gradient';
  if (bg === 'solid')      launcher.style.background = color;
  else if (bg === 'dark')  launcher.style.background = '#1c1c1e';
  else if (bg === 'white') launcher.style.background = '#ffffff';
  else                     launcher.style.background = 'linear-gradient(145deg,' + color + ',' + accent + ')';
  launcher.style.boxShadow = '0 4px 28px ' + color + '88, 0 2px 8px rgba(0,0,0,0.3)';
  var sendBtn = document.getElementById('imsg-send-btn');
  sendBtn.style.background    = color;
  sendBtn.style.boxShadow     = '0 2px 12px ' + color + '66';
  var avatar = document.getElementById('imsg-avatar');
  avatar.style.background     = 'linear-gradient(135deg,' + color + ',' + accent + ')';
  // Update product card badge colors
  document.querySelectorAll('.imsg-pc-badge').forEach(function(el) { el.style.color = color; });
  document.querySelectorAll('.imsg-pc-cta').forEach(function(el) { el.style.background = color; });
}

function getInitials(name) {
  return name.split(' ').map(function(w){ return w[0]; }).join('').slice(0,2).toUpperCase();
}

/* ── TOGGLE OPEN/CLOSE ───────────────────────────────────────────── */
function imsgToggle() {
  var win   = document.getElementById('imsg-window');
  var badge = document.getElementById('imsg-badge');
  var icon  = document.getElementById('imsg-launcher-icon');
  var close = document.getElementById('imsg-launcher-close');

  imsgIsOpen = !imsgIsOpen;
  win.classList.toggle('open', imsgIsOpen);
  icon.classList.toggle('hide', imsgIsOpen);
  close.classList.toggle('show', imsgIsOpen);

  if (imsgIsOpen) {
    badge.style.display = 'none';
    imsgDismissProactive();
    // Show welcome only if no session and no proactive message was injected
    if (imsgMsgCount === 0 && !imsgSessionRestored) setTimeout(imsgWelcome, 320);
    setTimeout(function(){ document.getElementById('imsg-textarea').focus(); }, 420);
  }
}

/* ── PROACTIVE BUBBLE ────────────────────────────────────────────── */
function imsgShowProactive() {
  if (imsgProactiveShown || imsgIsOpen) return;
  imsgProactiveShown = true;

  var pageType = imsgDetectPageType();
  var pageTitle = imsgGetProductTitle();

  fetch(IMSG_PROACTIVE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ page_type: pageType, page_title: pageTitle })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    document.getElementById('imsg-proactive-text').textContent = data.message || IMSG.greeting;
    var chipsEl = document.getElementById('imsg-proactive-chips');
    chipsEl.innerHTML = '';
    (data.chips || []).forEach(function(chip) {
      var btn = document.createElement('button');
      btn.className = 'imsg-proactive-chip';
      btn.textContent = chip;
      btn.onclick = function() {
        var proactiveMsg = document.getElementById('imsg-proactive-text').textContent;
        imsgDismissProactive();
        if (!imsgIsOpen) {
          // Prevent welcome from firing — we'll inject the proactive message instead
          imsgSessionRestored = true;
          imsgToggle();
        }
        setTimeout(function() {
          // If chat is empty, show the proactive message as Armie's opener first
          if (imsgMsgCount === 0) {
            addDateSep('Today');
            addMsg(proactiveMsg, 'recv');
            imsgHistory.push({ role: 'assistant', content: proactiveMsg });
          }
          addMsg(chip, 'sent');
          imsgHistory.push({ role: 'user', content: chip });
          imsgSaveSession();
          imsgAIReply();
        }, 350);
      };
      chipsEl.appendChild(btn);
    });
    document.getElementById('imsg-proactive-bubble').classList.add('show');
    // Show notification badge
    var badge = document.getElementById('imsg-badge');
    badge.style.display = 'flex';
  })
  .catch(function() {
    // Fallback proactive message
    document.getElementById('imsg-proactive-text').textContent = IMSG.greeting;
    document.getElementById('imsg-proactive-bubble').classList.add('show');
    var badge = document.getElementById('imsg-badge');
    badge.style.display = 'flex';
  });
}

// Clicking the proactive bubble itself opens chat with the proactive message as opener
function imsgOpenFromProactive() {
  var proactiveMsg = document.getElementById('imsg-proactive-text').textContent;
  imsgDismissProactive();
  if (!imsgIsOpen) {
    imsgSessionRestored = true; // prevent welcome from overriding
    imsgToggle();
  }
  setTimeout(function() {
    if (imsgMsgCount === 0) {
      addDateSep('Today');
      addMsg(proactiveMsg, 'recv');
      imsgHistory.push({ role: 'assistant', content: proactiveMsg });
      imsgSaveSession();
      setQRs(IMSG.quickReplies);
    }
  }, 350);
}

function imsgDismissProactive() {
  document.getElementById('imsg-proactive-bubble').classList.remove('show');
}

function imsgDetectPageType() {
  var path = window.location.pathname || '';
  if (path.indexOf('/products/') > -1) return 'product';
  if (path.indexOf('/collections/') > -1) return 'collection';
  if (path.indexOf('/cart') > -1) return 'cart';
  if (path.indexOf('/search') > -1) return 'search';
  return 'homepage';
}

function imsgGetProductTitle() {
  // Try to get the actual product title from the page for product-specific proactive messages
  try {
    var h1 = document.querySelector('h1.product__title, h1.product-title, h1[class*="product"], .product-single__title, [data-product-title]');
    if (h1) return h1.textContent.trim();
    var og = document.querySelector('meta[property="og:title"]');
    if (og) return og.getAttribute('content').replace(' – Limited Armor', '').replace(' | Limited Armor', '').trim();
  } catch(e) {}
  return document.title || '';
}

//* ── WELCOME FLOW ──────────────────────────────────────────── */
function imsgWelcome() {
  clearMsgs();
  addDateSep('Today');
  showTyping(function() {
    addMsg(IMSG.greeting, 'recv');
    setQRs(IMSG.quickReplies);
  }, 1500);
}

/* ── PERSISTENT CHAT SESSION ───────────────────────────────── */
var IMSG_SESSION_KEY = 'imsg_session_v1';
var IMSG_SESSION_MAX_AGE = 24 * 60 * 60 * 1000; // 24 hours

function imsgSaveSession() {
  try {
    var el = document.getElementById('imsg-msgs');
    localStorage.setItem(IMSG_SESSION_KEY, JSON.stringify({
      ts: Date.now(),
      html: el.innerHTML,
      history: imsgHistory,
      msgCount: imsgMsgCount
    }));
  } catch(e) {}
}

function imsgRestoreSession() {
  try {
    var raw = localStorage.getItem(IMSG_SESSION_KEY);
    if (!raw) return;
    var data = JSON.parse(raw);
    // Expire after 24 hours
    if (Date.now() - data.ts > IMSG_SESSION_MAX_AGE) {
      localStorage.removeItem(IMSG_SESSION_KEY);
      return;
    }
    if (data.html && data.html.length > 10) {
      document.getElementById('imsg-msgs').innerHTML = data.html;
      imsgHistory  = data.history  || [];
      imsgMsgCount = data.msgCount || 0;
      // Fix receipt timers — mark all as Read since they're restored
      document.querySelectorAll('.imsg-receipt').forEach(function(r) { r.textContent = 'Read'; });
      setTimeout(scrollBottom, 100);
      return true;
    }
  } catch(e) {}
  return false;
}

function imsgClearSession() {
  localStorage.removeItem(IMSG_SESSION_KEY);
}

/* ── MESSAGES ────────────────────────────────────────────────── */
function clearMsgs() {
  document.getElementById('imsg-msgs').innerHTML = '';
  imsgMsgCount = 0;
  imsgHistory  = [];
  imsgClearSession();
}

function addDateSep(t) {
  var el = document.getElementById('imsg-msgs');
  var d = document.createElement('div');
  d.className = 'imsg-date-sep';
  d.textContent = t;
  el.appendChild(d);
}

function addMsg(text, type) {
  var el = document.getElementById('imsg-msgs');
  var row = document.createElement('div');
  row.className = 'imsg-row ' + type;
  imsgMsgCount++;

  var bub = document.createElement('div');
  bub.className = 'imsg-bubble';
  bub.textContent = text;
  row.appendChild(bub);

  var ts = document.createElement('div');
  ts.className = 'imsg-ts';
  ts.textContent = imsgTime();
  row.appendChild(ts);

  if (type === 'sent') {
    var rec = document.createElement('div');
    rec.className = 'imsg-receipt';
    rec.textContent = 'Delivered';
    row.appendChild(rec);
    setTimeout(function(){ rec.textContent = 'Read'; }, 2200);
  }

  el.appendChild(row);
  scrollBottom();
  imsgSaveSession();
}

function addImgMsg(src, type) {
  var el = document.getElementById('imsg-msgs');
  var row = document.createElement('div');
  row.className = 'imsg-row ' + type;
  imsgMsgCount++;

  var wrap = document.createElement('div');
  wrap.className = 'imsg-bubble-img';
  var img = document.createElement('img');
  img.src = src;
  img.style.maxWidth = '200px';
  img.style.borderRadius = '14px';
  wrap.appendChild(img);
  row.appendChild(wrap);

  var ts = document.createElement('div');
  ts.className = 'imsg-ts';
  ts.textContent = imsgTime();
  row.appendChild(ts);

  if (type === 'sent') {
    var rec = document.createElement('div');
    rec.className = 'imsg-receipt';
    rec.textContent = 'Delivered';
    row.appendChild(rec);
    setTimeout(function(){ rec.textContent = 'Read'; }, 2200);
  }

  el.appendChild(row);
  scrollBottom();
}

function addProductCards(products) {
  if (!products || !products.length) return;
  var el = document.getElementById('imsg-msgs');
  var row = document.createElement('div');
  row.className = 'imsg-row recv';
  // Make the row full-width so carousel can extend edge-to-edge
  row.style.maxWidth = '100%';
  row.style.width = '100%';

  var wrap = document.createElement('div');
  wrap.className = 'imsg-product-cards-wrap';

  products.forEach(function(p) {
    var card = document.createElement('a');
    card.className = 'imsg-ai-product-card';
    card.href = p.url || '#';
    card.target = '_blank';
    card.rel = 'noopener';
    // Prevent drag from triggering navigation
    card.addEventListener('click', function(e) {
      if (wrap._dragged) { e.preventDefault(); }
    });

    // ── PRODUCT IMAGE (full-width top) ──
    var imgEl;
    if (p.image) {
      imgEl = document.createElement('img');
      imgEl.className = 'imsg-pc-img';
      imgEl.src = p.image;
      imgEl.alt = p.name || '';
      imgEl.loading = 'lazy';
      imgEl.onerror = function() {
        var ph = document.createElement('div');
        ph.className = 'imsg-pc-img-placeholder';
        ph.textContent = '📱';
        if (imgEl.parentNode) imgEl.parentNode.replaceChild(ph, imgEl);
      };
    } else {
      imgEl = document.createElement('div');
      imgEl.className = 'imsg-pc-img-placeholder';
      imgEl.textContent = '📱';
    }
    card.appendChild(imgEl);

    // ── BODY ──
    var body = document.createElement('div');
    body.className = 'imsg-pc-body';

    if (p.badge) {
      var badge = document.createElement('div');
      badge.className = 'imsg-pc-badge';
      badge.textContent = p.badge;
      badge.style.color = IMSG.brandColor;
      body.appendChild(badge);
    }

    var name = document.createElement('div');
    name.className = 'imsg-pc-name';
    name.textContent = p.name;
    body.appendChild(name);

    var priceRow = document.createElement('div');
    priceRow.className = 'imsg-pc-price-row';
    var price = document.createElement('span');
    price.className = 'imsg-pc-price';
    price.textContent = p.price;
    priceRow.appendChild(price);
    if (p.original_price) {
      var orig = document.createElement('span');
      orig.className = 'imsg-pc-original';
      orig.textContent = p.original_price;
      priceRow.appendChild(orig);
    }
    if (p.discount) {
      var disc = document.createElement('span');
      disc.className = 'imsg-pc-discount';
      disc.textContent = p.discount;
      priceRow.appendChild(disc);
    }
    body.appendChild(priceRow);

    if (p.rating && p.reviews) {
      var rating = document.createElement('div');
      rating.className = 'imsg-pc-rating';
      rating.textContent = '⭐ ' + p.rating + ' (' + p.reviews + ' reviews)';
      body.appendChild(rating);
    }
    card.appendChild(body);

    // ── CTA ──
    var cta = document.createElement('span');
    cta.className = 'imsg-pc-cta';
    cta.textContent = 'Shop →';
    cta.style.background = IMSG.brandColor;
    card.appendChild(cta);

    wrap.appendChild(card);
  });

  // ── MOUSE DRAG-TO-SCROLL (desktop) ──
  var isDragging = false, startX = 0, scrollLeft = 0;
  wrap.addEventListener('mousedown', function(e) {
    isDragging = true;
    wrap._dragged = false;
    startX = e.pageX - wrap.offsetLeft;
    scrollLeft = wrap.scrollLeft;
    wrap.classList.add('dragging');
  });
  document.addEventListener('mousemove', function(e) {
    if (!isDragging) return;
    e.preventDefault();
    var x = e.pageX - wrap.offsetLeft;
    var walk = (x - startX) * 1.2;
    if (Math.abs(walk) > 4) wrap._dragged = true;
    wrap.scrollLeft = scrollLeft - walk;
  });
  document.addEventListener('mouseup', function() {
    if (!isDragging) return;
    isDragging = false;
    wrap.classList.remove('dragging');
    setTimeout(function() { wrap._dragged = false; }, 100);
  });

  row.appendChild(wrap);
  el.appendChild(row);
  scrollBottom();
}

function showTyping(cb, delay) {
  var el = document.getElementById('imsg-msgs');
  var row = document.createElement('div');
  row.className = 'imsg-row recv';
  row.id = 'imsg-typing-row';
  var ind = document.createElement('div');
  ind.className = 'imsg-typing';
  ind.innerHTML = '<span></span><span></span><span></span>';
  row.appendChild(ind);
  el.appendChild(row);
  scrollBottom();
  setTimeout(function() {
    var tr = document.getElementById('imsg-typing-row');
    if (tr) tr.remove();
    cb();
  }, delay || 1400);
}

/* ── SEND ────────────────────────────────────────────────────────── */
function imsgSend() {
  if (imsgTypingLock) return;
  var inp    = document.getElementById('imsg-textarea');
  var text   = inp.value.trim();
  var hasImg = !!imsgPendingImg;

  if (!text && !hasImg) return;

  if (hasImg) {
    addImgMsg(imsgPendingImg, 'sent');
    imsgClearImgPreview();
  }
  if (text) {
    addMsg(text, 'sent');
    inp.value = '';
    imsgAutoResize(inp);
    imsgToggleSend();
    imsgHistory.push({ role: 'user', content: text });
    imsgAIReply();
  } else if (hasImg) {
    imsgHistory.push({ role: 'user', content: '[Customer sent an image]' });
    imsgAIReply();
  }
}

/* ── AI REPLY ENGINE ─────────────────────────────────────────────── */
function imsgAIReply() {
  if (imsgTypingLock) return;
  imsgTypingLock = true;

  // Show typing indicator immediately
  var el = document.getElementById('imsg-msgs');
  var typingRow = document.createElement('div');
  typingRow.className = 'imsg-row recv';
  typingRow.id = 'imsg-typing-row';
  var ind = document.createElement('div');
  ind.className = 'imsg-typing';
  ind.innerHTML = '<span></span><span></span><span></span>';
  typingRow.appendChild(ind);
  el.appendChild(typingRow);
  scrollBottom();

  // Get current page context (product title, URL) to help the AI
  var pageCtx = '';
  try {
    pageCtx = 'Page: ' + document.title + ' | URL: ' + window.location.href;
    var metaDesc = document.querySelector('meta[name="description"]');
    if (metaDesc) pageCtx += ' | ' + metaDesc.getAttribute('content');
  } catch(e) {}

  var pageType = imsgDetectPageType();

  fetch(IMSG_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: imsgHistory,
      store_context: pageCtx,
      page_type: pageType,
      page_title: document.title || ''
    })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    var tr = document.getElementById('imsg-typing-row');
    if (tr) tr.remove();

    var reply = data.reply || "I'm here to help! What can I do for you? 😊";
    addMsg(reply, 'recv');
    imsgHistory.push({ role: 'assistant', content: reply });
    imsgSaveSession();

    // Render product cards if AI returned them
    if (data.product_cards && data.product_cards.length) {
      setTimeout(function() { addProductCards(data.product_cards); }, 200);
    }

    // Update chips dynamically from AI response
    if (data.chips && data.chips.length) {
      setTimeout(function() { setQRs(data.chips); }, 300);
    }

    // Handle escalation
    if (data.escalate) {
      setTimeout(function() {
        addMsg('Connecting you with our support team now... 💙', 'recv');
      }, 800);
    }

    imsgTypingLock = false;
  })
  .catch(function(err) {
    var tr = document.getElementById('imsg-typing-row');
    if (tr) tr.remove();
    addMsg("Sorry, I'm having a quick connection issue. Email us at support@limitedarmor.com and we'll get back to you right away! 📧", 'recv');
    imsgTypingLock = false;
    console.warn('iMsg AI error:', err);
  });
}

/* ── QUICK REPLIES / CHIPS ───────────────────────────────────────── */
function setQRs(replies) {
  var el = document.getElementById('imsg-qr-bar');
  // Animate out old chips, animate in new
  el.style.opacity = '0';
  setTimeout(function() {
    el.innerHTML = replies.map(function(r) {
      return '<button class="imsg-qr-chip" onclick="imsgQR(this)">' + r + '</button>';
    }).join('');
    el.style.opacity = '1';
  }, 150);
}

function imsgQR(el) {
  if (imsgTypingLock) return;
  var text = el.textContent;
  addMsg(text, 'sent');
  imsgHistory.push({ role: 'user', content: text });
  imsgAIReply();
}

/* ── IMAGE IN MESSAGE ────────────────────────────────────────────── */
function imsgMsgImgSelected(e) {
  var file = e.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(ev) {
    imsgPendingImg = ev.target.result;
    var thumb = document.getElementById('imsg-img-thumb');
    thumb.src = imsgPendingImg;
    document.getElementById('imsg-img-strip').classList.add('visible');
    document.getElementById('imsg-send-btn').disabled = false;
  };
  reader.readAsDataURL(file);
  e.target.value = '';
}

function imsgClearImgPreview() {
  imsgPendingImg = null;
  document.getElementById('imsg-img-strip').classList.remove('visible');
  document.getElementById('imsg-img-thumb').src = '';
  imsgToggleSend();
}

/* ── UPLOAD PANEL ────────────────────────────────────────────────── */
/* ADMIN ONLY — set agent photo/logo via localStorage, not exposed to customers */

function applyAvatar(src) {
  // Header avatar
  var photo = document.getElementById('imsg-avatar-photo');
  photo.src = src;
  photo.classList.add('loaded');
  document.getElementById('imsg-avatar-initials').style.opacity = '0';

  // Launcher logo
  var launcherLogo = document.getElementById('imsg-launcher-logo');
  launcherLogo.src = src;
  launcherLogo.classList.add('loaded');
  document.getElementById('imsg-launcher-icon').style.opacity = '0';
}

function applyLogo(src) {
  var logoImg  = document.getElementById('imsg-brand-logo-img');
  var logoText = document.getElementById('imsg-brand-logo-text');
  logoImg.src = src;
  logoImg.classList.add('loaded');
  logoText.style.opacity = '0';
}



/* ── UTILITIES ───────────────────────────────────────────────────── */
function scrollBottom() {
  var el = document.getElementById('imsg-msgs');
  requestAnimationFrame(function(){ el.scrollTop = el.scrollHeight; });
}
function imsgTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
function imsgHandleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); imsgSend(); }
}
function imsgAutoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}
function imsgToggleSend() {
  var hasText = !!document.getElementById('imsg-textarea').value.trim();
  var hasImg  = !!imsgPendingImg;
  document.getElementById('imsg-send-btn').disabled = !(hasText || hasImg);
}
