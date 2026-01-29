// Better E-Leiloes - Popup Script

document.addEventListener('DOMContentLoaded', () => {
    const toggleEnrichment = document.getElementById('toggle-enrichment');
    const apiBaseInput = document.getElementById('api-base');
    const dashboardUrlInput = document.getElementById('dashboard-url');
    const btnDashboard = document.getElementById('btn-dashboard');
    const btnSave = document.getElementById('btn-save');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');

    // Load saved settings
    chrome.storage.sync.get(['apiBase', 'dashboardUrl', 'enableEnrichment'], (result) => {
        apiBaseInput.value = result.apiBase || 'https://martelo.pt/api';
        dashboardUrlInput.value = result.dashboardUrl || 'https://martelo.pt/dashboard.html';

        const enrichmentEnabled = result.enableEnrichment !== false;
        toggleEnrichment.classList.toggle('active', enrichmentEnabled);
    });

    // Check if on e-leiloes.pt
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const url = tabs[0]?.url || '';
        const isOnEleiloes = url.includes('e-leiloes.pt');

        if (isOnEleiloes) {
            statusDot.classList.remove('inactive');
            statusText.textContent = 'Extensão ativa nesta página';
        } else {
            statusDot.classList.add('inactive');
            statusText.textContent = 'Visita e-leiloes.pt para usar';
        }
    });

    // Toggle enrichment
    toggleEnrichment.addEventListener('click', () => {
        toggleEnrichment.classList.toggle('active');
    });

    // Open dashboard
    btnDashboard.addEventListener('click', () => {
        const dashboardUrl = dashboardUrlInput.value || 'https://martelo.pt/dashboard.html';
        chrome.tabs.create({ url: dashboardUrl });
    });

    // Save settings
    btnSave.addEventListener('click', () => {
        const settings = {
            apiBase: apiBaseInput.value.trim() || 'https://martelo.pt/api',
            dashboardUrl: dashboardUrlInput.value.trim() || 'https://martelo.pt/dashboard.html',
            enableEnrichment: toggleEnrichment.classList.contains('active')
        };

        chrome.storage.sync.set(settings, () => {
            // Show feedback
            btnSave.textContent = 'Guardado!';
            btnSave.style.background = '#22c55e';

            setTimeout(() => {
                btnSave.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                        <polyline points="17 21 17 13 7 13 7 21"></polyline>
                        <polyline points="7 3 7 8 15 8"></polyline>
                    </svg>
                    Guardar Configurações
                `;
                btnSave.style.background = '';
            }, 1500);

            // Notify content script to reload settings
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                if (tabs[0]) {
                    chrome.tabs.sendMessage(tabs[0].id, { action: 'reloadSettings' }).catch(() => {});
                }
            });
        });
    });
});
