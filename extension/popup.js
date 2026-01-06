/**
 * E-Leiloes Dashboard - Popup Script
 */

// Default settings
const DEFAULT_SETTINGS = {
  backendUrl: 'http://localhost:8000',
  notificationsEnabled: true,
  soundEnabled: true,
  autoConnect: true
};

// DOM Elements
const elements = {
  statusDot: document.getElementById('statusDot'),
  statusText: document.getElementById('statusText'),
  btnConnect: document.getElementById('btnConnect'),
  btnRefresh: document.getElementById('btnRefresh'),
  btnSettings: document.getElementById('btnSettings'),
  btnOptions: document.getElementById('btnOptions'),
  btnClearNotifs: document.getElementById('btnClearNotifs'),
  statNotifications: document.getElementById('statNotifications'),
  statFavorites: document.getElementById('statFavorites'),
  statEnding: document.getElementById('statEnding'),
  notificationList: document.getElementById('notificationList'),
  notifBadge: document.getElementById('notifBadge'),
  favoritesList: document.getElementById('favoritesList'),
  linkDashboard: document.getElementById('linkDashboard')
};

// State
let isConnected = false;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  await updateConnectionStatus();
  await loadNotifications();
  await loadFavorites();
  setupEventListeners();
});

// Load settings
async function loadSettings() {
  const { settings = DEFAULT_SETTINGS } = await chrome.storage.sync.get('settings');
  elements.linkDashboard.href = settings.backendUrl || DEFAULT_SETTINGS.backendUrl;
}

// Update connection status
async function updateConnectionStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'get_status' });
    isConnected = response?.connected || false;

    if (isConnected) {
      elements.statusDot.className = 'status-dot connected';
      elements.statusText.textContent = 'Conectado ao servidor';
      elements.btnConnect.textContent = 'Desligar';
    } else {
      elements.statusDot.className = 'status-dot';
      elements.statusText.textContent = 'Desconectado';
      elements.btnConnect.textContent = 'Ligar';
    }
  } catch (error) {
    console.error('Error getting status:', error);
    elements.statusDot.className = 'status-dot';
    elements.statusText.textContent = 'Erro de comunicacao';
  }
}

// Load notifications
async function loadNotifications() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'get_notifications' });
    const notifications = response?.notifications || [];
    const { unreadCount = 0 } = await chrome.storage.local.get('unreadCount');

    elements.statNotifications.textContent = unreadCount.toString();

    if (unreadCount > 0) {
      elements.notifBadge.style.display = 'inline';
      elements.notifBadge.textContent = unreadCount.toString();
    } else {
      elements.notifBadge.style.display = 'none';
    }

    renderNotifications(notifications.slice(0, 5));
  } catch (error) {
    console.error('Error loading notifications:', error);
  }
}

// Render notifications
function renderNotifications(notifications) {
  if (notifications.length === 0) {
    elements.notificationList.innerHTML = `
      <div class="empty-state">
        <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"/>
        </svg>
        <p>Sem notificacoes recentes</p>
      </div>
    `;
    return;
  }

  elements.notificationList.innerHTML = notifications.map(notif => {
    if (notif.type === 'price_change') {
      const change = notif.newPrice - notif.oldPrice;
      const changePercent = ((change / notif.oldPrice) * 100).toFixed(1);
      const isPositive = change > 0;

      return `
        <div class="notification-item" data-reference="${notif.reference}">
          <div class="notification-header">
            <span class="notification-ref">${notif.reference}</span>
            <span class="notification-time">${formatTime(notif.timestamp)}</span>
          </div>
          <div class="notification-body">Alteracao de preco</div>
          <div class="notification-price">
            <span class="notification-price-old">${formatPrice(notif.oldPrice)}</span>
            <span class="notification-price-new">${formatPrice(notif.newPrice)}</span>
            <span class="notification-price-change ${isPositive ? '' : 'negative'}">
              ${isPositive ? '+' : ''}${changePercent}%
            </span>
          </div>
        </div>
      `;
    }

    if (notif.type === 'event_ended') {
      return `
        <div class="notification-item" data-reference="${notif.reference}">
          <div class="notification-header">
            <span class="notification-ref">${notif.reference}</span>
            <span class="notification-time">${formatTime(notif.timestamp)}</span>
          </div>
          <div class="notification-body">Leilao terminado</div>
          <div class="notification-price">
            <span class="notification-price-new">${formatPrice(notif.finalPrice)}</span>
          </div>
        </div>
      `;
    }

    return '';
  }).join('');

  // Add click handlers
  document.querySelectorAll('.notification-item').forEach(item => {
    item.addEventListener('click', () => {
      const reference = item.dataset.reference;
      if (reference) {
        chrome.tabs.create({ url: `https://e-leiloes.pt/eventos/${reference}` });
      }
    });
  });
}

