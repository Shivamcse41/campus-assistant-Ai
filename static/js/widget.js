/**
 * CampConnect Embeddable Chatbot Widget
 * ──────────────────────────────────────
 * Embed this widget by adding a script tag:
 * <script src="http://localhost:8000/static/js/widget.js" data-client-id="YOUR_CLIENT_ID" defer></script>
 */

(function () {
  // ── Retrieve Client ID ──────────────────────────────────────────────────────
  const scriptTag = document.currentScript;
  const clientId = scriptTag ? scriptTag.getAttribute('data-client-id') : null;

  if (!clientId) {
    console.error('CampConnect Widget: Missing data-client-id attribute on the script tag.');
    return;
  }

  const hostUrl = scriptTag ? new URL(scriptTag.src).origin : window.location.origin;

  // ── CSS Variables & Styles injection ────────────────────────────────────────
  const widgetStyles = `
    /* Widget Colors: Luxury Charcoal (#111827), Gold (#d97706), Cream (#fef3c7) */
    :root {
      --ccw-bg-dark: #0f172a;
      --ccw-bg-surface: #1e293b;
      --ccw-gold: #d97706;
      --ccw-gold-light: #f59e0b;
      --ccw-cream: #f8fafc;
      --ccw-cream-muted: #94a3b8;
      --ccw-border: rgba(217, 119, 6, 0.2);
      --ccw-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), 0 0 20px rgba(217, 119, 6, 0.1);
    }

    #cc-widget-container * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    }

    /* Floating Button */
    #cc-widget-trigger {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border: 2px solid var(--ccw-gold);
      box-shadow: var(--ccw-shadow);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    #cc-widget-trigger:hover {
      transform: scale(1.08) rotate(5deg);
      border-color: var(--ccw-gold-light);
      box-shadow: 0 12px 35px rgba(0, 0, 0, 0.5), 0 0 30px rgba(217, 119, 6, 0.25);
    }

    #cc-widget-trigger svg {
      width: 28px;
      height: 28px;
      fill: var(--ccw-gold);
      transition: fill 0.3s ease;
    }

    #cc-widget-trigger:hover svg {
      fill: var(--ccw-gold-light);
    }

    /* Chat Window */
    #cc-widget-window {
      position: fixed;
      bottom: 96px;
      right: 24px;
      width: 380px;
      height: 520px;
      max-height: calc(100vh - 140px);
      background: var(--ccw-bg-dark);
      border: 1px solid var(--ccw-border);
      border-radius: 16px;
      box-shadow: var(--ccw-shadow);
      z-index: 999999;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      opacity: 0;
      transform: translateY(20px) scale(0.95);
      pointer-events: none;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    #cc-widget-window.cc-active {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: all;
    }

    /* Header */
    .cc-widget-header {
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border-bottom: 1px solid var(--ccw-border);
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .cc-widget-brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .cc-widget-icon {
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, var(--ccw-gold) 0%, #78350f 100%);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
    }

    .cc-widget-title {
      font-weight: 700;
      color: var(--ccw-cream);
      font-size: 15px;
    }

    .cc-widget-subtitle {
      font-size: 11px;
      color: var(--ccw-cream-muted);
    }

    .cc-widget-close {
      background: transparent;
      border: none;
      color: var(--ccw-cream-muted);
      cursor: pointer;
      font-size: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 0.2s ease;
    }

    .cc-widget-close:hover {
      color: var(--ccw-gold-light);
    }

    /* Messages Area */
    .cc-widget-messages {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #090d16;
    }

    /* Scrollbar */
    .cc-widget-messages::-webkit-scrollbar {
      width: 5px;
    }
    .cc-widget-messages::-webkit-scrollbar-track {
      background: transparent;
    }
    .cc-widget-messages::-webkit-scrollbar-thumb {
      background: var(--ccw-border);
      border-radius: 10px;
    }

    /* Bubbles */
    .cc-msg-bubble {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13.5px;
      line-height: 1.5;
      color: var(--ccw-cream);
      word-wrap: break-word;
      animation: ccBubbleIn 0.25s ease-out;
    }

    @keyframes ccBubbleIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .cc-msg-bubble.cc-user {
      align-self: flex-end;
      background: linear-gradient(135deg, var(--ccw-gold) 0%, #b45309 100%);
      border-bottom-right-radius: 2px;
      box-shadow: 0 4px 12px rgba(217, 119, 6, 0.15);
    }

    .cc-msg-bubble.cc-bot {
      align-self: flex-start;
      background: var(--ccw-bg-surface);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-bottom-left-radius: 2px;
    }

    .cc-msg-source {
      display: block;
      margin-top: 6px;
      font-size: 10.5px;
      color: var(--ccw-cream-muted);
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      padding-top: 4px;
      font-style: italic;
    }

    /* Typing Dots */
    .cc-typing-indicator {
      display: flex;
      gap: 4px;
      padding: 6px 4px;
    }

    .cc-typing-indicator span {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--ccw-cream-muted);
      animation: ccDotBounce 1.2s infinite ease-in-out;
    }

    .cc-typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
    .cc-typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes ccDotBounce {
      0%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-5px); }
    }

    /* Input Area */
    .cc-widget-input-area {
      padding: 12px 16px;
      background: var(--ccw-bg-surface);
      border-top: 1px solid var(--ccw-border);
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .cc-widget-input {
      flex: 1;
      height: 38px;
      background: rgba(0, 0, 0, 0.2);
      border: 1px solid var(--ccw-border);
      border-radius: 8px;
      padding: 0 12px;
      color: var(--ccw-cream);
      font-size: 13.5px;
      outline: none;
      transition: all 0.2s ease;
    }

    .cc-widget-input::placeholder {
      color: var(--ccw-cream-muted);
    }

    .cc-widget-input:focus {
      border-color: var(--ccw-gold-light);
      background: rgba(0, 0, 0, 0.3);
      box-shadow: 0 0 0 2px rgba(217, 119, 6, 0.15);
    }

    .cc-widget-send {
      width: 38px;
      height: 38px;
      border-radius: 8px;
      background: var(--ccw-gold);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease;
    }

    .cc-widget-send:hover {
      background: var(--ccw-gold-light);
      transform: translateY(-1px);
    }

    .cc-widget-send svg {
      width: 16px;
      height: 16px;
      fill: #fff;
    }

    .cc-widget-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }

    /* Mobile Adaptability */
    @media (max-width: 450px) {
      #cc-widget-window {
        bottom: 0;
        right: 0;
        width: 100%;
        height: 100%;
        max-height: 100%;
        border-radius: 0;
        border: none;
      }
      #cc-widget-trigger {
        bottom: 16px;
        right: 16px;
      }
    }
  `;

  // Inject Styles
  const styleEl = document.createElement('style');
  styleEl.textContent = widgetStyles;
  document.head.appendChild(styleEl);

  // ── Render Widget HTML ──────────────────────────────────────────────────────
  const widgetContainer = document.createElement('div');
  widgetContainer.id = 'cc-widget-container';

  widgetContainer.innerHTML = `
    <!-- Floating Button -->
    <button id="cc-widget-trigger" title="Chat with AI" aria-label="Open Chat">
      <svg viewBox="0 0 24 24">
        <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/>
      </svg>
    </button>

    <!-- Chat Drawer -->
    <div id="cc-widget-window">
      <!-- Header -->
      <div class="cc-widget-header">
        <div class="cc-widget-brand">
          <div class="cc-widget-icon">⚜️</div>
          <div>
            <div class="cc-widget-title">CampConnect</div>
            <div class="cc-widget-subtitle">AI Concierge Assistant</div>
          </div>
        </div>
        <button class="cc-widget-close" id="cc-widget-close" aria-label="Close Chat">&times;</button>
      </div>

      <!-- Messages Area -->
      <div class="cc-widget-messages" id="cc-widget-msgs">
        <div class="cc-msg-bubble cc-bot">
          Welcome! I am your AI assistant, powered by the organization's knowledge base. How may I assist you today?
        </div>
      </div>

      <!-- Input Area -->
      <div class="cc-widget-input-area">
        <input type="text" class="cc-widget-input" id="cc-widget-input" placeholder="Type your inquiry here..." />
        <button class="cc-widget-send" id="cc-widget-send" aria-label="Send Message">
          <svg viewBox="0 0 24 24">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(widgetContainer);

  // ── Element References ──────────────────────────────────────────────────────
  const triggerBtn = document.getElementById('cc-widget-trigger');
  const chatWindow = document.getElementById('cc-widget-window');
  const closeBtn = document.getElementById('cc-widget-close');
  const messageInput = document.getElementById('cc-widget-input');
  const sendBtn = document.getElementById('cc-widget-send');
  const messagesBox = document.getElementById('cc-widget-msgs');

  let isOpen = false;

  // ── Event Handlers ──────────────────────────────────────────────────────────
  function toggleChat() {
    isOpen = !isOpen;
    if (isOpen) {
      chatWindow.classList.add('cc-active');
      triggerBtn.style.display = 'none'; // Hide floating button when chat is open
      setTimeout(() => messageInput.focus(), 100);
    } else {
      chatWindow.classList.remove('cc-active');
      triggerBtn.style.display = 'flex'; // Restore floating button when closed
    }
  }

  triggerBtn.addEventListener('click', toggleChat);
  closeBtn.addEventListener('click', toggleChat);

  // Send message trigger
  async function handleSend() {
    const question = messageInput.value.trim();
    if (!question) return;

    // Append user message
    appendBubble('cc-user', question);
    messageInput.value = '';
    sendBtn.disabled = true;

    // Append typing indicator
    const thinkingBubble = appendBubble('cc-bot', `
      <div class="cc-typing-indicator">
        <span></span><span></span><span></span>
      </div>
    `);
    messagesBox.scrollTop = messagesBox.scrollHeight;

    try {
      const res = await fetch(`${hostUrl}/api/query/public/${clientId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question })
      });

      thinkingBubble.remove(); // Remove thinking bubble

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Query failed');

      // Append bot bubble
      let botContent = `<div>${escapeHTML(data.answer)}</div>`;
      if (data.sources && data.sources.length > 0) {
        const srcNames = [...new Set(data.sources.map(s => s.source))].join(', ');
        botContent += `<span class="cc-msg-source">Reference: ${escapeHTML(srcNames)}</span>`;
      }
      appendBubble('cc-bot', botContent);

    } catch (err) {
      console.error(err);
      thinkingBubble.remove();
      appendBubble('cc-bot', `<div style="color:#ef4444;">⚠️ Error: ${escapeHTML(err.message)}</div>`);
    } finally {
      sendBtn.disabled = false;
      messageInput.focus();
    }

    messagesBox.scrollTop = messagesBox.scrollHeight;
  }

  sendBtn.addEventListener('click', handleSend);
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleSend();
  });

  // Helper to append bubble
  function appendBubble(sender, htmlContent) {
    const bubble = document.createElement('div');
    bubble.className = `cc-msg-bubble ${sender}`;
    bubble.innerHTML = htmlContent;
    messagesBox.appendChild(bubble);
    return bubble;
  }

  // HTML escaping utility
  function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
      tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
      }[tag] || tag)
    );
  }

})();
