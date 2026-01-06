/**
 * E-Leiloes Dashboard - Background Service Worker
 * Handles SSE connection, notifications, and badge updates
 */

// Default settings
const DEFAULT_SETTINGS = {
  backendUrl: 'http://localhost:8000',
  notificationsEnabled: true,
  soundEnabled: true,
  autoConnect: true
};

// State
let sseConnection = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 5000;

// Initialize on install
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log('[E-Leiloes] Extension installed/updated:', details.reason);

  // Set default settings on first install
  if (details.reason === 'install') {
    await chrome.storage.sync.set({ settings: DEFAULT_SETTINGS });
    console.log('[E-Leiloes] Default settings saved');
  }

  // Initialize badge
  await updateBadge(0);

  // Auto-connect if enabled
  const { settings } = await chrome.storage.sync.get('settings');
  if (settings?.autoConnect) {
    connectToSSE();
  }
});

// Handle startup
chrome.runtime.onStartup.addListener(async () => {
  console.log('[E-Leiloes] Browser started');
  const { settings } = await chrome.storage.sync.get('settings');
  if (settings?.autoConnect) {
    connectToSSE();
  }
});

// Connect to SSE endpoint
async function connectToSSE() {
  const { settings } = await chrome.storage.sync.get('settings');
  const backendUrl = settings?.backendUrl || DEFAULT_SETTINGS.backendUrl;
  const sseUrl = `${backendUrl}/api/events/live`;

  console.log('[E-Leiloes] Connecting to SSE:', sseUrl);

  // Close existing connection
  if (sseConnection) {
    sseConnection.close();
  }

  try {
    // Use fetch for SSE in service worker (EventSource not available)
    const response = await fetch(sseUrl, {
      headers: {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache'
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    reconnectAttempts = 0;
    broadcastConnectionStatus('connected');
    console.log('[E-Leiloes] SSE connected!');

    // Read stream
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        console.log('[E-Leiloes] SSE stream ended');
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete messages
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            await handleSSEMessage(data);
          } catch (e) {
            console.warn('[E-Leiloes] Failed to parse SSE data:', e);
          }
        }
      }
    }

    // Stream ended - reconnect
    scheduleReconnect();

  } catch (error) {
    console.error('[E-Leiloes] SSE connection error:', error);
    broadcastConnectionStatus('error', error.message);
    scheduleReconnect();
  }
}

