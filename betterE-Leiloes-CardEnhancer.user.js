// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      6.0
// @description  Design moderno com carousel de imagens e distinção visual de tipos de leilão
// @author       Nuno Mansilhas
// @match        https://www.e-leiloes.pt/*
// @icon         https://www.e-leiloes.pt/favicon.ico
// @grant        none
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
        MAX_CAROUSEL_IMAGES: 5,
        // CARD_DESIGN: 1, 2, ou 3 - Escolhe o design dos cards
        // 1 = Minimal Clean (branco, limpo)
        // 2 = Glassmorphism (vidro fosco, gradientes)
        // 3 = Dark Premium (escuro, dourado)
        CARD_DESIGN: 'all' // 'all' mostra os 3 para comparar, ou 1, 2, 3 para escolher um
    };

    // ====================================
    // ESTILOS CSS - 3 DESIGNS
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
        /* DESIGN 1: MINIMAL CLEAN                     */
        /* ============================================ */

        .p-evento[data-design="1"] {
            border-radius: 16px !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
            background: white !important;
        }

        .p-evento[data-design="1"]:hover {
            box-shadow: 0 10px 40px rgba(0,0,0,0.1) !important;
            border-color: #d1d5db !important;
        }

        .p-evento[data-design="1"] .better-carousel {
            border-radius: 12px;
            margin: 8px;
            height: 160px;
        }

        .p-evento[data-design="1"] .better-valores-row {
            background: #f9fafb;
            padding: 10px 12px;
            gap: 6px;
        }

        .p-evento[data-design="1"] .better-valor-item {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 6px 10px;
        }

        .p-evento[data-design="1"] .better-valor-label {
            color: #6b7280;
            font-size: 9px;
        }

        .p-evento[data-design="1"] .better-valor-amount {
            color: #111827;
            font-size: 12px;
        }

        .p-evento[data-design="1"] .better-valor-item.lance-atual {
            background: #fef3c7;
            border-color: #fcd34d;
        }

        .p-evento[data-design="1"] .better-countdown-row {
            background: white;
            padding: 8px 12px;
            border-top: 1px solid #f3f4f6;
        }

        .p-evento[data-design="1"] .native-ref-prefix.lo { color: #3b82f6 !important; }
        .p-evento[data-design="1"] .native-ref-prefix.np { color: #f59e0b !important; }

        /* ============================================ */
        /* DESIGN 2: GLASSMORPHISM                     */
        /* ============================================ */

        .p-evento[data-design="2"] {
            border-radius: 20px !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1) !important;
            background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%) !important;
            backdrop-filter: blur(10px) !important;
        }

        .p-evento[data-design="2"]:hover {
            box-shadow: 0 16px 48px rgba(59,130,246,0.2) !important;
            border-color: rgba(59,130,246,0.3) !important;
        }

        .p-evento[data-design="2"] .better-carousel {
            border-radius: 16px;
            margin: 10px;
            height: 170px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }

        .p-evento[data-design="2"] .better-carousel-nav {
            background: rgba(255,255,255,0.9);
            color: #1e293b;
            backdrop-filter: blur(8px);
        }

        .p-evento[data-design="2"] .better-valores-row {
            background: linear-gradient(135deg, rgba(59,130,246,0.05) 0%, rgba(139,92,246,0.05) 100%);
            padding: 12px;
            gap: 8px;
            border-radius: 0 0 16px 16px;
        }

        .p-evento[data-design="2"] .better-valor-item {
            background: rgba(255,255,255,0.8);
            border: 1px solid rgba(59,130,246,0.2);
            border-radius: 10px;
            padding: 8px 12px;
            backdrop-filter: blur(4px);
        }

        .p-evento[data-design="2"] .better-valor-label {
            color: #6366f1;
            font-size: 9px;
            font-weight: 700;
        }

        .p-evento[data-design="2"] .better-valor-amount {
            color: #1e293b;
            font-size: 12px;
            font-weight: 700;
        }

        .p-evento[data-design="2"] .better-valor-item.lance-atual {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-color: #fbbf24;
        }

        .p-evento[data-design="2"] .better-countdown-row {
            background: transparent;
            padding: 10px 12px;
        }

        .p-evento[data-design="2"] .better-countdown {
            background: rgba(59,130,246,0.1);
            padding: 6px 12px;
            border-radius: 20px;
        }

        .p-evento[data-design="2"] .native-ref-prefix.lo { color: #6366f1 !important; }
        .p-evento[data-design="2"] .native-ref-prefix.np { color: #f59e0b !important; }

        /* ============================================ */
        /* DESIGN 3: DARK PREMIUM                      */
        /* ============================================ */

        .p-evento[data-design="3"] {
            border-radius: 12px !important;
            border: 1px solid #374151 !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
            background: linear-gradient(180deg, #1f2937 0%, #111827 100%) !important;
        }

        .p-evento[data-design="3"]:hover {
            box-shadow: 0 8px 32px rgba(251,191,36,0.2) !important;
            border-color: #fbbf24 !important;
        }

        .p-evento[data-design="3"] .w-full {
            background: transparent !important;
        }

        .p-evento[data-design="3"] .better-carousel {
            border-radius: 8px;
            margin: 8px;
            height: 165px;
            border: 1px solid #374151;
        }

        .p-evento[data-design="3"] .better-carousel-nav {
            background: rgba(251,191,36,0.9);
            color: #111827;
        }

        .p-evento[data-design="3"] .better-carousel-dot {
            background: rgba(251,191,36,0.4);
        }

        .p-evento[data-design="3"] .better-carousel-dot.active {
            background: #fbbf24;
        }

        .p-evento[data-design="3"] .better-valores-row {
            background: rgba(0,0,0,0.3);
            padding: 10px 12px;
            gap: 6px;
        }

        .p-evento[data-design="3"] .better-valor-item {
            background: rgba(55,65,81,0.8);
            border: 1px solid #4b5563;
            border-radius: 6px;
            padding: 6px 10px;
        }

        .p-evento[data-design="3"] .better-valor-label {
            color: #9ca3af;
            font-size: 9px;
        }

        .p-evento[data-design="3"] .better-valor-amount {
            color: #f9fafb;
            font-size: 12px;
        }

        .p-evento[data-design="3"] .better-valor-item.lance-atual {
            background: linear-gradient(135deg, #78350f 0%, #92400e 100%);
            border-color: #fbbf24;
        }

        .p-evento[data-design="3"] .better-valor-item.lance-atual .better-valor-label {
            color: #fde68a;
        }

        .p-evento[data-design="3"] .better-valor-item.lance-atual .better-valor-amount {
            color: #fbbf24;
        }

        .p-evento[data-design="3"] .better-countdown-row {
            background: transparent;
            padding: 8px 12px;
            border-top: 1px solid #374151;
        }

        .p-evento[data-design="3"] .better-countdown-text {
            color: #9ca3af !important;
        }

        .p-evento[data-design="3"] .better-countdown-time {
            color: #fbbf24 !important;
        }

        /* Dark theme text overrides */
        .p-evento[data-design="3"] .text-sm,
        .p-evento[data-design="3"] .text-xs,
        .p-evento[data-design="3"] .font-semibold {
            color: #f3f4f6 !important;
        }

        .p-evento[data-design="3"] .pi-tag,
        .p-evento[data-design="3"] .pi-building,
        .p-evento[data-design="3"] .pi-map-marker,
        .p-evento[data-design="3"] .pi-star {
            color: #9ca3af !important;
        }

        .p-evento[data-design="3"] .pi-map-marker.better-map-link {
            color: #fbbf24 !important;
        }

        .p-evento[data-design="3"] .native-ref-prefix.lo { color: #60a5fa !important; }
        .p-evento[data-design="3"] .native-ref-prefix.np { color: #fbbf24 !important; }

        /* ============================================ */
        /* VALORES E COUNTDOWN (shared)                */
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

        .better-countdown-row {
            display: flex;
            justify-content: center;
        }

        .better-countdown {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
        }

        .better-countdown-icon {
            font-size: 13px;
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
        /* DESIGN SELECTOR (para preview)              */
        /* ============================================ */

        .better-design-selector {
            position: fixed;
            top: 80px;
            right: 20px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            padding: 16px;
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .better-design-selector h4 {
            margin: 0 0 12px 0;
            font-size: 14px;
            color: #1f2937;
        }

        .better-design-option {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            margin: 4px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            border: 2px solid transparent;
        }

        .better-design-option:hover {
            background: #f3f4f6;
        }

        .better-design-option.active {
            background: #eff6ff;
            border-color: #3b82f6;
        }

        .better-design-option input {
            display: none;
        }

        .better-design-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            border: 2px solid #d1d5db;
        }

        .better-design-option.active .better-design-dot {
            background: #3b82f6;
            border-color: #3b82f6;
        }

        .better-design-name {
            font-size: 13px;
            font-weight: 500;
            color: #374151;
        }

        .better-design-desc {
            font-size: 10px;
            color: #6b7280;
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
    // DESIGN SELECTOR
    // ====================================

    let currentDesign = CONFIG.CARD_DESIGN === 'all' ? 1 : CONFIG.CARD_DESIGN;

    function createDesignSelector() {
        if (CONFIG.CARD_DESIGN !== 'all') return;
        if (document.querySelector('.better-design-selector')) return;

        const selector = document.createElement('div');
        selector.className = 'better-design-selector';
        selector.innerHTML = `
            <h4>🎨 Card Design</h4>
            <label class="better-design-option ${currentDesign === 1 ? 'active' : ''}" data-design="1">
                <input type="radio" name="design" value="1" ${currentDesign === 1 ? 'checked' : ''}>
                <span class="better-design-dot"></span>
                <div>
                    <div class="better-design-name">Minimal Clean</div>
                    <div class="better-design-desc">Branco, limpo, subtil</div>
                </div>
            </label>
            <label class="better-design-option ${currentDesign === 2 ? 'active' : ''}" data-design="2">
                <input type="radio" name="design" value="2" ${currentDesign === 2 ? 'checked' : ''}>
                <span class="better-design-dot"></span>
                <div>
                    <div class="better-design-name">Glassmorphism</div>
                    <div class="better-design-desc">Vidro fosco, gradientes</div>
                </div>
            </label>
            <label class="better-design-option ${currentDesign === 3 ? 'active' : ''}" data-design="3">
                <input type="radio" name="design" value="3" ${currentDesign === 3 ? 'checked' : ''}>
                <span class="better-design-dot"></span>
                <div>
                    <div class="better-design-name">Dark Premium</div>
                    <div class="better-design-desc">Escuro, dourado, premium</div>
                </div>
            </label>
        `;

        selector.querySelectorAll('.better-design-option').forEach(opt => {
            opt.addEventListener('click', () => {
                const design = parseInt(opt.dataset.design);
                currentDesign = design;

                // Update UI
                selector.querySelectorAll('.better-design-option').forEach(o => o.classList.remove('active'));
                opt.classList.add('active');

                // Update all cards
                document.querySelectorAll('.p-evento[data-better-enhanced="true"]').forEach(card => {
                    card.dataset.design = design;
                });

                console.log(`🎨 Design changed to: ${design}`);
            });
        });

        document.body.appendChild(selector);
    }

    // ====================================
    // API
    // ====================================

    async function getEventFromAPI(reference) {
        if (!CONFIG.ENABLE_API_ENRICHMENT) return null;

        try {
            const response = await fetch(`${CONFIG.API_BASE}/events/${reference}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error(`❌ API error for ${reference}:`, error);
        }
        return null;
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
        card.dataset.design = currentDesign;

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
            const hasGPS = apiData.gps && apiData.gps.latitude;
            const nativeMapMarker = card.querySelector('.pi-map-marker');
            if (nativeMapMarker && hasGPS) {
                const mapsUrl = `https://www.google.com/maps?q=${apiData.gps.latitude},${apiData.gps.longitude}`;
                nativeMapMarker.classList.add('better-map-link');
                nativeMapMarker.title = 'Ver no Google Maps';
                nativeMapMarker.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    window.open(mapsUrl, '_blank', 'noopener,noreferrer');
                });
            }

            // Carousel
            const nativeImageDiv = card.querySelector('.p-evento-image');
            if (nativeImageDiv && apiData.imagens && apiData.imagens.length > 0) {
                const images = apiData.imagens.slice(0, CONFIG.MAX_CAROUSEL_IMAGES);

                if (images.length > 1) {
                    nativeImageDiv.style.display = 'none';

                    const carousel = document.createElement('div');
                    carousel.className = 'better-carousel';
                    carousel.innerHTML = `
                        <div class="better-carousel-track">
                            ${images.map(img => `<div class="better-carousel-slide" style="background-image: url('${img}');"></div>`).join('')}
                        </div>
                        <button class="better-carousel-nav prev">‹</button>
                        <button class="better-carousel-nav next">›</button>
                        <div class="better-carousel-dots">
                            ${images.map((_, idx) => `<div class="better-carousel-dot ${idx === 0 ? 'active' : ''}" data-index="${idx}"></div>`).join('')}
                        </div>
                    `;

                    nativeImageDiv.parentNode.insertBefore(carousel, nativeImageDiv.nextSibling);

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

            // Values
            let valoresHTML = '';
            if (apiData.valores) {
                const v = apiData.valores;
                const items = [];
                if (v.valorBase) items.push(`<div class="better-valor-item"><span class="better-valor-label">VB:</span><span class="better-valor-amount">${formatCurrency(v.valorBase)}</span></div>`);
                if (v.valorAbertura) items.push(`<div class="better-valor-item"><span class="better-valor-label">VA:</span><span class="better-valor-amount">${formatCurrency(v.valorAbertura)}</span></div>`);
                if (v.valorMinimo) items.push(`<div class="better-valor-item"><span class="better-valor-label">VM:</span><span class="better-valor-amount">${formatCurrency(v.valorMinimo)}</span></div>`);
                items.push(`<div class="better-valor-item lance-atual"><span class="better-valor-label">Lance:</span><span class="better-valor-amount">${v.lanceAtual ? formatCurrency(v.lanceAtual) : '0 €'}</span></div>`);
                valoresHTML = `<div class="better-valores-row">${items.join('')}</div>`;
            }

            // Countdown
            let countdownHTML = '';
            if (apiData.dataFim) {
                const remaining = calculateTimeRemaining(apiData.dataFim);
                if (remaining) {
                    const countdownId = `countdown-${reference}`;
                    countdownHTML = `
                        <div class="better-countdown-row">
                            <div class="better-countdown">
                                <span class="better-countdown-icon">⏱️</span>
                                <span class="better-countdown-text">Termina:</span>
                                <span class="better-countdown-time ${remaining.isEnding ? 'ending-soon' : ''}" id="${countdownId}" data-end="${apiData.dataFim}">${remaining.text}</span>
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
        console.log('🚀 Better E-Leilões Card Enhancer v6.0');
        console.log('🎨 Design mode:', CONFIG.CARD_DESIGN === 'all' ? 'Preview all 3 designs' : `Design ${CONFIG.CARD_DESIGN}`);

        integrateWithNativeFloatingButtons();
        createDesignSelector();
        enhanceAllCards();

        setInterval(updateAllCountdowns, 1000);

        observer.observe(document.body, { childList: true, subtree: true });

        console.log('✅ Card enhancer v6.0 ativo!');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
