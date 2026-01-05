// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      9.1
// @description  Design moderno com altura fixa, badges, favoritos e melhor UX
// @author       Nuno Mansilhas
// @match        https://e-leiloes.pt/*
// @match        https://www.e-leiloes.pt/*
// @match        http://e-leiloes.pt/*
// @match        http://www.e-leiloes.pt/*
// @icon         https://www.e-leiloes.pt/favicon.ico
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      localhost
// @connect      127.0.0.1
// @updateURL    https://raw.githubusercontent.com/nunomansilhas/better-e-leiloes/main/betterE-Leiloes-CardEnhancer.user.js
// @downloadURL  https://raw.githubusercontent.com/nunomansilhas/better-e-leiloes/main/betterE-Leiloes-CardEnhancer.user.js
// ==/UserScript==

(function() {
    'use strict';

    // ====================================
    // CONFIGURAÇÃO
    // ====================================

    const CONFIG = {
        API_BASE: 'http://localhost:8000/api',
        DASHBOARD_URL: 'http://localhost:8000',
        ENABLE_API_ENRICHMENT: true,
        MAX_CAROUSEL_IMAGES: 10,
        CARD_HEIGHT: 420  // Fixed card height in pixels
    };

    // Favorites storage
    let favorites = [];
    try {
        favorites = JSON.parse(GM_getValue('favorites', '[]'));
    } catch (e) {
        favorites = [];
    }

    function saveFavorites() {
        GM_setValue('favorites', JSON.stringify(favorites));
    }

    function toggleFavorite(reference) {
        const idx = favorites.indexOf(reference);
        if (idx > -1) {
            favorites.splice(idx, 1);
        } else {
            favorites.push(reference);
        }
        saveFavorites();
        return favorites.includes(reference);
    }

    // ====================================
    // ESTILOS CSS - v9.0 REDESIGN
    // ====================================

    const styles = document.createElement('style');
    styles.textContent = `
        /* ============================================ */
        /* v9.0 - FIXED HEIGHT CARDS                   */
        /* ============================================ */

        .p-evento {
            transition: all 0.3s ease !important;
            overflow: hidden !important;
        }

        .p-evento:hover {
            transform: translateY(-4px) !important;
        }

        .p-evento[data-better-enhanced="true"] {
            height: ${CONFIG.CARD_HEIGHT}px !important;
            min-height: ${CONFIG.CARD_HEIGHT}px !important;
            max-height: ${CONFIG.CARD_HEIGHT}px !important;
            border-radius: 16px !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
            background: white !important;
            position: relative !important;
            display: flex !important;
            flex-direction: column !important;
        }

        .p-evento[data-better-enhanced="true"]:hover {
            box-shadow: 0 12px 40px rgba(0,0,0,0.12) !important;
            border-color: #3b82f6 !important;
        }

        /* Hide native elements we replace */
        .p-evento[data-better-enhanced="true"] .surface-100.border-round-bottom,
        .p-evento[data-better-enhanced="true"] .p-tag.p-component {
            display: none !important;
        }

        .p-evento[data-better-enhanced="true"] .w-full {
            border: none !important;
            border-radius: 0 !important;
        }

        /* Padroniza fontes */
        .p-evento[data-better-enhanced="true"],
        .p-evento[data-better-enhanced="true"] *:not([class*="pi-"]):not(i) {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* Hide context menu */
        .p-contextmenu.p-component {
            display: none !important;
        }

        /* Fix links */
        .p-evento a[href*="/evento/"] {
            pointer-events: none !important;
        }

        /* ============================================ */
        /* TITLE - 2 LINES WITH ELLIPSIS               */
        /* ============================================ */

        .p-evento[data-better-enhanced="true"] .better-title {
            font-size: 14px !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
            color: #1f2937 !important;
            display: -webkit-box !important;
            -webkit-line-clamp: 2 !important;
            -webkit-box-orient: vertical !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            height: 36px !important;
            margin: 0 !important;
            padding: 8px 12px 4px 12px !important;
        }

        /* ============================================ */
        /* LOCATION - BETTER VISIBILITY                */
        /* ============================================ */

        .better-location {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px 8px 12px;
            font-size: 13px !important;
            color: #6b7280;
        }

        .better-location .pi-map-marker {
            color: #3b82f6 !important;
            font-size: 14px !important;
        }

        .better-location-text {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }

        /* ============================================ */
        /* TYPE BADGE - COLORED                        */
        /* ============================================ */

        .better-type-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .better-type-badge.imoveis { background: #dbeafe; color: #1d4ed8; }
        .better-type-badge.veiculos { background: #fef3c7; color: #b45309; }
        .better-type-badge.equipamentos { background: #d1fae5; color: #047857; }
        .better-type-badge.direitos { background: #ede9fe; color: #6d28d9; }
        .better-type-badge.outros { background: #f3f4f6; color: #4b5563; }

        /* ============================================ */
        /* URGENCY BADGES                              */
        /* ============================================ */

        .better-badges {
            position: absolute;
            top: 8px;
            left: 8px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            z-index: 15;
        }

        .better-badge {
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }

        .better-badge.new {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
        }

        .better-badge.ending {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            animation: pulse-badge 1.5s infinite;
        }

        .better-badge.ending-soon {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
        }

        @keyframes pulse-badge {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.9; transform: scale(1.02); }
        }

        /* ============================================ */
        /* ACTION BUTTONS (Refresh, Sync, Favorite)    */
        /* ============================================ */

        .better-action-buttons {
            position: absolute;
            top: 8px;
            right: 8px;
            display: flex;
            gap: 4px;
            z-index: 15;
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        .p-evento:hover .better-action-buttons {
            opacity: 1;
        }

        .better-action-btn {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }

        .better-action-btn.refresh {
            background: #3b82f6;
            color: white;
        }

        .better-action-btn.refresh:hover {
            background: #2563eb;
            transform: scale(1.1);
        }

        .better-action-btn.sync {
            background: #10b981;
            color: white;
        }

        .better-action-btn.sync:hover {
            background: #059669;
            transform: scale(1.1);
        }

        .better-action-btn.favorite {
            background: white;
            color: #d1d5db;
        }

        .better-action-btn.favorite:hover {
            color: #ef4444;
            transform: scale(1.1);
        }

        .better-action-btn.favorite.active {
            background: #fef2f2;
            color: #ef4444;
        }

        .better-action-btn.loading {
            pointer-events: none;
            opacity: 0.7;
        }

        .better-action-btn.loading::after {
            content: '';
            width: 14px;
            height: 14px;
            border: 2px solid transparent;
            border-top-color: currentColor;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* ============================================ */
        /* CAROUSEL                                    */
        /* ============================================ */

        .better-carousel {
            position: relative;
            width: calc(100% - 16px);
            height: 150px;
            overflow: hidden;
            background: linear-gradient(135deg, #f8fafc, #e2e8f0);
            border-radius: 12px;
            margin: 8px;
            flex-shrink: 0;
        }

        .better-carousel-track {
            display: flex;
            transition: transform 0.3s ease;
            height: 100%;
        }

        .better-carousel-slide {
            min-width: 100%;
            height: 100%;
            background-size: cover;
            background-position: center;
            cursor: zoom-in;
        }

        .better-carousel-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(0, 0, 0, 0.6);
            color: white;
            border: none;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 16px;
            z-index: 5;
            opacity: 0;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .better-carousel:hover .better-carousel-nav {
            opacity: 1;
        }

        .better-carousel-nav:hover {
            background: rgba(0, 0, 0, 0.8);
            transform: translateY(-50%) scale(1.1);
        }

        .better-carousel-nav.prev { left: 8px; }
        .better-carousel-nav.next { right: 8px; }

        .better-carousel-dots {
            position: absolute;
            bottom: 8px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 5px;
            z-index: 5;
        }

        .better-carousel-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            cursor: pointer;
            transition: all 0.2s ease;
            border: 1px solid rgba(0,0,0,0.2);
        }

        .better-carousel-dot:hover {
            background: rgba(255, 255, 255, 0.8);
        }

        .better-carousel-dot.active {
            background: white;
            width: 20px;
            border-radius: 4px;
        }

        .better-carousel-counter {
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            z-index: 5;
        }

        /* ============================================ */
        /* TIME OVERLAY ON IMAGE (when < 24h)          */
        /* ============================================ */

        .better-time-overlay {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(transparent, rgba(0,0,0,0.8));
            padding: 20px 12px 10px 12px;
            z-index: 4;
        }

        .better-time-overlay-content {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            color: white;
            font-size: 14px;
            font-weight: 700;
        }

        .better-time-overlay-icon {
            font-size: 18px;
        }

        .better-time-overlay.critical .better-time-overlay-content {
            color: #fca5a5;
        }

        /* ============================================ */
        /* CARD BODY                                   */
        /* ============================================ */

        .better-card-body {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .better-meta-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 6px 12px;
            gap: 8px;
        }

        /* ============================================ */
        /* VALUES ROW                                  */
        /* ============================================ */

        .better-valores-row {
            display: flex;
            justify-content: center;
            gap: 6px;
            padding: 8px 12px;
            background: #f9fafb;
            border-top: 1px solid #f3f4f6;
        }

        .better-valor-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 6px 12px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            min-width: 70px;
        }

        .better-valor-label {
            font-size: 9px;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .better-valor-amount {
            font-size: 12px;
            font-weight: 700;
            color: #1f2937;
        }

        /* ============================================ */
        /* LANCE CTA BUTTON - HIGHLIGHTED              */
        /* ============================================ */

        .better-lance-cta {
            margin: 8px 12px;
            padding: 12px 20px;
            background: linear-gradient(135deg, #fbbf24, #f59e0b) !important;
            border: none !important;
            border-radius: 12px !important;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        }

        .better-lance-cta:hover {
            background: linear-gradient(135deg, #f59e0b, #d97706) !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(245, 158, 11, 0.4);
        }

        .better-lance-cta .lance-label {
            font-size: 11px;
            font-weight: 600;
            color: rgba(0,0,0,0.6);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .better-lance-cta .lance-value {
            font-size: 18px;
            font-weight: 800;
            color: #1f2937;
        }

        .better-lance-cta .lance-icon {
            font-size: 20px;
        }

        /* With bids indicator */
        .better-lance-cta.has-bids {
            background: linear-gradient(135deg, #22c55e, #16a34a) !important;
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);
        }

        .better-lance-cta.has-bids:hover {
            background: linear-gradient(135deg, #16a34a, #15803d) !important;
            box-shadow: 0 6px 16px rgba(34, 197, 94, 0.4);
        }

        .better-lance-cta.has-bids .lance-value {
            color: white;
        }

        .better-lance-cta.has-bids .lance-label {
            color: rgba(255,255,255,0.8);
        }

        .better-bids-count {
            background: rgba(255,255,255,0.3);
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 700;
            color: white;
        }

        /* ============================================ */
        /* COUNTDOWN ROW - IMPROVED                    */
        /* ============================================ */

        .better-countdown-row {
            padding: 10px 12px;
            background: #1f2937;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: auto;
            border-radius: 0 0 16px 16px;
        }

        .better-countdown-icon {
            font-size: 16px;
        }

        .better-countdown-text {
            font-size: 12px;
            font-weight: 500;
            color: #9ca3af;
        }

        .better-countdown-time {
            font-size: 14px;
            font-weight: 700;
            color: white;
        }

        .better-countdown-time.ending-soon {
            color: #fbbf24;
            animation: pulse-text 1.5s infinite;
        }

        .better-countdown-time.critical {
            color: #ef4444;
            animation: pulse-text 0.8s infinite;
        }

        @keyframes pulse-text {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }

        /* ============================================ */
        /* MAP MARKER                                  */
        /* ============================================ */

        .p-evento[data-better-enhanced="true"] .pi-map-marker.better-map-link {
            color: #3b82f6 !important;
            cursor: pointer !important;
            pointer-events: auto !important;
            transition: all 0.2s ease !important;
        }

        .p-evento[data-better-enhanced="true"] .pi-map-marker.better-map-link:hover {
            transform: scale(1.2) !important;
            color: #2563eb !important;
        }

        /* ============================================ */
        /* LIGHTBOX                                    */
        /* ============================================ */

        .better-lightbox {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.95);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .better-lightbox.active {
            opacity: 1;
        }

        .better-lightbox-img {
            max-width: 90vw;
            max-height: 90vh;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        }

        .better-lightbox-close {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 44px;
            height: 44px;
            background: rgba(255, 255, 255, 0.15);
            border: none;
            border-radius: 50%;
            color: white;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .better-lightbox-close:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: scale(1.1);
        }

        .better-lightbox-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: rgba(255, 255, 255, 0.15);
            border: none;
            border-radius: 50%;
            color: white;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .better-lightbox-nav:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-50%) scale(1.1);
        }

        .better-lightbox-nav.prev { left: 20px; }
        .better-lightbox-nav.next { right: 20px; }

        .better-lightbox-counter {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            color: white;
            font-size: 14px;
            background: rgba(0, 0, 0, 0.6);
            padding: 8px 20px;
            border-radius: 20px;
        }

        /* ============================================ */
        /* DASHBOARD BUTTON                            */
        /* ============================================ */

        .better-dashboard-btn {
            background: #3b82f6 !important;
            border-color: #3b82f6 !important;
        }

        .better-dashboard-btn:hover {
            background: #2563eb !important;
            transform: scale(1.05) !important;
        }

        /* ============================================ */
        /* REFERENCE PREFIX COLORS                     */
        /* ============================================ */

        .native-ref-prefix.lo { color: #3b82f6 !important; font-weight: 700; }
        .native-ref-prefix.np { color: #f59e0b !important; font-weight: 700; }
    `;
    document.head.appendChild(styles);

    // ====================================
    // UTILITÁRIOS
    // ====================================

    function formatCurrency(value) {
        if (!value && value !== 0) return '-';
        const num = parseFloat(value);
        return new Intl.NumberFormat('pt-PT', {
            maximumFractionDigits: 0
        }).format(num) + ' €';
    }

    function calculateTimeRemaining(endDate) {
        if (!endDate) return null;

        const now = new Date();
        const end = new Date(endDate);
        const diff = end - now;

        if (diff <= 0) return { text: 'Terminado', isEnding: false, isCritical: false, hours: 0 };

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        const totalHours = diff / (1000 * 60 * 60);
        const isEnding = totalHours < 24;
        const isCritical = totalHours < 1;

        let text = '';
        if (days > 0) {
            text = `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            text = `${hours}h ${minutes}m ${seconds}s`;
        } else if (minutes > 0) {
            text = `${minutes}m ${seconds}s`;
        } else {
            text = `${seconds}s`;
        }

        return { text, isEnding, isCritical, hours: totalHours };
    }

    function getTypeClass(tipo, tipoId) {
        const tipoLower = (tipo || '').toLowerCase();
        if (tipoId === 1 || tipoLower.includes('imov') || tipoLower.includes('apart') || tipoLower.includes('morad')) return 'imoveis';
        if (tipoId === 2 || tipoLower.includes('veic') || tipoLower.includes('auto')) return 'veiculos';
        if (tipoId === 3 || tipoLower.includes('equip')) return 'equipamentos';
        if (tipoId === 6 || tipoLower.includes('direit')) return 'direitos';
        return 'outros';
    }

    function getTypeLabel(tipo, tipoId) {
        const typeClass = getTypeClass(tipo, tipoId);
        const labels = {
            'imoveis': '🏠 Imóvel',
            'veiculos': '🚗 Veículo',
            'equipamentos': '⚙️ Equipamento',
            'direitos': '📜 Direito',
            'outros': '📦 Outro'
        };
        return labels[typeClass] || labels['outros'];
    }

    // ====================================
    // API
    // ====================================

    function getEventFromAPI(reference) {
        if (!CONFIG.ENABLE_API_ENRICHMENT) return Promise.resolve(null);

        return new Promise((resolve) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url: `${CONFIG.API_BASE}/events/${reference}`,
                headers: { 'Accept': 'application/json' },
                onload: function(response) {
                    if (response.status === 200) {
                        try {
                            resolve(JSON.parse(response.responseText));
                        } catch (e) {
                            resolve(null);
                        }
                    } else if (response.status === 404) {
                        resolve({ _notFound: true });
                    } else {
                        resolve(null);
                    }
                },
                onerror: () => resolve(null),
                ontimeout: () => resolve(null)
            });
        });
    }

    function triggerScrape(reference) {
        return new Promise((resolve) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: `${CONFIG.API_BASE}/scrape/event/${reference}`,
                headers: { 'Accept': 'application/json' },
                onload: (response) => resolve(response.status === 200 || response.status === 202),
                onerror: () => resolve(false)
            });
        });
    }

    // ====================================
    // LIGHTBOX
    // ====================================

    let lightboxImages = [];
    let lightboxIndex = 0;

    function openLightbox(images, startIndex = 0) {
        lightboxImages = images;
        lightboxIndex = startIndex;

        const lightbox = document.createElement('div');
        lightbox.className = 'better-lightbox';
        lightbox.id = 'better-lightbox';
        lightbox.innerHTML = `
            <button class="better-lightbox-close">×</button>
            <button class="better-lightbox-nav prev">‹</button>
            <img class="better-lightbox-img" src="${images[startIndex]}">
            <button class="better-lightbox-nav next">›</button>
            <div class="better-lightbox-counter">${startIndex + 1} / ${images.length}</div>
        `;

        document.body.appendChild(lightbox);
        setTimeout(() => lightbox.classList.add('active'), 10);

        const img = lightbox.querySelector('.better-lightbox-img');
        const counter = lightbox.querySelector('.better-lightbox-counter');

        function updateLightbox() {
            img.src = lightboxImages[lightboxIndex];
            counter.textContent = `${lightboxIndex + 1} / ${lightboxImages.length}`;
        }

        lightbox.querySelector('.better-lightbox-close').addEventListener('click', closeLightbox);
        lightbox.querySelector('.better-lightbox-nav.prev').addEventListener('click', () => {
            lightboxIndex = (lightboxIndex - 1 + lightboxImages.length) % lightboxImages.length;
            updateLightbox();
        });
        lightbox.querySelector('.better-lightbox-nav.next').addEventListener('click', () => {
            lightboxIndex = (lightboxIndex + 1) % lightboxImages.length;
            updateLightbox();
        });

        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) closeLightbox();
        });

        document.addEventListener('keydown', handleLightboxKeys);
    }

    function closeLightbox() {
        const lightbox = document.getElementById('better-lightbox');
        if (lightbox) {
            lightbox.classList.remove('active');
            setTimeout(() => lightbox.remove(), 300);
        }
        document.removeEventListener('keydown', handleLightboxKeys);
    }

    function handleLightboxKeys(e) {
        if (e.key === 'Escape') closeLightbox();
        const img = document.querySelector('.better-lightbox-img');
        const counter = document.querySelector('.better-lightbox-counter');
        if (e.key === 'ArrowLeft') {
            lightboxIndex = (lightboxIndex - 1 + lightboxImages.length) % lightboxImages.length;
            if (img && counter) { img.src = lightboxImages[lightboxIndex]; counter.textContent = `${lightboxIndex + 1} / ${lightboxImages.length}`; }
        }
        if (e.key === 'ArrowRight') {
            lightboxIndex = (lightboxIndex + 1) % lightboxImages.length;
            if (img && counter) { img.src = lightboxImages[lightboxIndex]; counter.textContent = `${lightboxIndex + 1} / ${lightboxImages.length}`; }
        }
    }

    // ====================================
    // FLOATING BUTTON
    // ====================================

    function integrateWithNativeFloatingButtons() {
        if (document.querySelector('.better-dashboard-btn')) return;

        const btn = document.createElement('button');
        btn.className = 'p-button p-component p-button-icon-only p-button-base fixed fadein animation-duration-400 right-0 z-999 better-dashboard-btn';
        btn.type = 'button';
        btn.title = 'Better E-Leilões Dashboard';
        btn.style.cssText = 'margin-right: 5px; bottom: 137px; background: #3b82f6; border-color: #3b82f6;';
        btn.innerHTML = `<span class="p-button-icon pi pi-home"></span><span class="p-button-label">&nbsp;</span>`;

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            window.open(CONFIG.DASHBOARD_URL, '_blank');
        });

        document.body.appendChild(btn);
    }

    // ====================================
    // CARD ENHANCEMENT
    // ====================================

    function extractReferenceFromCard(card) {
        const refElement = card.querySelector('.pi-tag + span');
        return refElement ? refElement.textContent.trim() : null;
    }

    async function enhanceCard(card) {
        if (card.dataset.betterEnhanced) return;
        card.dataset.betterEnhanced = 'true';

        const reference = extractReferenceFromCard(card);
        if (!reference) return;

        try {
            const apiData = await getEventFromAPI(reference);

            // If 404, keep original but add sync button
            if (!apiData || apiData._notFound) {
                addActionButtons(card, reference, false);
                return;
            }

            const eventUrl = `https://www.e-leiloes.pt/evento/${reference}`;

            // Calculate time info
            const timeInfo = apiData.data_fim ? calculateTimeRemaining(apiData.data_fim) : null;
            const hasBids = apiData.lance_atual && apiData.lance_atual > 0;

            // Extract native image BEFORE clearing card content
            let nativeImageUrl = null;
            const nativeImageDiv = card.querySelector('.p-evento-image');
            if (nativeImageDiv) {
                const bgStyle = nativeImageDiv.style.backgroundImage;
                if (bgStyle) {
                    const match = bgStyle.match(/url\(["']?([^"')]+)["']?\)/);
                    if (match) nativeImageUrl = match[1];
                }
                // Also try to find img tag
                const imgTag = nativeImageDiv.querySelector('img');
                if (imgTag && imgTag.src) nativeImageUrl = imgTag.src;
            }

            // Build new card content
            card.innerHTML = '';

            // Add badges container
            const badgesDiv = document.createElement('div');
            badgesDiv.className = 'better-badges';

            if (timeInfo) {
                if (timeInfo.isCritical) {
                    badgesDiv.innerHTML += `<span class="better-badge ending">🔥 A Terminar!</span>`;
                } else if (timeInfo.isEnding) {
                    badgesDiv.innerHTML += `<span class="better-badge ending-soon">⚡ < 24h</span>`;
                }
            }

            card.appendChild(badgesDiv);

            // Add action buttons
            addActionButtons(card, reference, true, apiData);

            // Carousel - use API images or fallback to native image
            let images = [];
            if (apiData.imagens && apiData.imagens.length > 0) {
                images = apiData.imagens.slice(0, CONFIG.MAX_CAROUSEL_IMAGES);
            } else if (nativeImageUrl) {
                images = [nativeImageUrl];
            }

            if (images.length > 0) {
                const carousel = document.createElement('div');
                carousel.className = 'better-carousel';
                carousel.innerHTML = `
                    <div class="better-carousel-track">
                        ${images.map((img, idx) => `<div class="better-carousel-slide" style="background-image: url('${img}');" data-index="${idx}"></div>`).join('')}
                    </div>
                    ${timeInfo && timeInfo.isEnding ? `
                        <div class="better-time-overlay ${timeInfo.isCritical ? 'critical' : ''}">
                            <div class="better-time-overlay-content">
                                <span class="better-time-overlay-icon">⏱️</span>
                                <span>${timeInfo.text}</span>
                            </div>
                        </div>
                    ` : ''}
                    ${images.length > 1 ? `
                        <button class="better-carousel-nav prev">‹</button>
                        <button class="better-carousel-nav next">›</button>
                        <div class="better-carousel-counter">${images.length} 📷</div>
                    ` : ''}
                `;

                card.appendChild(carousel);

                // Carousel navigation
                if (images.length > 1) {
                    const track = carousel.querySelector('.better-carousel-track');
                    let currentSlide = 0;

                    function updateCarousel() {
                        track.style.transform = `translateX(-${currentSlide * 100}%)`;
                    }

                    carousel.querySelector('.prev')?.addEventListener('click', (e) => {
                        e.stopPropagation();
                        currentSlide = (currentSlide - 1 + images.length) % images.length;
                        updateCarousel();
                    });

                    carousel.querySelector('.next')?.addEventListener('click', (e) => {
                        e.stopPropagation();
                        currentSlide = (currentSlide + 1) % images.length;
                        updateCarousel();
                    });
                }

                // Lightbox
                carousel.querySelectorAll('.better-carousel-slide').forEach((slide, idx) => {
                    slide.addEventListener('click', (e) => {
                        e.stopPropagation();
                        openLightbox(images, idx);
                    });
                });
            } else {
                // No images at all - show placeholder
                const placeholder = document.createElement('div');
                placeholder.className = 'better-carousel';
                placeholder.innerHTML = `
                    <div style="display:flex;align-items:center;justify-content:center;height:100%;color:#9ca3af;font-size:14px;">
                        📷 Sem imagem
                    </div>
                `;
                card.appendChild(placeholder);
            }

            // Card body
            const cardBody = document.createElement('div');
            cardBody.className = 'better-card-body';

            // Title (2 lines max with ellipsis)
            const title = document.createElement('h3');
            title.className = 'better-title';
            title.textContent = apiData.titulo || reference;
            title.title = apiData.titulo || reference;
            cardBody.appendChild(title);

            // Meta row: location + type badge
            const metaRow = document.createElement('div');
            metaRow.className = 'better-meta-row';

            const location = apiData.distrito || apiData.concelho || apiData.freguesia || '';
            if (location) {
                metaRow.innerHTML += `
                    <div class="better-location">
                        <i class="pi pi-map-marker"></i>
                        <span class="better-location-text" title="${location}">${location}</span>
                    </div>
                `;
            }

            const typeClass = getTypeClass(apiData.tipo, apiData.tipo_id);
            const typeLabel = getTypeLabel(apiData.tipo, apiData.tipo_id);
            metaRow.innerHTML += `<span class="better-type-badge ${typeClass}">${typeLabel}</span>`;

            cardBody.appendChild(metaRow);

            // Values row (VB, VA, VM)
            const hasValues = apiData.valor_base || apiData.valor_abertura || apiData.valor_minimo;
            if (hasValues) {
                const valoresRow = document.createElement('div');
                valoresRow.className = 'better-valores-row';

                if (apiData.valor_base) {
                    valoresRow.innerHTML += `<div class="better-valor-item"><span class="better-valor-label">Base</span><span class="better-valor-amount">${formatCurrency(apiData.valor_base)}</span></div>`;
                }
                if (apiData.valor_abertura) {
                    valoresRow.innerHTML += `<div class="better-valor-item"><span class="better-valor-label">Abertura</span><span class="better-valor-amount">${formatCurrency(apiData.valor_abertura)}</span></div>`;
                }
                if (apiData.valor_minimo) {
                    valoresRow.innerHTML += `<div class="better-valor-item"><span class="better-valor-label">Mínimo</span><span class="better-valor-amount">${formatCurrency(apiData.valor_minimo)}</span></div>`;
                }

                cardBody.appendChild(valoresRow);
            }

            // Lance CTA button
            const lanceCta = document.createElement('button');
            lanceCta.className = `better-lance-cta ${hasBids ? 'has-bids' : ''}`;
            lanceCta.innerHTML = `
                <span class="lance-icon">💰</span>
                <div>
                    <div class="lance-label">${hasBids ? 'Lance Atual' : 'Valor Inicial'}</div>
                    <div class="lance-value">${formatCurrency(apiData.lance_atual || apiData.valor_abertura || apiData.valor_base || 0)}</div>
                </div>
                ${hasBids ? '<span class="better-bids-count">Com lances</span>' : ''}
            `;
            lanceCta.addEventListener('click', (e) => {
                e.stopPropagation();
                window.open(eventUrl, '_blank');
            });
            cardBody.appendChild(lanceCta);

            card.appendChild(cardBody);

            // Countdown row (bottom)
            if (timeInfo) {
                const countdownRow = document.createElement('div');
                countdownRow.className = 'better-countdown-row';
                countdownRow.innerHTML = `
                    <span class="better-countdown-icon">⏰</span>
                    <span class="better-countdown-text">Termina em:</span>
                    <span class="better-countdown-time ${timeInfo.isCritical ? 'critical' : (timeInfo.isEnding ? 'ending-soon' : '')}" data-end="${apiData.data_fim}">${timeInfo.text}</span>
                `;
                card.appendChild(countdownRow);
            }

            // Click handler for card
            card.style.cursor = 'pointer';
            card.addEventListener('click', (e) => {
                if (e.target.closest('.better-carousel-nav, .better-carousel-slide, .better-action-btn, .better-lance-cta')) return;
                e.preventDefault();
                window.open(eventUrl, '_blank');
            });

        } catch (error) {
            console.error(`❌ Error enhancing card for ${reference}:`, error);
        }
    }

    function addActionButtons(card, reference, hasData, apiData = null) {
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'better-action-buttons';

        // Favorite button
        const isFav = favorites.includes(reference);
        const favBtn = document.createElement('button');
        favBtn.className = `better-action-btn favorite ${isFav ? 'active' : ''}`;
        favBtn.title = isFav ? 'Remover dos favoritos' : 'Adicionar aos favoritos';
        favBtn.innerHTML = isFav ? '❤️' : '🤍';
        favBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const nowFav = toggleFavorite(reference);
            favBtn.classList.toggle('active', nowFav);
            favBtn.innerHTML = nowFav ? '❤️' : '🤍';
            favBtn.title = nowFav ? 'Remover dos favoritos' : 'Adicionar aos favoritos';
        });
        buttonsDiv.appendChild(favBtn);

        if (hasData) {
            // Refresh button
            const refreshBtn = document.createElement('button');
            refreshBtn.className = 'better-action-btn refresh';
            refreshBtn.title = 'Atualizar dados';
            refreshBtn.innerHTML = '🔄';
            refreshBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                refreshBtn.classList.add('loading');
                refreshBtn.innerHTML = '';

                const success = await triggerScrape(reference);
                if (success) {
                    setTimeout(async () => {
                        delete card.dataset.betterEnhanced;
                        await enhanceCard(card);
                    }, 2000);
                } else {
                    refreshBtn.classList.remove('loading');
                    refreshBtn.innerHTML = '❌';
                    setTimeout(() => { refreshBtn.innerHTML = '🔄'; }, 2000);
                }
            });
            buttonsDiv.appendChild(refreshBtn);
        }

        // Sync button
        const syncBtn = document.createElement('button');
        syncBtn.className = 'better-action-btn sync';
        syncBtn.title = hasData ? 'Sincronizar' : 'Adicionar à BD';
        syncBtn.innerHTML = '⬇️';
        syncBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            syncBtn.classList.add('loading');
            syncBtn.innerHTML = '';

            const success = await triggerScrape(reference);
            if (success) {
                syncBtn.classList.remove('loading');
                syncBtn.innerHTML = '✅';
                if (!hasData) {
                    setTimeout(async () => {
                        delete card.dataset.betterEnhanced;
                        card.querySelectorAll('.better-action-buttons').forEach(el => el.remove());
                        await enhanceCard(card);
                    }, 2000);
                }
            } else {
                syncBtn.classList.remove('loading');
                syncBtn.innerHTML = '❌';
                setTimeout(() => { syncBtn.innerHTML = '⬇️'; }, 2000);
            }
        });
        buttonsDiv.appendChild(syncBtn);

        card.appendChild(buttonsDiv);
    }

    // ====================================
    // OBSERVER & INIT
    // ====================================

    function enhanceAllCards() {
        document.querySelectorAll('.p-evento').forEach(card => enhanceCard(card));
    }

    const observer = new MutationObserver(() => {
        enhanceAllCards();
    });

    function updateAllCountdowns() {
        document.querySelectorAll('[data-end]').forEach(el => {
            const remaining = calculateTimeRemaining(el.dataset.end);
            if (remaining) {
                el.textContent = remaining.text;
                el.classList.toggle('ending-soon', remaining.isEnding && !remaining.isCritical);
                el.classList.toggle('critical', remaining.isCritical);
            }
        });
    }

    function init() {
        console.log('🚀 Better E-Leilões Card Enhancer v9.1 - Fixed Height + Image Fallback');

        integrateWithNativeFloatingButtons();
        enhanceAllCards();

        setInterval(updateAllCountdowns, 1000);
        observer.observe(document.body, { childList: true, subtree: true });

        console.log('✅ v9.1 ativo - fallback para imagem original quando API não tem!');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
