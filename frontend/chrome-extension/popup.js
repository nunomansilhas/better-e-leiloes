// Better E-Leilões - Popup Script

const DEFAULT_CONFIG = {
    API_BASE: 'http://localhost:8000/api',
    DASHBOARD_URL: 'http://localhost:8000',
    ENABLE_API_ENRICHMENT: true,
    MAX_CAROUSEL_IMAGES: 10,
    API_TIMEOUT_GET: 3000,
    API_TIMEOUT_SCRAPE: 10000
};

// DOM Elements
const apiBaseInput = document.getElementById('apiBase');
const dashboardUrlInput = document.getElementById('dashboardUrl');
const enableApiCheckbox = document.getElementById('enableApi');
const maxImagesInput = document.getElementById('maxImages');
const timeoutGetInput = document.getElementById('timeoutGet');
const timeoutScrapeInput = document.getElementById('timeoutScrape');
const saveBtn = document.getElementById('saveBtn');
const openDashboardBtn = document.getElementById('openDashboard');
const statusDiv = document.getElementById('status');

// Load config from storage
function loadConfig() {
    chrome.storage.sync.get(['config'], (result) => {
        const config = result.config || DEFAULT_CONFIG;

        apiBaseInput.value = config.API_BASE || DEFAULT_CONFIG.API_BASE;
        dashboardUrlInput.value = config.DASHBOARD_URL || DEFAULT_CONFIG.DASHBOARD_URL;
        enableApiCheckbox.checked = config.ENABLE_API_ENRICHMENT !== false;
        maxImagesInput.value = config.MAX_CAROUSEL_IMAGES || DEFAULT_CONFIG.MAX_CAROUSEL_IMAGES;
        timeoutGetInput.value = config.API_TIMEOUT_GET || DEFAULT_CONFIG.API_TIMEOUT_GET;
        timeoutScrapeInput.value = config.API_TIMEOUT_SCRAPE || DEFAULT_CONFIG.API_TIMEOUT_SCRAPE;
    });
}

// Save config to storage
function saveConfig() {
    const config = {
        API_BASE: apiBaseInput.value.trim() || DEFAULT_CONFIG.API_BASE,
        DASHBOARD_URL: dashboardUrlInput.value.trim() || DEFAULT_CONFIG.DASHBOARD_URL,
        ENABLE_API_ENRICHMENT: enableApiCheckbox.checked,
        MAX_CAROUSEL_IMAGES: parseInt(maxImagesInput.value) || DEFAULT_CONFIG.MAX_CAROUSEL_IMAGES,
        API_TIMEOUT_GET: parseInt(timeoutGetInput.value) || DEFAULT_CONFIG.API_TIMEOUT_GET,
        API_TIMEOUT_SCRAPE: parseInt(timeoutScrapeInput.value) || DEFAULT_CONFIG.API_TIMEOUT_SCRAPE
    };

    chrome.storage.sync.set({ config }, () => {
        // Show success message
        statusDiv.classList.add('show');
        setTimeout(() => {
            statusDiv.classList.remove('show');
        }, 2000);

        // Notify content scripts to reload config
        chrome.tabs.query({ url: ['*://e-leiloes.pt/*', '*://www.e-leiloes.pt/*'] }, (tabs) => {
            tabs.forEach(tab => {
                chrome.tabs.sendMessage(tab.id, { action: 'reloadConfig' }).catch(() => {
                    // Tab might not have content script loaded yet
                });
            });
        });
    });
}

// Open dashboard in new tab
function openDashboard() {
    const dashboardUrl = dashboardUrlInput.value.trim() || DEFAULT_CONFIG.DASHBOARD_URL;
    chrome.tabs.create({ url: dashboardUrl });
}

// Event listeners
saveBtn.addEventListener('click', saveConfig);
openDashboardBtn.addEventListener('click', openDashboard);

// Load config on popup open
loadConfig();
