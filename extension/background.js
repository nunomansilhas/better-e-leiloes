/**
 * Better E-Leilões - Background Service Worker
 * Handles extension lifecycle and messaging
 */

// Set default settings on install
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        chrome.storage.sync.set({
            apiUrl: 'http://localhost:8000',
            enableApiEnrichment: true,
            maxCarouselImages: 10
        });
        console.log('Better E-Leilões extension installed');
    }
});

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'getConfig') {
        chrome.storage.sync.get({
            apiUrl: 'http://localhost:8000',
            enableApiEnrichment: true,
            maxCarouselImages: 10
        }, (items) => {
            sendResponse(items);
        });
        return true; // Keep channel open for async response
    }
});

// Listen for tab updates to inject content script if needed
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        if (tab.url.includes('e-leiloes.pt')) {
            console.log('E-Leilões page loaded:', tab.url);
        }
    }
});
