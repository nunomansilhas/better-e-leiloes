/**
 * E-Leiloes Dashboard - Content Script
 * Injects UI improvements on e-leiloes.pt pages
 */

(function() {
  'use strict';

  console.log('[E-Leiloes Extension] Content script loaded');

  // State
  let favorites = [];
  let settings = {};

  // Initialize
  async function init() {
    // Load favorites and settings
    try {
      const response = await chrome.runtime.sendMessage({ type: 'get_favorites' });
      favorites = response?.favorites || [];
    } catch (e) {
      console.warn('[E-Leiloes] Failed to load favorites:', e);
    }

    try {
      const { settings: s } = await chrome.storage.sync.get('settings');
      settings = s || {};
    } catch (e) {
      console.warn('[E-Leiloes] Failed to load settings:', e);
    }

    // Inject improvements
    injectStyles();
    enhanceEventCards();
    enhanceEventDetailPage();
    setupObserver();

    console.log('[E-Leiloes Extension] Initialized');
  }

  // Inject additional styles
  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      /* E-Leiloes Dashboard Extension Styles */

      .eleiloes-ext-toolbar {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        flex-wrap: wrap;
      }

      .eleiloes-ext-btn {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        border: none;
        text-decoration: none;
      }

      .eleiloes-ext-btn-favorite {
        background: #fef3c7;
        color: #92400e;
      }

      .eleiloes-ext-btn-favorite:hover {
        background: #fde68a;
      }

      .eleiloes-ext-btn-favorite.active {
        background: #f59e0b;
        color: white;
      }

      .eleiloes-ext-btn-notify {
        background: #dbeafe;
        color: #1e40af;
      }

      .eleiloes-ext-btn-notify:hover {
        background: #bfdbfe;
      }

      .eleiloes-ext-btn-dashboard {
        background: #f3e8ff;
        color: #6b21a8;
      }

      .eleiloes-ext-btn-dashboard:hover {
        background: #e9d5ff;
      }

      .eleiloes-ext-price-highlight {
        animation: eleiloes-price-pulse 2s ease-in-out;
      }

      @keyframes eleiloes-price-pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); background: #dcfce7; }
      }

      .eleiloes-ext-toast {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #1e293b;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: eleiloes-toast-in 0.3s ease;
        max-width: 350px;
      }

      .eleiloes-ext-toast.price-up {
        border-left: 4px solid #22c55e;
      }

      .eleiloes-ext-toast.price-down {
        border-left: 4px solid #ef4444;
      }

      @keyframes eleiloes-toast-in {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }

      .eleiloes-ext-badge {
        position: absolute;
        top: -4px;
        right: -4px;
        background: #ef4444;
        color: white;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 10px;
        min-width: 18px;
        text-align: center;
      }

      .eleiloes-ext-favorite-star {
        position: absolute;
        top: 8px;
        right: 8px;
        width: 24px;
        height: 24px;
        background: rgba(255, 255, 255, 0.9);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.2s;
        z-index: 10;
      }

      .eleiloes-ext-favorite-star:hover {
        transform: scale(1.1);
        background: #fef3c7;
      }

      .eleiloes-ext-favorite-star.active {
        background: #f59e0b;
        color: white;
      }

      .eleiloes-ext-ending-soon {
        border: 2px solid #f59e0b !important;
        box-shadow: 0 0 10px rgba(245, 158, 11, 0.3) !important;
      }

      .eleiloes-ext-ending-badge {
        position: absolute;
        top: 8px;
        left: 8px;
        background: linear-gradient(135deg, #f59e0b, #d97706);
        color: white;
        font-size: 10px;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 4px;
        z-index: 10;
        animation: eleiloes-pulse 2s infinite;
      }

      @keyframes eleiloes-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
      }
    `;
    document.head.appendChild(style);
  }

  // Enhance event cards on listing pages
  function enhanceEventCards() {
    // Find all event cards (adjust selector based on actual e-leiloes.pt structure)
    const cards = document.querySelectorAll('[class*="card"], [class*="evento"], [class*="item"]');

    cards.forEach(card => {
      // Skip if already enhanced
      if (card.dataset.eleiloesEnhanced) return;
      card.dataset.eleiloesEnhanced = 'true';

      // Try to extract reference from card
      const reference = extractReference(card);
      if (!reference) return;

      // Make card position relative for absolute positioning
      card.style.position = 'relative';

      // Add favorite star
      const star = createFavoriteStar(reference);
      card.appendChild(star);

      // Check if ending soon
      const endTime = extractEndTime(card);
      if (endTime && isEndingSoon(endTime)) {
        card.classList.add('eleiloes-ext-ending-soon');
        const badge = document.createElement('div');
        badge.className = 'eleiloes-ext-ending-badge';
        badge.textContent = 'A terminar!';
        card.appendChild(badge);
      }
    });
  }

  // Enhance event detail page
  function enhanceEventDetailPage() {
    // Check if we're on a detail page
    const url = window.location.pathname;
    if (!url.includes('/eventos/') && !url.includes('/imoveis/') && !url.includes('/veiculos/')) {
      return;
    }

    // Extract reference from URL or page content
    const reference = extractReferenceFromPage();
    if (!reference) return;

    // Find a good place to inject toolbar
    const targetSelectors = [
      '.event-actions',
      '.details-header',
      '.price-section',
      '[class*="header"]',
      '[class*="title"]'
    ];

    let target = null;
    for (const selector of targetSelectors) {
      target = document.querySelector(selector);
      if (target) break;
    }

    if (!target) {
      // Fallback: insert after first h1
      target = document.querySelector('h1');
    }

    if (target) {
      const toolbar = createToolbar(reference);
      target.insertAdjacentElement('afterend', toolbar);
    }
  }

  // Create favorite star element
  function createFavoriteStar(reference) {
    const star = document.createElement('div');
    star.className = 'eleiloes-ext-favorite-star';
    star.dataset.reference = reference;

    if (favorites.includes(reference)) {
      star.classList.add('active');
    }

    star.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="${favorites.includes(reference) ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
      </svg>
    `;

    star.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const isActive = star.classList.contains('active');

      if (isActive) {
        await chrome.runtime.sendMessage({ type: 'remove_favorite', reference });
        star.classList.remove('active');
        star.querySelector('svg').setAttribute('fill', 'none');
        favorites = favorites.filter(f => f !== reference);
      } else {
        await chrome.runtime.sendMessage({ type: 'add_favorite', reference });
        star.classList.add('active');
        star.querySelector('svg').setAttribute('fill', 'currentColor');
        favorites.push(reference);
      }

      showToast(isActive ? 'Removido dos favoritos' : 'Adicionado aos favoritos', 'info');
    });

    return star;
  }

  // Create action toolbar
  function createToolbar(reference) {
    const toolbar = document.createElement('div');
    toolbar.className = 'eleiloes-ext-toolbar';

    const isFavorite = favorites.includes(reference);

    toolbar.innerHTML = `
      <button class="eleiloes-ext-btn eleiloes-ext-btn-favorite ${isFavorite ? 'active' : ''}" data-action="favorite">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="${isFavorite ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
        </svg>
        <span>${isFavorite ? 'Favorito' : 'Adicionar'}</span>
      </button>
      <button class="eleiloes-ext-btn eleiloes-ext-btn-notify" data-action="notify">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        <span>Notificar</span>
      </button>
      <a class="eleiloes-ext-btn eleiloes-ext-btn-dashboard" href="${getDashboardUrl()}/eventos/${reference}" target="_blank">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        <span>Ver no Dashboard</span>
      </a>
    `;

    // Add event listeners
    toolbar.querySelector('[data-action="favorite"]').addEventListener('click', async () => {
      const btn = toolbar.querySelector('[data-action="favorite"]');
      const isActive = btn.classList.contains('active');

      if (isActive) {
        await chrome.runtime.sendMessage({ type: 'remove_favorite', reference });
        btn.classList.remove('active');
        btn.querySelector('svg').setAttribute('fill', 'none');
        btn.querySelector('span').textContent = 'Adicionar';
        favorites = favorites.filter(f => f !== reference);
      } else {
        await chrome.runtime.sendMessage({ type: 'add_favorite', reference });
        btn.classList.add('active');
        btn.querySelector('svg').setAttribute('fill', 'currentColor');
        btn.querySelector('span').textContent = 'Favorito';
        favorites.push(reference);
      }

      showToast(isActive ? 'Removido dos favoritos' : 'Adicionado aos favoritos', 'info');
    });

    toolbar.querySelector('[data-action="notify"]').addEventListener('click', async () => {
      // Request notification permission if needed
      if (Notification.permission === 'default') {
        await Notification.requestPermission();
      }
      showToast('Notificacoes ativadas para este leilao', 'success');
    });

    return toolbar;
  }

  // Extract reference from element
  function extractReference(element) {
    // Try different patterns
    const patterns = [
      /(?:LO|NP)[-\s]?\d{10,}/i,
      /(?:referencia|ref)[:\s]*([A-Z]{2}[-\s]?\d+)/i
    ];

    // Check href
    const link = element.querySelector('a[href*="eventos/"], a[href*="imoveis/"], a[href*="veiculos/"]');
    if (link) {
      const match = link.href.match(/\/(LO|NP)[-]?(\d+)/i);
      if (match) return `${match[1]}${match[2]}`;
    }

    // Check text content
    const text = element.textContent;
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) return match[1] || match[0];
    }

    return null;
  }

  // Extract reference from current page
  function extractReferenceFromPage() {
    // Try URL first
    const urlMatch = window.location.pathname.match(/\/(LO|NP)[-]?(\d+)/i);
    if (urlMatch) return `${urlMatch[1]}${urlMatch[2]}`;

    // Try page content
    const pageText = document.body.textContent;
    const match = pageText.match(/(?:Referencia|Ref\.?)[:\s]*((?:LO|NP)[-\s]?\d+)/i);
    if (match) return match[1].replace(/[-\s]/g, '');

    return null;
  }

  // Extract end time from element
  function extractEndTime(element) {
    const text = element.textContent;

    // Look for date patterns
    const patterns = [
      /termina[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/i,
      /fim[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/i,
      /(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s*(?:as\s*)?(\d{1,2}:\d{2})/i
    ];

    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (match) {
        try {
          return new Date(match[1]);
        } catch (e) {
          continue;
        }
      }
    }

    return null;
  }

  // Check if ending within 24 hours
  function isEndingSoon(endTime) {
    const now = new Date();
    const diff = endTime - now;
    const hoursRemaining = diff / (1000 * 60 * 60);
    return hoursRemaining > 0 && hoursRemaining <= 24;
  }

  // Get dashboard URL
  function getDashboardUrl() {
    return settings.backendUrl || 'http://localhost:8000';
  }

  // Show toast notification
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `eleiloes-ext-toast ${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'eleiloes-toast-in 0.3s ease reverse';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  // Setup mutation observer for dynamic content
  function setupObserver() {
    const observer = new MutationObserver((mutations) => {
      let shouldEnhance = false;

      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          shouldEnhance = true;
          break;
        }
      }

      if (shouldEnhance) {
        // Debounce enhancement
        clearTimeout(window.eleiloesEnhanceTimeout);
        window.eleiloesEnhanceTimeout = setTimeout(enhanceEventCards, 500);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'price_change') {
      handlePriceChangeOnPage(message);
    }

    if (message.type === 'event_ended') {
      handleEventEndedOnPage(message);
    }

    sendResponse({ received: true });
    return true;
  });

  // Handle price change notification on page
  function handlePriceChangeOnPage(data) {
    // Highlight price if visible
    const priceElements = document.querySelectorAll('[class*="price"], [class*="lance"], [class*="valor"]');

    priceElements.forEach(el => {
      if (el.textContent.includes(data.old_price) || el.textContent.includes(data.reference)) {
        el.classList.add('eleiloes-ext-price-highlight');
        setTimeout(() => el.classList.remove('eleiloes-ext-price-highlight'), 2000);
      }
    });

    // Show toast
    const change = data.new_price - data.old_price;
    const changeType = change > 0 ? 'price-up' : 'price-down';
    showToast(
      `${data.reference}: Novo lance ${formatPrice(data.new_price)} (${change > 0 ? '+' : ''}${formatPrice(change)})`,
      changeType
    );
  }

  // Handle event ended on page
  function handleEventEndedOnPage(data) {
    showToast(`Leilao ${data.reference} terminou! Preco final: ${formatPrice(data.final_price)}`, 'info');
  }

  // Format price
  function formatPrice(price) {
    if (typeof price !== 'number') return 'N/A';
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR'
    }).format(price);
  }

  // Start
  init();
})();
