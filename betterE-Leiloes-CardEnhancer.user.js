// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      11.1
// @description  v11.1 - Cleaner side-by-side design, no gap
// @author       Nuno Mansilhas
// @match        https://e-leiloes.pt/*
// @match        https://www.e-leiloes.pt/*
// @match        http://e-leiloes.pt/*
// @match        http://www.e-leiloes.pt/*
// @icon         https://www.e-leiloes.pt/favicon.ico
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      127.0.0.1
// @connect      e-leiloes.pt
// @connect      www.e-leiloes.pt
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
        MAX_CAROUSEL_IMAGES: 10  // Increased to show more images
    };

    // ====================================
    // ESTILOS CSS - MINIMAL CLEAN
    // ====================================

    const styles = document.createElement('style');
    styles.textContent = `
        /* ============================================ */
        /* BASE STYLES (comum a todos os designs)      */
        /* ============================================ */

        .p-evento {
            overflow: hidden !important;
            transition: background-color 0.2s ease !important;
        }

        .p-evento:hover {
            background-color: #f8f9fa !important;
        }

        /* Força remover bordas do div nativo */
        .p-evento[data-better-enhanced="true"] .w-full {
            border: none !important;
            border-radius: 0 !important;
        }

        /* Padroniza fontes */
        .p-evento[data-better-enhanced="true"],
        .p-evento[data-better-enhanced="true"] *:not([class*="pi-"]):not(i) {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        }

        /* Hide custom context menu */
        .p-contextmenu.p-component {
            display: none !important;
        }

        /* Esconde elementos nativos que substituímos */
        .p-evento[data-better-enhanced="true"] .surface-100.border-round-bottom,
        .p-evento[data-better-enhanced="true"] .p-tag.p-component {
            display: none !important;
        }

        /* Fix para links */
        .p-evento a[href*="/evento/"] {
            pointer-events: none !important;
        }

        /* Map marker clickable */
        .p-evento[data-better-enhanced="true"] .pi-map-marker.better-map-link {
            color: #1e3a5f !important;
            cursor: pointer !important;
            pointer-events: auto !important;
            transition: color 0.15s ease !important;
        }

        .p-evento[data-better-enhanced="true"] .pi-map-marker.better-map-link:hover {
            color: #3b82f6 !important;
        }

        /* ============================================ */
        /* CONSISTENT FONT SIZES                       */
        /* ============================================ */

        .p-evento[data-better-enhanced="true"] .better-valor-label,
        .p-evento[data-better-enhanced="true"] .better-valor-amount,
        .p-evento[data-better-enhanced="true"] .better-countdown-text,
        .p-evento[data-better-enhanced="true"] .better-countdown-time {
            font-size: 12px !important;
        }

        /* ============================================ */
        /* ACTION BUTTONS - Same style as native star  */
        /* ============================================ */

        .better-action-buttons {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .better-action-btn {
            background: none;
            border: none;
            cursor: pointer;
            padding: 0;
            color: #1e3a5f;
            transition: all 0.15s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .better-action-btn i {
            font-size: 1.25rem;
        }

        .better-action-btn:hover {
            color: #3b82f6;
        }

        .better-action-btn.loading {
            pointer-events: none;
            opacity: 0.6;
        }

        .better-action-btn.loading i {
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
            width: 100%;
            height: 180px;
            overflow: hidden;
            background: #f1f5f9;
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
            background: rgba(255, 255, 255, 0.9);
            color: #333;
            border: none;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            z-index: 5;
            opacity: 0;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        }

        .better-carousel:hover .better-carousel-nav {
            opacity: 1;
        }

        .better-carousel-nav:hover {
            background: #333;
            color: white;
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
            top: 8px;
            left: 8px;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 600;
            z-index: 5;
        }

        /* Dashboard button */
        .better-dashboard-btn {
            background: #3b82f6 !important;
            border-color: #3b82f6 !important;
        }

        .better-dashboard-btn:hover {
            background: #2563eb !important;
            transform: scale(1.05) !important;
        }

        /* ============================================ */
        /* MINIMAL CLEAN DESIGN - OPTIMIZED LAYOUT     */
        /* ============================================ */

        .p-evento[data-better-enhanced="true"] {
            border-radius: 16px !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
            background: white !important;
            position: relative !important;
            height: 420px !important;
            min-height: 420px !important;
            max-height: 420px !important;
            display: flex !important;
            flex-direction: column !important;
            overflow: hidden !important;
        }

        .p-evento[data-better-enhanced="true"]:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
            border-color: #d1d5db !important;
            background: #f9fafb !important;
        }

        /* Carousel - compact */
        .p-evento[data-better-enhanced="true"] .better-carousel {
            border-radius: 10px;
            margin: 6px;
            height: 140px !important;
            min-height: 140px !important;
            max-height: 140px !important;
            flex-shrink: 0 !important;
        }

        /* Native header area - compact */
        .p-evento[data-better-enhanced="true"] > .w-full:first-of-type {
            flex-shrink: 0 !important;
            padding: 4px 8px !important;
        }

        /* Title area - FIXED height for alignment */
        .p-evento[data-better-enhanced="true"] .p-evento-title,
        .p-evento[data-better-enhanced="true"] a[href*="/evento/"] > div {
            display: -webkit-box !important;
            -webkit-line-clamp: 2 !important;
            -webkit-box-orient: vertical !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            height: 32px !important;
            min-height: 32px !important;
            max-height: 32px !important;
            line-height: 1.3 !important;
            font-size: 11px !important;
        }

        /* Card content wrapper - fills remaining space, pushes countdown to bottom */
        .p-evento[data-better-enhanced="true"] > .better-card-content {
            flex: 1 1 auto !important;
            display: flex !important;
            flex-direction: column !important;
            min-height: 0 !important;
        }

        /* ============================================ */
        /* SIDE-BY-SIDE CONTENT - CLEAN MINIMAL DESIGN */
        /* ============================================ */

        .p-evento[data-better-enhanced="true"] .better-content-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            padding: 6px;
            flex: 1;
        }

        /* Left column: Values */
        .p-evento[data-better-enhanced="true"] .better-values-col {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .p-evento[data-better-enhanced="true"] .better-value-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 3px 0;
            border-bottom: 1px solid #f3f4f6;
        }

        .p-evento[data-better-enhanced="true"] .better-value-row:last-child {
            border-bottom: none;
        }

        .p-evento[data-better-enhanced="true"] .better-value-row.highlight {
            background: linear-gradient(90deg, #fef3c7 0%, transparent 100%);
            margin: 2px -4px;
            padding: 4px 4px;
            border-radius: 4px;
            border-bottom: none;
        }

        .p-evento[data-better-enhanced="true"] .better-value-label {
            color: #9ca3af;
            font-size: 9px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .p-evento[data-better-enhanced="true"] .better-value-row.highlight .better-value-label {
            color: #92400e;
            font-weight: 600;
        }

        .p-evento[data-better-enhanced="true"] .better-value-amount {
            color: #374151;
            font-size: 11px;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        .p-evento[data-better-enhanced="true"] .better-value-row.highlight .better-value-amount {
            color: #92400e;
            font-weight: 700;
            font-size: 12px;
        }

        /* Right column: Details */
        .p-evento[data-better-enhanced="true"] .better-details-col {
            display: flex;
            flex-direction: column;
            gap: 2px;
            border-left: 2px solid #e5e7eb;
            padding-left: 10px;
        }

        .p-evento[data-better-enhanced="true"] .better-detail-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 3px 0;
        }

        .p-evento[data-better-enhanced="true"] .better-detail-label {
            color: #9ca3af;
            font-size: 9px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }

        .p-evento[data-better-enhanced="true"] .better-detail-value {
            color: #1f2937;
            font-size: 10px;
            font-weight: 500;
            text-align: right;
            max-width: 80px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* Zone: Countdown - clean bottom bar */
        .p-evento[data-better-enhanced="true"] .better-countdown-row {
            background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%);
            padding: 6px;
            border-top: 1px solid #e5e7eb;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 0 0 16px 16px;
            flex-shrink: 0;
        }

        .p-evento[data-better-enhanced="true"] .native-ref-prefix.lo { color: #3b82f6 !important; }
        .p-evento[data-better-enhanced="true"] .native-ref-prefix.np { color: #f59e0b !important; }

        /* ============================================ */
        /* COUNTDOWN BASE                              */
        /* ============================================ */

        .better-countdown {
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 9px;
        }

        .better-countdown-icon {
            font-size: 10px;
        }

        .better-countdown-text {
            font-weight: 600;
            color: #374151;
        }

        .better-countdown-time {
            color: #dc2626;
            font-weight: 700;
        }

        .better-countdown-time.ending-soon {
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* ============================================ */
        /* LIGHTBOX FOR FULL IMAGE VIEW                */
        /* ============================================ */

        .better-lightbox {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.9);
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
        }

        .better-lightbox-close {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 40px;
            height: 40px;
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 50%;
            color: white;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .better-lightbox-close:hover {
            background: rgba(255, 255, 255, 0.4);
        }

        .better-lightbox-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: rgba(255, 255, 255, 0.2);
            border: none;
            border-radius: 50%;
            color: white;
            font-size: 24px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .better-lightbox-nav:hover {
            background: rgba(255, 255, 255, 0.4);
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
            background: rgba(0, 0, 0, 0.5);
            padding: 5px 15px;
            border-radius: 20px;
        }
    `;
    document.head.appendChild(styles);

    // ====================================
    // UTILITÁRIOS
    // ====================================

    function formatCurrency(value) {
        if (value === null || value === undefined) return '0,00 €';
        const num = parseFloat(value);
        return new Intl.NumberFormat('pt-PT', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(num) + ' €';
    }

    function calculateTimeRemaining(endDate) {
        if (!endDate) return null;

        const now = new Date();
        const end = new Date(endDate);
        const diff = end - now;

        if (diff <= 0) return { text: 'Terminado', isEnding: false };

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        let text = '';
        const isEnding = days === 0 && hours < 24;

        if (days > 0) {
            text = `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            text = `${hours}h ${minutes}m ${seconds}s`;
        } else if (minutes > 0) {
            text = `${minutes}m ${seconds}s`;
        } else {
            text = `${seconds}s`;
        }

        return { text, isEnding };
    }

    // ====================================
    // API (using GM_xmlhttpRequest to bypass ad blockers)
    // ====================================

    function getEventFromAPI(reference) {
        if (!CONFIG.ENABLE_API_ENRICHMENT) return Promise.resolve(null);

        return new Promise((resolve) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url: `${CONFIG.API_BASE}/events/${reference}`,
                headers: {
                    'Accept': 'application/json'
                },
                onload: function(response) {
                    if (response.status === 200) {
                        try {
                            resolve(JSON.parse(response.responseText));
                        } catch (e) {
                            console.error(`❌ JSON parse error for ${reference}:`, e);
                            resolve(null);
                        }
                    } else if (response.status === 404) {
                        // Event not in database - return special marker
                        resolve({ _notFound: true });
                    } else {
                        resolve(null);
                    }
                },
                onerror: function(error) {
                    console.error(`❌ API error for ${reference}:`, error);
                    resolve(null);
                },
                ontimeout: function() {
                    console.error(`❌ API timeout for ${reference}`);
                    resolve(null);
                }
            });
        });
    }

    // Scrape event via our backend (uses official API + saves to DB)
    function scrapeEventViaBackend(reference) {
        return new Promise((resolve) => {
            GM_xmlhttpRequest({
                method: 'POST',
                url: `${CONFIG.API_BASE}/scrape/stage2/api?references=${reference}&save_to_db=true`,
                headers: {
                    'Accept': 'application/json'
                },
                onload: function(response) {
                    if (response.status === 200) {
                        try {
                            const data = JSON.parse(response.responseText);
                            // Return first event from the response
                            resolve(data.events && data.events.length > 0 ? data.events[0] : null);
                        } catch (e) {
                            console.error(`❌ JSON parse error:`, e);
                            resolve(null);
                        }
                    } else {
                        console.error(`❌ Scrape failed for ${reference}:`, response.status);
                        resolve(null);
                    }
                },
                onerror: function(error) {
                    console.error(`❌ Scrape error for ${reference}:`, error);
                    resolve(null);
                }
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
        if (e.key === 'ArrowLeft') {
            lightboxIndex = (lightboxIndex - 1 + lightboxImages.length) % lightboxImages.length;
            const img = document.querySelector('.better-lightbox-img');
            const counter = document.querySelector('.better-lightbox-counter');
            if (img && counter) {
                img.src = lightboxImages[lightboxIndex];
                counter.textContent = `${lightboxIndex + 1} / ${lightboxImages.length}`;
            }
        }
        if (e.key === 'ArrowRight') {
            lightboxIndex = (lightboxIndex + 1) % lightboxImages.length;
            const img = document.querySelector('.better-lightbox-img');
            const counter = document.querySelector('.better-lightbox-counter');
            if (img && counter) {
                img.src = lightboxImages[lightboxIndex];
                counter.textContent = `${lightboxIndex + 1} / ${lightboxImages.length}`;
            }
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
        btn.innerHTML = `
            <span class="p-button-icon pi pi-home" data-pc-section="icon"></span>
            <span class="p-button-label" data-pc-section="label">&nbsp;</span>
        `;

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            window.open(CONFIG.DASHBOARD_URL, '_blank', 'noopener,noreferrer');
        });

        document.body.appendChild(btn);
    }

    // ====================================
    // CARD ENHANCEMENT
    // ====================================

    function extractReferenceFromCard(card) {
        const refElement = card.querySelector('.pi-tag + span');
        if (refElement) {
            return refElement.textContent.trim();
        }
        return null;
    }

    async function enhanceCard(card) {
        if (card.dataset.betterEnhanced) return;
        card.dataset.betterEnhanced = 'true';

        const reference = extractReferenceFromCard(card);

        try {
            if (!reference) return;

            const apiData = await getEventFromAPI(reference);

            // If API returned 404 or null, keep original card but add action buttons
            if (!apiData || apiData._notFound) {
                // Add sync button to allow scraping this event
                addActionButtons(card, reference, false, null);
                return; // Keep original card design
            }

            const eventUrl = `https://www.e-leiloes.pt/evento/${reference}`;
            card.style.position = 'relative';

            // Add action buttons (refresh, sync, and map if GPS available)
            const hasGPS = apiData.latitude && apiData.longitude;
            const gpsData = hasGPS ? { lat: apiData.latitude, lng: apiData.longitude } : null;
            addActionButtons(card, reference, true, gpsData);

            // Remove native links
            card.querySelectorAll('a[href*="/evento/"]').forEach(link => {
                link.removeAttribute('href');
                link.style.pointerEvents = 'none';
            });

            // Color reference prefix
            const nativeRefSpan = card.querySelector('.pi-tag + span');
            if (nativeRefSpan) {
                const refText = nativeRefSpan.textContent.trim();
                const prefix = refText.substring(0, 2);
                const rest = refText.substring(2);
                nativeRefSpan.innerHTML = `<span class="native-ref-prefix ${prefix.toLowerCase()}">${prefix}</span>${rest}`;
            }

            // Remove borders from native divs
            card.querySelectorAll('.w-full').forEach(div => {
                div.classList.remove('border-1', 'surface-border', 'border-round');
                div.style.border = 'none';
            });

            // Style map marker (hasGPS already defined above)
            const nativeMapMarker = card.querySelector('.pi-map-marker');
            if (nativeMapMarker && hasGPS) {
                const mapsUrl = `https://www.google.com/maps?q=${apiData.latitude},${apiData.longitude}`;
                nativeMapMarker.classList.add('better-map-link');
                nativeMapMarker.title = 'Ver no Google Maps';
                nativeMapMarker.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    window.open(mapsUrl, '_blank', 'noopener,noreferrer');
                });
            }

            // Carousel - show all images from fotos field (API returns array of FotoItem objects)
            const nativeImageDiv = card.querySelector('.p-evento-image');
            // Extract image URLs from fotos objects (same transformation as backend dashboard)
            const images = (apiData.fotos || [])
                .slice(0, CONFIG.MAX_CAROUSEL_IMAGES)
                .map(f => f.image || f.thumbnail || f)  // Handle both object and string formats
                .filter(Boolean);

            if (nativeImageDiv && images.length > 0) {
                nativeImageDiv.style.display = 'none';

                const carousel = document.createElement('div');
                carousel.className = 'better-carousel';
                carousel.innerHTML = `
                    <div class="better-carousel-track">
                        ${images.map((img, idx) => `<div class="better-carousel-slide" style="background-image: url('${img}');" data-index="${idx}"></div>`).join('')}
                    </div>
                    <div class="better-carousel-counter">${images.length} 📷</div>
                    ${images.length > 1 ? `
                        <button class="better-carousel-nav prev">‹</button>
                        <button class="better-carousel-nav next">›</button>
                        <div class="better-carousel-dots">
                            ${images.map((_, idx) => `<div class="better-carousel-dot ${idx === 0 ? 'active' : ''}" data-index="${idx}"></div>`).join('')}
                        </div>
                    ` : ''}
                `;

                nativeImageDiv.parentNode.insertBefore(carousel, nativeImageDiv.nextSibling);

                // Carousel navigation
                const track = carousel.querySelector('.better-carousel-track');
                const dots = carousel.querySelectorAll('.better-carousel-dot');
                let currentSlide = 0;

                function updateCarousel() {
                    track.style.transform = `translateX(-${currentSlide * 100}%)`;
                    dots.forEach((d, i) => d.classList.toggle('active', i === currentSlide));
                }

                if (images.length > 1) {
                    carousel.querySelector('.prev').addEventListener('click', (e) => {
                        e.stopPropagation();
                        currentSlide = (currentSlide - 1 + images.length) % images.length;
                        updateCarousel();
                    });

                    carousel.querySelector('.next').addEventListener('click', (e) => {
                        e.stopPropagation();
                        currentSlide = (currentSlide + 1) % images.length;
                        updateCarousel();
                    });

                    dots.forEach((dot, idx) => {
                        dot.addEventListener('click', (e) => {
                            e.stopPropagation();
                            currentSlide = idx;
                            updateCarousel();
                        });
                    });
                }

                // Click on slide opens lightbox
                carousel.querySelectorAll('.better-carousel-slide').forEach((slide, idx) => {
                    slide.addEventListener('click', (e) => {
                        e.stopPropagation();
                        openLightbox(images, idx);
                    });
                });
            }

            // Values - Side-by-side layout: Values (left) | Details (right)
            // Left column: VB, VA, VM, Lance stacked
            let valuesHTML = '';
            if (apiData.valor_base) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VB</span><span class="better-value-amount">${formatCurrency(apiData.valor_base)}</span></div>`;
            if (apiData.valor_abertura) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VA</span><span class="better-value-amount">${formatCurrency(apiData.valor_abertura)}</span></div>`;
            if (apiData.valor_minimo) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VM</span><span class="better-value-amount">${formatCurrency(apiData.valor_minimo)}</span></div>`;
            valuesHTML += `<div class="better-value-row highlight"><span class="better-value-label">Lance</span><span class="better-value-amount">${apiData.lance_atual ? formatCurrency(apiData.lance_atual) : '0 €'}</span></div>`;

            // Right column: Dynamic details based on event type
            let detailsHTML = '';
            const tipoId = apiData.tipo_id || 0;
            const isImovel = tipoId === 1 || (apiData.tipo && apiData.tipo.toLowerCase().includes('imov'));
            const isVeiculo = tipoId === 2 || (apiData.tipo && (apiData.tipo.toLowerCase().includes('veic') || apiData.tipo.toLowerCase().includes('auto')));

            if (isImovel) {
                // Imóvel: Tipologia, Área, Subtipo
                if (apiData.tipologia) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipologia}</span></div>`;
                if (apiData.area_util) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Área</span><span class="better-detail-value">${apiData.area_util} m²</span></div>`;
                else if (apiData.area_bruta) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Área</span><span class="better-detail-value">${apiData.area_bruta} m²</span></div>`;
                if (apiData.subtipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Subtipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
            } else if (isVeiculo) {
                // Veículo: Matrícula, Marca, Modelo
                if (apiData.matricula) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Matrícula</span><span class="better-detail-value">${apiData.matricula}</span></div>`;
                if (apiData.marca) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Marca</span><span class="better-detail-value">${apiData.marca}</span></div>`;
                if (apiData.modelo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Modelo</span><span class="better-detail-value">${apiData.modelo}</span></div>`;
                if (apiData.subtipo && !apiData.marca) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
            } else {
                // Other: Subtipo, Tipo
                if (apiData.subtipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Subtipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
                if (apiData.tipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipo}</span></div>`;
            }
            // Always add location if available
            if (apiData.concelho) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Local</span><span class="better-detail-value" title="${apiData.concelho}${apiData.distrito ? ', ' + apiData.distrito : ''}">${apiData.concelho}</span></div>`;
            else if (apiData.distrito) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Distrito</span><span class="better-detail-value">${apiData.distrito}</span></div>`;

            // Fallback if no details found
            if (!detailsHTML) {
                if (apiData.tipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipo}</span></div>`;
            }

            const valoresHTML = `<div class="better-content-grid"><div class="better-values-col">${valuesHTML}</div><div class="better-details-col">${detailsHTML}</div></div>`;

            // Countdown (API v2: data_fim)
            let countdownHTML = '';
            if (apiData.data_fim) {
                const remaining = calculateTimeRemaining(apiData.data_fim);
                if (remaining) {
                    const countdownId = `countdown-${reference}`;
                    countdownHTML = `
                        <div class="better-countdown-row">
                            <div class="better-countdown">
                                <span class="better-countdown-icon">⏱️</span>
                                <span class="better-countdown-text">Termina:</span>
                                <span class="better-countdown-time ${remaining.isEnding ? 'ending-soon' : ''}" id="${countdownId}" data-end="${apiData.data_fim}">${remaining.text}</span>
                            </div>
                        </div>
                    `;
                }
            }

            // Insert content - wrapper is a direct child of card for proper flex layout
            const wrapper = document.createElement('div');
            wrapper.className = 'better-card-content';
            wrapper.innerHTML = valoresHTML + countdownHTML;
            // Append directly to card so it participates in card's flex layout
            card.appendChild(wrapper);

            // Click handlers
            card.style.cursor = 'pointer';
            card.addEventListener('click', (e) => {
                if (e.target.closest('.pi-map-marker, .better-carousel-nav, .better-carousel-dot, .better-carousel-slide, .pi-star, .better-action-btn')) return;
                e.preventDefault();
                e.stopPropagation();
                window.open(eventUrl, '_blank', 'noopener,noreferrer');
            }, true);

            // Restore native right-click context menu
            card.addEventListener('contextmenu', (e) => {
                e.stopPropagation();
            }, true);

        } catch (error) {
            console.error(`❌ Error enhancing card for ${reference}:`, error);
        }
    }

    function addActionButtons(card, reference, hasData, gpsData) {
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'better-action-buttons';

        // Map button - opens Google Maps (only if GPS available)
        if (gpsData) {
            const mapBtn = document.createElement('button');
            mapBtn.className = 'better-action-btn map';
            mapBtn.title = 'Ver no Google Maps';
            mapBtn.innerHTML = '<i class="pi pi-map-marker"></i>';
            mapBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                const mapsUrl = `https://www.google.com/maps?q=${gpsData.lat},${gpsData.lng}`;
                window.open(mapsUrl, '_blank', 'noopener,noreferrer');
            });
            buttonsDiv.appendChild(mapBtn);
        }

        // Refresh button - scrapes via backend (uses official API + saves to DB)
        const refreshBtn = document.createElement('button');
        refreshBtn.className = 'better-action-btn refresh';
        refreshBtn.title = 'Atualizar dados (scrape via API oficial)';
        refreshBtn.innerHTML = '<i class="pi pi-sync"></i>';
        refreshBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            e.preventDefault();
            refreshBtn.classList.add('loading');

            const scrapedEvent = await scrapeEventViaBackend(reference);

            if (scrapedEvent) {
                refreshBtn.classList.remove('loading');
                refreshBtn.innerHTML = '<i class="pi pi-check"></i>';

                // Re-enhance card with fresh data after a short delay
                setTimeout(async () => {
                    refreshBtn.innerHTML = '<i class="pi pi-sync"></i>';
                    // Remove enhanced flag to allow re-enhancement
                    delete card.dataset.betterEnhanced;
                    // Remove our added elements
                    card.querySelectorAll('.better-carousel, .better-card-content, .better-action-buttons').forEach(el => el.remove());
                    // Show native image again
                    const nativeImg = card.querySelector('.p-evento-image');
                    if (nativeImg) nativeImg.style.display = '';
                    // Re-enhance with fresh data from our backend
                    await enhanceCard(card);
                }, 1000);
            } else {
                refreshBtn.classList.remove('loading');
                refreshBtn.innerHTML = '<i class="pi pi-times"></i>';
                setTimeout(() => { refreshBtn.innerHTML = '<i class="pi pi-sync"></i>'; }, 2000);
            }
        });
        buttonsDiv.appendChild(refreshBtn);

        // Find the native star's container and insert our buttons inline
        // Structure: <div class="flex align-items-center gap-1"><span class="p-tag">...</span><i class="pi pi-star">...</i></div>
        const nativeStar = card.querySelector('.pi-star');
        if (nativeStar && nativeStar.parentElement) {
            // Insert our buttons after the native star in the same flex container
            nativeStar.parentElement.appendChild(buttonsDiv);
        } else {
            // Fallback: if no star found, append to the header area
            const headerArea = card.querySelector('.flex.align-items-center.gap-1') || card.querySelector('.w-full:first-of-type');
            if (headerArea) {
                headerArea.appendChild(buttonsDiv);
            } else {
                // Last resort: append to card with position relative
                card.style.position = 'relative';
                buttonsDiv.style.position = 'absolute';
                buttonsDiv.style.top = '6px';
                buttonsDiv.style.right = '6px';
                card.appendChild(buttonsDiv);
            }
        }
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
                el.classList.toggle('ending-soon', remaining.isEnding);
            }
        });
    }

    function init() {
        console.log('🚀 Better E-Leilões Card Enhancer v11.1 - Clean Side-by-side Design');

        integrateWithNativeFloatingButtons();
        enhanceAllCards();

        setInterval(updateAllCountdowns, 1000);

        observer.observe(document.body, { childList: true, subtree: true });

        console.log('✅ Card enhancer v11.1 ativo!');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
