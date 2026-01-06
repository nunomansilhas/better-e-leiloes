/**
 * Better E-Leilões - Popup Script
 * Handles configuration and status display
 */

document.addEventListener('DOMContentLoaded', async () => {
    const apiUrlInput = document.getElementById('apiUrl');
    const enableApiCheckbox = document.getElementById('enableApi');
    const saveBtn = document.getElementById('saveBtn');
    const dashboardBtn = document.getElementById('dashboardBtn');
    const savedMsg = document.getElementById('savedMsg');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    // Load saved settings
    chrome.storage.sync.get({
        apiUrl: 'http://localhost:8000',
        enableApiEnrichment: true
    }, (items) => {
        apiUrlInput.value = items.apiUrl;
        enableApiCheckbox.checked = items.enableApiEnrichment;
        checkConnection(items.apiUrl);
    });

    // Check API connection
    async function checkConnection(url) {
        try {
            const response = await fetch(`${url}/api/health`, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });

            if (response.ok) {
                statusDot.classList.add('connected');
                statusText.classList.add('connected');
                statusText.textContent = 'Conectado ao Dashboard';
            } else {
                throw new Error('Not OK');
            }
        } catch (error) {
            statusDot.classList.remove('connected');
            statusText.classList.remove('connected');
            statusText.textContent = 'Dashboard não disponível';
        }
    }

    // Save settings
    saveBtn.addEventListener('click', () => {
        const apiUrl = apiUrlInput.value.trim().replace(/\/$/, ''); // Remove trailing slash
        const enableApiEnrichment = enableApiCheckbox.checked;

        chrome.storage.sync.set({
            apiUrl: apiUrl,
            enableApiEnrichment: enableApiEnrichment
        }, () => {
            // Show saved message
            savedMsg.classList.add('show');
            setTimeout(() => savedMsg.classList.remove('show'), 2000);

            // Re-check connection with new URL
            checkConnection(apiUrl);

            // Notify content scripts to reload config
            chrome.tabs.query({ url: ['*://e-leiloes.pt/*', '*://www.e-leiloes.pt/*'] }, (tabs) => {
                tabs.forEach(tab => {
                    chrome.tabs.sendMessage(tab.id, { action: 'reloadConfig' }).catch(() => {});
                });
            });
        });
    });

    // Open dashboard
    dashboardBtn.addEventListener('click', () => {
        const apiUrl = apiUrlInput.value.trim().replace(/\/$/, '');
        chrome.tabs.create({ url: apiUrl });
    });

    // Check connection when URL changes
    let debounceTimer;
    apiUrlInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            checkConnection(apiUrlInput.value.trim().replace(/\/$/, ''));
        }, 500);
    });
});