// Load favorites
async function loadFavorites() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'get_favorites' });
    const favorites = response?.favorites || [];

    elements.statFavorites.textContent = favorites.length.toString();
    renderFavorites(favorites);
  } catch (error) {
    console.error('Error loading favorites:', error);
  }
}

// Render favorites
function renderFavorites(favorites) {
  if (favorites.length === 0) {
    elements.favoritesList.innerHTML = `
      <div class="empty-state">
        <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z"/>
        </svg>
        <p>Nenhum favorito adicionado</p>
      </div>
    `;
    return;
  }

  elements.favoritesList.innerHTML = favorites.map(ref => `
    <div class="favorite-item" data-reference="${ref}">
      <span class="favorite-ref">${ref}</span>
      <button class="favorite-remove" title="Remover">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
  `).join('');

  // Add click handlers
  document.querySelectorAll('.favorite-item').forEach(item => {
    item.addEventListener('click', (e) => {
      if (!e.target.closest('.favorite-remove')) {
        const reference = item.dataset.reference;
        if (reference) {
          chrome.tabs.create({ url: `https://e-leiloes.pt/eventos/${reference}` });
        }
      }
    });
  });

  // Add remove handlers
  document.querySelectorAll('.favorite-remove').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const item = btn.closest('.favorite-item');
      const reference = item.dataset.reference;

      await chrome.runtime.sendMessage({ type: 'remove_favorite', reference });
      await loadFavorites();
    });
  });
}

// Setup event listeners
function setupEventListeners() {
  // Connect/Disconnect button
  elements.btnConnect.addEventListener('click', async () => {
    if (isConnected) {
      await chrome.runtime.sendMessage({ type: 'disconnect' });
    } else {
      await chrome.runtime.sendMessage({ type: 'connect' });
    }
    await updateConnectionStatus();
  });

  // Refresh button
  elements.btnRefresh.addEventListener('click', async () => {
    elements.btnRefresh.style.animation = 'spin 0.5s linear';
    await loadNotifications();
    await loadFavorites();
    await updateConnectionStatus();
    setTimeout(() => {
      elements.btnRefresh.style.animation = '';
    }, 500);
  });

  // Settings button
  elements.btnSettings.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // Options link
  elements.btnOptions.addEventListener('click', (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });

  // Clear notifications
  elements.btnClearNotifs.addEventListener('click', async () => {
    await chrome.runtime.sendMessage({ type: 'clear_notifications' });
    await loadNotifications();
  });

  // Listen for connection status changes
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'connection_status') {
      if (message.status === 'connected') {
        elements.statusDot.className = 'status-dot connected';
        elements.statusText.textContent = 'Conectado ao servidor';
        elements.btnConnect.textContent = 'Desligar';
        isConnected = true;
      } else if (message.status === 'reconnecting') {
        elements.statusDot.className = 'status-dot connecting';
        elements.statusText.textContent = `A reconectar... (${message.message})`;
      } else {
        elements.statusDot.className = 'status-dot';
        elements.statusText.textContent = message.message || 'Desconectado';
        elements.btnConnect.textContent = 'Ligar';
        isConnected = false;
      }
    }

    // Update notifications on new events
    if (message.type === 'price_change' || message.type === 'event_ended') {
      loadNotifications();
    }
  });
}

// Helper: Format price
function formatPrice(price) {
  if (typeof price !== 'number') return 'N/A';
  return new Intl.NumberFormat('pt-PT', {
    style: 'currency',
    currency: 'EUR'
  }).format(price);
}

// Helper: Format time
function formatTime(timestamp) {
  if (!timestamp) return '';

  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return 'Agora';
  if (diffMins < 60) return `${diffMins}min`;
  if (diffHours < 24) return `${diffHours}h`;

  return date.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' });
}

// Add spin animation style
const style = document.createElement('style');
style.textContent = `
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);
