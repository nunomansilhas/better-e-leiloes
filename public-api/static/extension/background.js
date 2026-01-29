// Better E-Leiloes - Background Service Worker

// Set default settings on install
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        chrome.storage.sync.set({
            apiBase: 'https://martelo.pt/api',
            dashboardUrl: 'https://martelo.pt/dashboard.html',
            enableEnrichment: true
        });
        console.log('Better E-Leiloes: Default settings initialized');
    }
});

// Handle messages from content script or popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'getSettings') {
        chrome.storage.sync.get(['apiBase', 'dashboardUrl', 'enableEnrichment'], (result) => {
            sendResponse(result);
        });
        return true; // Keep message channel open for async response
    }

    if (message.action === 'openDashboard') {
        chrome.storage.sync.get(['dashboardUrl'], (result) => {
            const dashboardUrl = result.dashboardUrl || 'https://martelo.pt/dashboard.html';
            chrome.tabs.create({ url: dashboardUrl });
        });
    }
});

// Update badge when on e-leiloes.pt
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        if (tab.url.includes('e-leiloes.pt')) {
            chrome.action.setBadgeText({ tabId, text: 'ON' });
            chrome.action.setBadgeBackgroundColor({ tabId, color: '#22c55e' });
        } else {
            chrome.action.setBadgeText({ tabId, text: '' });
        }
    }
});