// Schedule reconnection
function scheduleReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.log('[E-Leiloes] Max reconnect attempts reached');
    broadcastConnectionStatus('disconnected');
    return;
  }

  reconnectAttempts++;
  const delay = RECONNECT_DELAY * reconnectAttempts;
  console.log(`[E-Leiloes] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);

  broadcastConnectionStatus('reconnecting', `Attempt ${reconnectAttempts}`);

  setTimeout(connectToSSE, delay);
}

// Handle SSE messages
async function handleSSEMessage(data) {
  console.log('[E-Leiloes] SSE message:', data);

  if (data.type === 'ping') {
    return; // Ignore keepalive pings
  }

  if (data.type === 'connected') {
    console.log('[E-Leiloes] SSE confirmed connected');
    return;
  }

  // Price update notification
  if (data.type === 'price_change') {
    await handlePriceChange(data);
  }

  // Event ended notification
  if (data.type === 'event_ended') {
    await handleEventEnded(data);
  }

  // Forward to content scripts and popup
  broadcastToContentScripts(data);
}

// Handle price change events
async function handlePriceChange(data) {
  const { settings } = await chrome.storage.sync.get('settings');

  // Store notification
  await storeNotification({
    type: 'price_change',
    reference: data.reference,
    oldPrice: data.old_price,
    newPrice: data.new_price,
    timeRemaining: data.time_remaining,
    timestamp: data.timestamp || new Date().toISOString()
  });

  // Update badge
  const { unreadCount = 0 } = await chrome.storage.local.get('unreadCount');
  await updateBadge(unreadCount + 1);
  await chrome.storage.local.set({ unreadCount: unreadCount + 1 });

  // Show notification if enabled
  if (settings?.notificationsEnabled) {
    const priceChange = data.new_price - data.old_price;
    const changePercent = ((priceChange / data.old_price) * 100).toFixed(1);

    chrome.notifications.create(`price_${data.reference}_${Date.now()}`, {
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: `Alteracao de Preco - ${data.reference}`,
      message: `Novo lance: ${formatPrice(data.new_price)} (+${changePercent}%)\nRestam: ${data.time_remaining || 'N/A'}`,
      priority: 2
    });
  }
}

// Handle event ended
async function handleEventEnded(data) {
  const { settings } = await chrome.storage.sync.get('settings');

  // Store notification
  await storeNotification({
    type: 'event_ended',
    reference: data.reference,
    finalPrice: data.final_price,
    timestamp: data.timestamp || new Date().toISOString()
  });

  // Update badge
  const { unreadCount = 0 } = await chrome.storage.local.get('unreadCount');
  await updateBadge(unreadCount + 1);
  await chrome.storage.local.set({ unreadCount: unreadCount + 1 });

  // Show notification if enabled
  if (settings?.notificationsEnabled) {
    chrome.notifications.create(`ended_${data.reference}_${Date.now()}`, {
      type: 'basic',
      iconUrl: 'icons/icon128.png',
      title: `Leilao Terminado - ${data.reference}`,
      message: `Preco final: ${formatPrice(data.final_price)}`,
      priority: 1
    });
  }
}

// Store notification in local storage
async function storeNotification(notification) {
  const { notifications = [] } = await chrome.storage.local.get('notifications');
  notifications.unshift(notification);

  // Keep only last 100 notifications
  if (notifications.length > 100) {
    notifications.splice(100);
  }

  await chrome.storage.local.set({ notifications });
}

// Update badge
async function updateBadge(count) {
  const text = count > 0 ? (count > 99 ? '99+' : count.toString()) : '';
  await chrome.action.setBadgeText({ text });
  await chrome.action.setBadgeBackgroundColor({ color: count > 0 ? '#ef4444' : '#6b7280' });
}

// Broadcast connection status
function broadcastConnectionStatus(status, message = '') {
  chrome.runtime.sendMessage({
    type: 'connection_status',
    status,
    message
  }).catch(() => {}); // Ignore if no listeners
}

// Broadcast to content scripts
function broadcastToContentScripts(data) {
  chrome.tabs.query({ url: ['https://e-leiloes.pt/*', 'https://www.e-leiloes.pt/*'] }, (tabs) => {
    for (const tab of tabs) {
      chrome.tabs.sendMessage(tab.id, data).catch(() => {});
    }
  });

  // Also send to popup if open
  chrome.runtime.sendMessage(data).catch(() => {});
}

// Format price
function formatPrice(price) {
  if (typeof price !== 'number') return 'N/A';
  return new Intl.NumberFormat('pt-PT', {
    style: 'currency',
    currency: 'EUR'
  }).format(price);
}

// Message handlers
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    switch (message.type) {
      case 'connect':
        connectToSSE();
        sendResponse({ success: true });
        break;

      case 'disconnect':
        if (sseConnection) {
          sseConnection.close();
          sseConnection = null;
        }
        broadcastConnectionStatus('disconnected');
        sendResponse({ success: true });
        break;

      case 'get_status':
        sendResponse({
          connected: !!sseConnection,
          reconnectAttempts
        });
        break;

      case 'clear_badge':
        await updateBadge(0);
        await chrome.storage.local.set({ unreadCount: 0 });
        sendResponse({ success: true });
        break;

      case 'get_notifications':
        const { notifications = [] } = await chrome.storage.local.get('notifications');
        sendResponse({ notifications });
        break;

      case 'clear_notifications':
        await chrome.storage.local.set({ notifications: [], unreadCount: 0 });
        await updateBadge(0);
        sendResponse({ success: true });
        break;

      case 'add_favorite':
        await addFavorite(message.reference);
        sendResponse({ success: true });
        break;

      case 'remove_favorite':
        await removeFavorite(message.reference);
        sendResponse({ success: true });
        break;

      case 'get_favorites':
        const { favorites = [] } = await chrome.storage.sync.get('favorites');
        sendResponse({ favorites });
        break;

      default:
        sendResponse({ error: 'Unknown message type' });
    }
  })();
  return true; // Keep message channel open for async response
});

// Favorites management
async function addFavorite(reference) {
  const { favorites = [] } = await chrome.storage.sync.get('favorites');
  if (!favorites.includes(reference)) {
    favorites.push(reference);
    await chrome.storage.sync.set({ favorites });
  }
}

async function removeFavorite(reference) {
  const { favorites = [] } = await chrome.storage.sync.get('favorites');
  const index = favorites.indexOf(reference);
  if (index > -1) {
    favorites.splice(index, 1);
    await chrome.storage.sync.set({ favorites });
  }
}

// Handle notification clicks
chrome.notifications.onClicked.addListener(async (notificationId) => {
  // Extract reference from notification ID
  const match = notificationId.match(/^(price|ended)_([^_]+)_/);
  if (match) {
    const reference = match[2];
    // Open e-leiloes.pt page for this event
    chrome.tabs.create({
      url: `https://e-leiloes.pt/eventos/${reference}`
    });
  }
});

// Alarm for periodic sync (if needed)
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'sync_check') {
    // Check connection and reconnect if needed
    const { settings } = await chrome.storage.sync.get('settings');
    if (settings?.autoConnect && !sseConnection) {
      connectToSSE();
    }
  }
});

// Set up periodic check
chrome.alarms.create('sync_check', { periodInMinutes: 5 });
