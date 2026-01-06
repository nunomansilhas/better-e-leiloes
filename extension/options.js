/**
 * E-Leiloes Dashboard - Options Script
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
  backendUrl: document.getElementById('backendUrl'),
  notificationsEnabled: document.getElementById('notificationsEnabled'),
  soundEnabled: document.getElementById('soundEnabled'),
  autoConnect: document.getElementById('autoConnect'),
  connectionDot: document.getElementById('connectionDot'),
  connectionText: document.getElementById('connectionText'),
  btnTestConnection: document.getElementById('btnTestConnection'),
  btnSave: document.getElementById('btnSave'),
  btnReset: document.getElementById('btnReset'),
  btnExportData: document.getElementById('btnExportData'),
  btnClearData: document.getElementById('btnClearData'),
  toast: document.getElementById('toast')
};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  setupEventListeners();
});

// Load settings
async function loadSettings() {
  const { settings = DEFAULT_SETTINGS } = await chrome.storage.sync.get('settings');

  elements.backendUrl.value = settings.backendUrl || DEFAULT_SETTINGS.backendUrl;
  elements.notificationsEnabled.checked = settings.notificationsEnabled ?? DEFAULT_SETTINGS.notificationsEnabled;
  elements.soundEnabled.checked = settings.soundEnabled ?? DEFAULT_SETTINGS.soundEnabled;
  elements.autoConnect.checked = settings.autoConnect ?? DEFAULT_SETTINGS.autoConnect;
}

// Save settings
async function saveSettings() {
  const settings = {
    backendUrl: elements.backendUrl.value.trim() || DEFAULT_SETTINGS.backendUrl,
    notificationsEnabled: elements.notificationsEnabled.checked,
    soundEnabled: elements.soundEnabled.checked,
    autoConnect: elements.autoConnect.checked
  };

  // Remove trailing slash
  settings.backendUrl = settings.backendUrl.replace(/\/$/, '');

  await chrome.storage.sync.set({ settings });
  showToast('Definicoes guardadas!', 'success');

  // Notify background script
  chrome.runtime.sendMessage({ type: 'settings_updated', settings });
}

// Reset settings
async function resetSettings() {
  await chrome.storage.sync.set({ settings: DEFAULT_SETTINGS });
  await loadSettings();
  showToast('Definicoes repostas', 'success');
}

// Test connection
async function testConnection() {
  const url = elements.backendUrl.value.trim() || DEFAULT_SETTINGS.backendUrl;

  elements.connectionDot.className = 'connection-dot testing';
  elements.connectionText.textContent = 'A testar...';
  elements.btnTestConnection.disabled = true;

  try {
    const response = await fetch(`${url}/health`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });

    if (response.ok) {
      const data = await response.json();
      elements.connectionDot.className = 'connection-dot success';
      elements.connectionText.textContent = `Conectado - ${data.service || 'API'} v${data.version || '?'}`;
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  } catch (error) {
    elements.connectionDot.className = 'connection-dot error';
    elements.connectionText.textContent = `Erro: ${error.message}`;
  }

  elements.btnTestConnection.disabled = false;
}

// Export data
async function exportData() {
  const { settings } = await chrome.storage.sync.get('settings');
  const { notifications, favorites } = await chrome.storage.local.get(['notifications', 'favorites']);
  const { favorites: syncFavorites } = await chrome.storage.sync.get('favorites');

  const data = {
    settings,
    notifications: notifications || [],
    favorites: favorites || syncFavorites || [],
    exportedAt: new Date().toISOString()
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `e-leiloes-dashboard-backup-${new Date().toISOString().split('T')[0]}.json`;
  a.click();

  URL.revokeObjectURL(url);
  showToast('Dados exportados!', 'success');
}

// Clear data
async function clearData() {
  if (!confirm('Tem a certeza que quer limpar todos os dados? Esta acao nao pode ser revertida.')) {
    return;
  }

  await chrome.storage.local.clear();
  await chrome.storage.sync.remove(['favorites']);
  await chrome.runtime.sendMessage({ type: 'clear_badge' });

  showToast('Dados limpos!', 'success');
}

// Show toast notification
function showToast(message, type = 'info') {
  elements.toast.textContent = message;
  elements.toast.className = `toast visible ${type}`;

  setTimeout(() => {
    elements.toast.className = 'toast';
  }, 3000);
}

// Setup event listeners
function setupEventListeners() {
  elements.btnSave.addEventListener('click', saveSettings);
  elements.btnReset.addEventListener('click', resetSettings);
  elements.btnTestConnection.addEventListener('click', testConnection);
  elements.btnExportData.addEventListener('click', exportData);
  elements.btnClearData.addEventListener('click', clearData);

  // Auto-save on toggle change
  [elements.notificationsEnabled, elements.soundEnabled, elements.autoConnect].forEach(el => {
    el.addEventListener('change', () => {
      saveSettings();
    });
  });

  // Test connection on URL change (with debounce)
  let debounceTimer;
  elements.backendUrl.addEventListener('input', () => {
    elements.connectionDot.className = 'connection-dot';
    elements.connectionText.textContent = 'Nao testado';

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (elements.backendUrl.value.trim()) {
        testConnection();
      }
    }, 1000);
  });
}
