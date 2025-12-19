// ==UserScript==
// @name         E-Leiloes Live Price Updates
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Live price updates from Better E-Leiloes backend via SSE
// @author       Better E-Leiloes
// @match        https://www.e-leiloes.pt/*
// @match        https://e-leiloes.pt/*
// @icon         https://www.e-leiloes.pt/favicon.ico
// @grant        GM_addStyle
// @grant        GM_notification
// ==/UserScript==

(function() {
    'use strict';

    // ============== CONFIGURATION ==============
    // Change this to your backend URL
    const BACKEND_URL = 'http://localhost:8000';
    const SSE_ENDPOINT = `${BACKEND_URL}/api/events/live`;

    // Enable/disable features
    const SHOW_NOTIFICATIONS = true;
    const SHOW_TOAST = true;
    const HIGHLIGHT_CHANGES = true;

    // ============== STYLES ==============
    GM_addStyle(`
        @keyframes eleiloes-price-flash {
            0% { background-color: #4ade80; transform: scale(1.05); }
            50% { background-color: #22c55e; }
            100% { background-color: transparent; transform: scale(1); }
        }

        @keyframes eleiloes-timer-flash {
            0% { background-color: #f59e0b; transform: scale(1.05); }
            50% { background-color: #d97706; }
            100% { background-color: transparent; transform: scale(1); }
        }

        .eleiloes-price-updated {
            animation: eleiloes-price-flash 2s ease-out;
            border-radius: 4px;
        }

        .eleiloes-timer-updated {
            animation: eleiloes-timer-flash 2s ease-out;
            border-radius: 4px;
        }

        .eleiloes-toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            color: white;
            padding: 16px 24px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            z-index: 99999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 400px;
            transform: translateX(120%);
            transition: transform 0.3s ease-out;
            border-left: 4px solid #22c55e;
        }

        .eleiloes-toast.show {
            transform: translateX(0);
        }

        .eleiloes-toast-title {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .eleiloes-toast-body {
            font-size: 13px;
            opacity: 0.9;
            line-height: 1.4;
        }

        .eleiloes-toast-price {
            font-weight: 700;
            color: #4ade80;
        }

        .eleiloes-toast-timer {
            font-weight: 600;
            color: #fbbf24;
        }

        .eleiloes-status-badge {
            position: fixed;
            top: 10px;
            right: 10px;
            background: #1e293b;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            z-index: 99998;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .eleiloes-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ef4444;
        }

        .eleiloes-status-dot.connected {
            background: #22c55e;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    `);

    // ============== STATE ==============
    let eventSource = null;
    let isConnected = false;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 10;

    // ============== UI ELEMENTS ==============
    function createStatusBadge() {
        const badge = document.createElement('div');
        badge.className = 'eleiloes-status-badge';
        badge.id = 'eleiloes-status';
        badge.innerHTML = `
            <span class="eleiloes-status-dot"></span>
            <span class="eleiloes-status-text">Connecting...</span>
        `;
        document.body.appendChild(badge);
        return badge;
    }

    function updateStatusBadge(connected, text) {
        const badge = document.getElementById('eleiloes-status');
        if (!badge) return;

        const dot = badge.querySelector('.eleiloes-status-dot');
        const textEl = badge.querySelector('.eleiloes-status-text');

        if (connected) {
            dot.classList.add('connected');
        } else {
            dot.classList.remove('connected');
        }
        textEl.textContent = text;
    }

    function showToast(data) {
        if (!SHOW_TOAST) return;

        // Remove existing toast
        const existing = document.getElementById('eleiloes-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'eleiloes-toast';
        toast.id = 'eleiloes-toast';

        const priceChange = data.new_price !== data.old_price;
        const timerReset = data.time_extended;

        let bodyHTML = '';
        if (priceChange) {
            bodyHTML += `<div>Price: <span class="eleiloes-toast-price">${formatPrice(data.old_price)} → ${formatPrice(data.new_price)}</span></div>`;
        }
        if (timerReset && data.new_end) {
            const newEnd = new Date(data.new_end);
            bodyHTML += `<div>Timer: <span class="eleiloes-toast-timer">Reset to ${formatDateTime(newEnd)}</span></div>`;
        }

        // Calculate remaining time with seconds precision
        const timeRemaining = data.new_end ? formatTimeRemaining(data.new_end) : data.time_remaining;

        toast.innerHTML = `
            <div class="eleiloes-toast-title">
                <span>💰</span>
                <span>${data.reference}</span>
            </div>
            <div class="eleiloes-toast-body">
                ${bodyHTML}
                <div style="margin-top: 4px; opacity: 0.7; font-size: 11px;">
                    ${timeRemaining} remaining
                </div>
            </div>
        `;

        document.body.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        // Auto remove
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    // ============== PRICE UPDATES ==============
    function findAndUpdatePrice(reference, newPrice, oldEnd, newEnd, timeExtended) {
        // Try to find the event card or detail page with this reference
        const refElements = document.querySelectorAll('span, div');

        for (const el of refElements) {
            if (el.textContent && el.textContent.trim() === reference) {
                // Found the reference, now find price element nearby
                const card = el.closest('.p-evento') || el.closest('.bg-white');
                if (card) {
                    updatePriceInCard(card, newPrice, newEnd, timeExtended);
                    return true;
                }
            }
        }

        // Check if we're on the event detail page
        if (window.location.pathname.includes(`/evento/${reference}`)) {
            updatePriceOnDetailPage(newPrice, newEnd, timeExtended);
            return true;
        }

        return false;
    }

    function updatePriceInCard(card, newPrice, newEnd, timeExtended) {
        // Find price elements (look for euro values)
        const allText = card.querySelectorAll('span, div');

        for (const el of allText) {
            const text = el.textContent || '';

            // Look for "Lance Atual" or price patterns
            if (text.includes('Lance Atual') || text.match(/[\d\s.]+,\d{2}\s*€/)) {
                // Find the actual price value
                const priceMatch = text.match(/([\d\s.]+,\d{2})\s*€/);
                if (priceMatch) {
                    const formattedPrice = formatPriceEuro(newPrice);
                    el.textContent = el.textContent.replace(priceMatch[0], formattedPrice);

                    if (HIGHLIGHT_CHANGES) {
                        el.classList.add('eleiloes-price-updated');
                        setTimeout(() => el.classList.remove('eleiloes-price-updated'), 2000);
                    }
                }
            }

            // Update timer if extended
            if (timeExtended && newEnd) {
                if (text.includes('Fim:') || text.match(/\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}/)) {
                    const dateMatch = text.match(/(\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2})/);
                    if (dateMatch) {
                        const newDateStr = formatDateTime(new Date(newEnd));
                        el.textContent = el.textContent.replace(dateMatch[0], newDateStr);

                        if (HIGHLIGHT_CHANGES) {
                            el.classList.add('eleiloes-timer-updated');
                            setTimeout(() => el.classList.remove('eleiloes-timer-updated'), 2000);
                        }
                    }
                }
            }
        }
    }

    function updatePriceOnDetailPage(newPrice, newEnd, timeExtended) {
        // On detail page, look for specific price elements
        const body = document.body;
        const bodyText = body.innerHTML;

        // Update Lance Atual
        const priceElements = document.querySelectorAll('span.font-semibold, div.font-semibold');
        for (const el of priceElements) {
            if (el.textContent && el.textContent.match(/[\d\s.]+,\d{2}\s*€/)) {
                const parent = el.parentElement;
                if (parent && parent.textContent.toLowerCase().includes('atual')) {
                    el.textContent = formatPriceEuro(newPrice);

                    if (HIGHLIGHT_CHANGES) {
                        el.classList.add('eleiloes-price-updated');
                        setTimeout(() => el.classList.remove('eleiloes-price-updated'), 2000);
                    }
                }
            }
        }

        // Update end time if extended
        if (timeExtended && newEnd) {
            const dateElements = document.querySelectorAll('span.font-semibold');
            for (const el of dateElements) {
                if (el.textContent && el.textContent.match(/\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}/)) {
                    const parent = el.parentElement;
                    if (parent && parent.textContent.toLowerCase().includes('fim')) {
                        el.textContent = formatDateTime(new Date(newEnd));

                        if (HIGHLIGHT_CHANGES) {
                            el.classList.add('eleiloes-timer-updated');
                            setTimeout(() => el.classList.remove('eleiloes-timer-updated'), 2000);
                        }
                    }
                }
            }
        }
    }

    // ============== UTILITIES ==============
    function formatPrice(value) {
        if (value === null || value === undefined) return 'N/A';
        return new Intl.NumberFormat('pt-PT', {
            style: 'currency',
            currency: 'EUR'
        }).format(value);
    }

    function formatPriceEuro(value) {
        if (value === null || value === undefined) return 'N/A';
        return new Intl.NumberFormat('pt-PT', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value) + ' €';
    }

    function formatDateTime(date) {
        const pad = n => n.toString().padStart(2, '0');
        return `${pad(date.getDate())}/${pad(date.getMonth() + 1)}/${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    }

    function formatTimeRemaining(endDate) {
        if (!endDate) return 'N/A';
        const now = new Date();
        const end = new Date(endDate);
        const diff = Math.max(0, end - now) / 1000; // seconds

        const hours = Math.floor(diff / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        const seconds = Math.floor(diff % 60);

        if (hours > 0) {
            return `${hours}h${minutes}m${seconds}s`;
        } else if (minutes > 0) {
            return `${minutes}m${seconds}s`;
        } else {
            return `${seconds}s`;
        }
    }

    // ============== SSE CONNECTION ==============
    function connect() {
        if (eventSource) {
            eventSource.close();
        }

        console.log('[E-Leiloes Live] Connecting to SSE...');
        updateStatusBadge(false, 'Connecting...');

        try {
            eventSource = new EventSource(SSE_ENDPOINT);

            eventSource.onopen = () => {
                console.log('[E-Leiloes Live] Connected!');
                isConnected = true;
                reconnectAttempts = 0;
                updateStatusBadge(true, 'Live');
            };

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[E-Leiloes Live] Update:', data);

                    if (data.type === 'price_update') {
                        handlePriceUpdate(data);
                    } else if (data.type === 'heartbeat') {
                        // Heartbeat received, connection is alive
                        updateStatusBadge(true, 'Live');
                    }
                } catch (e) {
                    console.error('[E-Leiloes Live] Parse error:', e);
                }
            };

            eventSource.onerror = (error) => {
                console.error('[E-Leiloes Live] Error:', error);
                isConnected = false;
                updateStatusBadge(false, 'Disconnected');

                eventSource.close();

                // Reconnect with exponential backoff
                if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                    reconnectAttempts++;
                    console.log(`[E-Leiloes Live] Reconnecting in ${delay/1000}s (attempt ${reconnectAttempts})`);
                    updateStatusBadge(false, `Retry ${reconnectAttempts}...`);
                    setTimeout(connect, delay);
                } else {
                    updateStatusBadge(false, 'Failed');
                }
            };

        } catch (e) {
            console.error('[E-Leiloes Live] Connection error:', e);
            updateStatusBadge(false, 'Error');
        }
    }

    function handlePriceUpdate(data) {
        // Show toast notification
        showToast(data);

        // Try to update price on page
        const updated = findAndUpdatePrice(
            data.reference,
            data.new_price,
            data.old_end,
            data.new_end,
            data.time_extended
        );

        // Show browser notification if enabled
        if (SHOW_NOTIFICATIONS && Notification.permission === 'granted') {
            const priceChange = data.new_price !== data.old_price;
            const body = priceChange
                ? `Price: ${formatPrice(data.old_price)} → ${formatPrice(data.new_price)}`
                : `Timer reset (${data.time_remaining} remaining)`;

            GM_notification({
                title: `E-Leiloes: ${data.reference}`,
                text: body,
                timeout: 5000
            });
        }
    }

    // ============== INIT ==============
    function init() {
        console.log('[E-Leiloes Live] Initializing...');

        // Create status badge
        createStatusBadge();

        // Request notification permission
        if (SHOW_NOTIFICATIONS && Notification.permission === 'default') {
            Notification.requestPermission();
        }

        // Connect to SSE
        connect();

        // Reconnect on visibility change (tab becomes active)
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && !isConnected) {
                reconnectAttempts = 0;
                connect();
            }
        });
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
