// Better E-Leilões - Background Service Worker
// Handles API requests and settings storage

const DEFAULT_CONFIG = {
    API_BASE: 'http://localhost:8000/api',
    DASHBOARD_URL: 'http://localhost:8000',
    ENABLE_API_ENRICHMENT: true,
    MAX_CAROUSEL_IMAGES: 10,
    API_TIMEOUT_GET: 3000,
    API_TIMEOUT_SCRAPE: 10000
};

// Initialize config on install
chrome.runtime.onInstalled.addListener(() => {
    chrome.storage.sync.get(['config'], (result) => {
        if (!result.config) {
            chrome.storage.sync.set({ config: DEFAULT_CONFIG });
        }
    });
    console.log('🚀 Better E-Leilões extension installed');
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getConfig') {
        chrome.storage.sync.get(['config'], (result) => {
            sendResponse(result.config || DEFAULT_CONFIG);
        });
        return true; // Keep channel open for async response
    }

    if (request.action === 'saveConfig') {
        chrome.storage.sync.set({ config: request.config }, () => {
            sendResponse({ success: true });
        });
        return true;
    }

    if (request.action === 'apiRequest') {
        handleApiRequest(request)
            .then(response => sendResponse(response))
            .catch(error => sendResponse({ error: error.message }));
        return true;
    }
});

// API request handler with timeout
async function handleApiRequest(request) {
    const { url, method = 'GET', timeout = 3000 } = request;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            method,
            headers: {
                'Accept': 'application/json'
            },
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (response.status === 404) {
            return { _notFound: true };
        }

        if (!response.ok) {
            return { error: `HTTP ${response.status}` };
        }

        const data = await response.json();
        return data;
    } catch (error) {
        clearTimeout(timeoutId);

        if (error.name === 'AbortError') {
            console.error(`❌ API timeout for ${url}`);
            return { error: 'timeout' };
        }

        console.error(`❌ API error for ${url}:`, error);
        return { error: error.message };
    }
}
