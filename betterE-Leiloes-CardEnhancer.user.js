// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      7.2
// @description  Design moderno com carousel de imagens - compatível com API v2
// @author       Nuno Mansilhas
// @match        https://e-leiloes.pt/*
// @match        https://www.e-leiloes.pt/*
// @match        http://e-leiloes.pt/*
// @match        http://www.e-leiloes.pt/*
// @icon         https://www.e-leiloes.pt/favicon.ico
// @grant        GM_xmlhttpRequest
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
        MAX_CAROUSEL_IMAGES: 5
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
            transition: all 0.3s ease !important;
            overflow: hidden !important;
        }

        .p-evento:hover {
            transform: translateY(-4px) !important;
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

        /* Force white backgrounds on hover for all card elements */
        .p-evento[data-better-enhanced="true"] *:hover {
            background-color: inherit;
        }

        .p-evento[data-better-enhanced="true"]:hover .better-valores-row {
            background: white !important;
        }
        .p-evento[data-better-enhanced="true"]:hover .better-lance-row {
            background: white !important;
        }
        .p-evento[data-better-enhanced="true"]:hover .better-countdown-row {
            background: #f9fafb !important;
        }
        .p-evento[data-better-enhanced="true"]:hover .better-valor-item:not(.lance-atual) {
            background: #f9fafb !important;
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
            color: #3b82f6 !important;
            cursor: pointer !important;
            pointer-events: auto !important;
            transition: all 0.2s ease !important;
        }

        .p-evento[data-better-enhanced="true"] .pi-map-marker.better-map-link:hover {
            transform: scale(1.2) !important;
        }

        /* Carousel base */
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
        }

        .better-carousel-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(0, 0, 0, 0.5);
            color: white;
            border: none;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 14px;
            z-index: 5;
            opacity: 0;
            transition: all 0.2s ease;
        }

        .better-carousel:hover .better-carousel-nav {
            opacity: 1;
        }

        .better-carousel-nav.prev { left: 6px; }
        .better-carousel-nav.next { right: 6px; }

        .better-carousel-dots {
            position: absolute;
            bottom: 6px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 4px;
            z-index: 5;
        }

        .better-carousel-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .better-carousel-dot.active {
            background: white;
            width: 16px;
            border-radius: 3px;
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
        /* MINIMAL CLEAN DESIGN                        */
        /* ============================================ */

        .p-evento[data-better-enhanced="true"] {
            border-radius: 16px !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
            background: white !important;
        }

        .p-evento[data-better-enhanced="true"]:hover {
            box-shadow: 0 10px 40px rgba(0,0,0,0.1) !important;
            border-color: #d1d5db !important;
        }

        .p-evento[data-better-enhanced="true"] .better-carousel {
            border-radius: 12px;
            margin: 8px;
            height: 160px;
        }

        /* Zone: Values (VB/VA/VM) */
        .p-evento[data-better-enhanced="true"] .better-valores-row {
            background: white;
            padding: 12px 16px 8px 16px;
            gap: 8px;
            border-top: 1px solid #f3f4f6;
        }

        .p-evento[data-better-enhanced="true"] .better-valor-item {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 6px 12px;
            flex: 1;
            justify-content: center;
        }

        .p-evento[data-better-enhanced="true"] .better-valor-label {
            color: #6b7280;
            font-size: 8px;
        }

        .p-evento[data-better-enhanced="true"] .better-valor-amount {
            color: #111827;
            font-size: 10px;
        }

        /* Zone: Lance */
        .p-evento[data-better-enhanced="true"] .better-lance-row {
            padding: 8px 16px 12px 16px;
        }

        .p-evento[data-better-enhanced="true"] .better-valor-item.lance-atual {
            background: #fef3c7;
            border-color: #fcd34d;
            flex: none;
            padding: 8px 20px;
        }

        /* Zone: Countdown */
        .p-evento[data-better-enhanced="true"] .better-countdown-row {
            background: #f9fafb;
            padding: 10px 16px;
            border-top: 1px solid #e5e7eb;
        }

        .p-evento[data-better-enhanced="true"] .native-ref-prefix.lo { color: #3b82f6 !important; }
        .p-evento[data-better-enhanced="true"] .native-ref-prefix.np { color: #f59e0b !important; }

        /* ============================================ */
        /* VALORES E COUNTDOWN                         */
        /* ============================================ */

        .better-valores-row {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
        }

        .better-valor-item {
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .better-valor-label {
            font-weight: 600;
        }

        .better-valor-amount {
            font-weight: 700;
        }

        /* Lance row - separate centered row */
        .better-lance-row {
            display: flex;
            justify-content: center;
            padding: 8px 12px;
            background: white;
        }

        /* Countdown - Row 5 (locked to bottom) */
        .better-countdown-row {
            padding: 10px 16px;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: auto;
            border-radius: 0 0 16px 16px;
        }

        /* Card flex layout to push countdown to bottom */
        .p-evento[data-better-enhanced="true"] {
            display: flex;
            flex-direction: column;
        }

        /* Target only the card body container (not header) */
        .p-evento[data-better-enhanced="true"] > .w-full:last-of-type {
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }

        /* Card content wrapper - flex to push countdown down */
        .better-card-content {
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }

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
    `;
    document.head.appendChild(styles);

    // ====================================
    // UTILITÁRIOS
    // ====================================

    function formatCurrency(value) {
        if (!value) return '-';
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
            if (!apiData) return;

            const eventUrl = `https://www.e-leiloes.pt/evento/${reference}`;
            card.style.position = 'relative';

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

            // Style map marker
            const hasGPS = apiData.latitude && apiData.longitude;
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

            // Carousel - render even with 1 image
            const nativeImageDiv = card.querySelector('.p-evento-image');
            if (nativeImageDiv && apiData.imagens && apiData.imagens.length > 0) {
                const images = apiData.imagens.slice(0, CONFIG.MAX_CAROUSEL_IMAGES);

                nativeImageDiv.style.display = 'none';

                const carousel = document.createElement('div');
                carousel.className = 'better-carousel';
                carousel.innerHTML = `
                    <div class="better-carousel-track">
                        ${images.map(img => `<div class="better-carousel-slide" style="background-image: url('${img}');"></div>`).join('')}
                    </div>
                    ${images.length > 1 ? `
                        <button class="better-carousel-nav prev">‹</button>
                        <button class="better-carousel-nav next">›</button>
                        <div class="better-carousel-dots">
                            ${images.map((_, idx) => `<div class="better-carousel-dot ${idx === 0 ? 'active' : ''}" data-index="${idx}"></div>`).join('')}
                        </div>
                    ` : ''}
                `;

                nativeImageDiv.parentNode.insertBefore(carousel, nativeImageDiv.nextSibling);

                if (images.length > 1) {
                    const track = carousel.querySelector('.better-carousel-track');
                    const dots = carousel.querySelectorAll('.better-carousel-dot');
                    let currentSlide = 0;

                    function updateCarousel() {
                        track.style.transform = `translateX(-${currentSlide * 100}%)`;
                        dots.forEach((d, i) => d.classList.toggle('active', i === currentSlide));
                    }

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
            }

            // Values - VB/VA/VM in one row, Lance in separate row (API v2 format)
            let valoresHTML = '';
            const topItems = [];
            if (apiData.valor_base) topItems.push(`<div class="better-valor-item"><span class="better-valor-label">VB:</span><span class="better-valor-amount">${formatCurrency(apiData.valor_base)}</span></div>`);
            if (apiData.valor_abertura) topItems.push(`<div class="better-valor-item"><span class="better-valor-label">VA:</span><span class="better-valor-amount">${formatCurrency(apiData.valor_abertura)}</span></div>`);
            if (apiData.valor_minimo) topItems.push(`<div class="better-valor-item"><span class="better-valor-label">VM:</span><span class="better-valor-amount">${formatCurrency(apiData.valor_minimo)}</span></div>`);

            const lanceHTML = `<div class="better-lance-row"><div class="better-valor-item lance-atual"><span class="better-valor-label">Lance:</span><span class="better-valor-amount">${apiData.lance_atual ? formatCurrency(apiData.lance_atual) : '0 €'}</span></div></div>`;

            if (topItems.length > 0) {
                valoresHTML = `<div class="better-valores-row">${topItems.join('')}</div>${lanceHTML}`;
            } else {
                valoresHTML = lanceHTML;
            }

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

            // Insert content
            const cardBody = card.querySelector('.w-full');
            if (cardBody) {
                const wrapper = document.createElement('div');
                wrapper.className = 'better-card-content';
                wrapper.innerHTML = valoresHTML + countdownHTML;
                cardBody.appendChild(wrapper);
            }

            // Click handlers
            card.style.cursor = 'pointer';
            card.addEventListener('click', (e) => {
                if (e.target.closest('.pi-map-marker, .better-carousel-nav, .better-carousel-dot, .pi-star')) return;
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
        console.log('🚀 Better E-Leilões Card Enhancer v7.2 - API v2 (GM_xmlhttpRequest)');

        integrateWithNativeFloatingButtons();
        enhanceAllCards();

        setInterval(updateAllCountdowns, 1000);

        observer.observe(document.body, { childList: true, subtree: true });

        console.log('✅ Card enhancer v7.2 ativo - bypasses ad blockers!');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
