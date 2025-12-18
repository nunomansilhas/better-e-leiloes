// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      5.1
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
        MAX_CAROUSEL_IMAGES: 5
    };

    // ====================================
    // ESTILOS CSS - DESIGN MODERNO
    // ====================================

    const styles = document.createElement('style');
    styles.textContent = `
        /* Override do card nativo */
        .p-evento {
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
            transition: all 0.3s ease !important;
            border: 1px solid #e5e7eb !important;
        }

        .p-evento:hover {
            box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
            transform: translateY(-2px) !important;
        }

        /* Força remover bordas do div nativo */
        .p-evento[data-better-enhanced="true"] .w-full {
            border: none !important;
            border-radius: 0 !important;
        }

        /* Padroniza todas as fontes dentro do card, EXCETO ícones */
        .p-evento[data-better-enhanced="true"],
        .p-evento[data-better-enhanced="true"] *:not([class*="pi-"]):not(i) {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        }

        /* Esconde os elementos nativos que vamos substituir */
        .p-evento[data-better-enhanced="true"] .flex.align-items-center.justify-content-between.mt-2 {
            display: none !important;
        }

        /* Esconde os valores nativos na parte inferior */
        .p-evento[data-better-enhanced="true"] .surface-100.border-round-bottom {
            display: none !important;
        }

        /* ESCONDE o p-tag p-component (badge "Neg. Particular", "Leilão Online", etc) */
        .p-evento[data-better-enhanced="true"] .p-tag.p-component {
            display: none !important;
        }

        /* Centraliza o título do evento */
        .p-evento[data-better-enhanced="true"] .flex.align-items-start.px-3.pt-1 {
            text-align: center;
            justify-content: center;
        }

        .p-evento[data-better-enhanced="true"] .text-sm.font-semibold {
            text-align: center;
            width: 100%;
        }

        /* Colorir primeira parte da referência nativa (LO, NP) */
        .p-evento[data-better-enhanced="true"] .pi-tag + span .native-ref-prefix {
            color: #10b981 !important;
            font-weight: 900 !important;
        }

        .p-evento[data-better-enhanced="true"] .pi-tag + span .native-ref-prefix.lo {
            color: #3b82f6 !important;
        }

        .p-evento[data-better-enhanced="true"] .pi-tag + span .native-ref-prefix.np {
            color: #f59e0b !important;
        }

        /* Fix para links abrirem em nova aba */
        .p-evento a[href*="/evento/"] {
            pointer-events: none !important;
        }

        .p-evento a:not(.better-map-link) {
            cursor: default !important;
        }

        /* Map marker icon - styled and clickable */
        .p-evento[data-better-enhanced="true"] .pi-map-marker.better-map-link {
            color: #3b82f6 !important;
            cursor: pointer !important;
            pointer-events: auto !important;
            transition: all 0.2s ease !important;
            font-size: 14px !important;
        }

        .p-evento[data-better-enhanced="true"] .pi-map-marker.better-map-link:hover {
            color: #1d4ed8 !important;
            transform: scale(1.2) !important;
        }

        /* Header do card - Row 1 */
        .better-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border-bottom: 2px solid #e2e8f0;
        }

        .better-ref-badge {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 6px 12px;
            border-radius: 8px;
            font-weight: 700;
            font-size: 12px;
            letter-spacing: 0.5px;
            box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
        }

        .better-ref-badge .ref-prefix {
            color: #fbbf24;
            font-weight: 800;
        }

        .better-header-actions {
            display: flex !important;
            gap: 8px;
            align-items: center;
            flex-wrap: nowrap;
            visibility: visible !important;
        }

        .better-tipo-badge {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .better-tipo-badge.movel {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        }

        .better-btn {
            background: white;
            border: 1px solid #e5e7eb;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer !important;
            transition: all 0.2s ease;
            display: inline-flex !important;
            align-items: center;
            gap: 4px;
            color: #374151;
            text-decoration: none;
            white-space: nowrap;
            visibility: visible !important;
            opacity: 1 !important;
            z-index: 2 !important;
            position: relative !important;
        }

        .better-btn:hover {
            background: #f9fafb;
            border-color: #d1d5db;
            transform: translateY(-1px);
        }

        .better-btn-primary {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            border: none;
        }

        .better-btn-primary:hover {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        }

        /* Dashboard floating button - matches native PrimeVue style */
        .better-dashboard-btn {
            background: #3b82f6 !important;
            border-color: #3b82f6 !important;
        }

        .better-dashboard-btn:hover {
            background: #2563eb !important;
            border-color: #2563eb !important;
            transform: scale(1.05) !important;
        }

        /* Contador de imagens no carousel */
        .better-image-badge {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            color: white;
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            z-index: 10;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* Carousel de imagens customizado */
        .better-carousel {
            position: relative;
            width: 100%;
            height: 200px;
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
            background-repeat: no-repeat;
        }

        .better-carousel-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px);
            color: white;
            border: none;
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            z-index: 5;
            transition: all 0.2s ease;
        }

        .better-carousel-nav:hover {
            background: rgba(0, 0, 0, 0.7);
            transform: translateY(-50%) scale(1.1);
        }

        .better-carousel-nav.prev {
            left: 8px;
        }

        .better-carousel-nav.next {
            right: 8px;
        }

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
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .better-carousel-dot.active {
            background: white;
            width: 18px;
            border-radius: 3px;
        }

        /* Detalhes - Row 3 */
        .better-details-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 16px;
            background: white;
            border-bottom: 1px solid #f1f5f9;
        }

        .better-icon-box {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            flex-shrink: 0;
        }

        .better-details-info {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .better-detail-item {
            font-size: 12px;
            color: #64748b;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .better-detail-label {
            font-weight: 600;
            color: #374151;
        }

        .better-detail-value {
            color: #1f2937;
            font-weight: 500;
        }

        .better-matricula-badge {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            color: #92400e;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
            border: 1px solid #fbbf24;
        }

        .better-tipologia-badge {
            background: linear-gradient(135deg, #ddd6fe 0%, #c4b5fd 100%);
            color: #5b21b6;
            padding: 4px 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
        }

        /* VALORES COMPACTOS - Linha única */
        .better-valores-row {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            padding: 8px 12px;
            background: #f8fafc;
            justify-content: center;
        }

        .better-valor-item {
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            background: white;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            font-size: 11px;
        }

        .better-valor-item.lance-atual {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-color: #fbbf24;
        }

        .better-valor-item.lance-atual .better-valor-label {
            color: #92400e;
        }

        .better-valor-item.lance-atual .better-valor-amount {
            color: #78350f;
        }

        .better-valor-label {
            font-size: 10px;
            font-weight: 600;
            color: #64748b;
        }

        .better-valor-amount {
            font-size: 11px;
            font-weight: 700;
            color: #1e293b;
        }

        /* Countdown - Row 5 */
        .better-countdown-row {
            padding: 8px 12px;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .better-countdown {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
        }

        .better-countdown-icon {
            font-size: 14px;
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

        /* Localização extra */
        .better-location-row {
            padding: 8px 16px;
            background: #f9fafb;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            align-items: center;
            font-size: 10px;
        }

        .better-location-tag {
            background: #e0f2fe;
            color: #0369a1;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 3px;
        }

        /* GPS Badge */
        .better-gps-badge {
            background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
            color: #1e40af;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

    `;
    document.head.appendChild(styles);

    // ====================================
    // UTILITÁRIOS
    // ====================================

    function formatCurrency(value) {
        if (!value) return '-';
        // Compact format without decimals
        const num = parseFloat(value);
        if (num >= 1000) {
            return new Intl.NumberFormat('pt-PT', {
                maximumFractionDigits: 0
            }).format(num) + ' €';
        }
        return new Intl.NumberFormat('pt-PT', {
            minimumFractionDigits: 0,
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
    // API
    // ====================================

    async function getEventFromAPI(reference) {
        if (!CONFIG.ENABLE_API_ENRICHMENT) return null;

        try {
            console.log(`🔍 Fetching data for ${reference} from ${CONFIG.API_BASE}/events/${reference}`);
            const response = await fetch(`${CONFIG.API_BASE}/events/${reference}`);
            console.log(`📡 Response status: ${response.status}`);
            if (response.ok) {
                const data = await response.json();
                console.log(`✅ Data received for ${reference}:`, data);
                return data;
            } else {
                console.warn(`⚠️ API returned ${response.status} for ${reference}`);
            }
        } catch (error) {
            console.error(`❌ API error for ${reference}:`, error);
        }
        return null;
    }

    // ====================================
    // INTEGRAR COM BOTÕES FLUTUANTES NATIVOS
    // ====================================

    function integrateWithNativeFloatingButtons() {
        // Check if we already added our button
        if (document.querySelector('.better-dashboard-btn')) return;

        // Create dashboard button matching native PrimeVue style (icon-only)
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
        console.log('✅ Created native-style floating dashboard button');
    }

    // ====================================
    // REDESENHAR CARD
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

        // Extract reference before try block so it's accessible in catch
        const reference = extractReferenceFromCard(card);

        try {
            console.log(`🎯 Enhancing card for reference: ${reference}`);
            if (!reference) {
                console.warn('⚠️ No reference found in card');
                return;
            }

            // Busca dados da API
            const apiData = await getEventFromAPI(reference);
            if (!apiData) {
                console.warn(`⚠️ No API data returned for ${reference} - card will not be enhanced`);
                return;
            }
            console.log(`🎨 Starting card enhancement for ${reference}`);

            // URL do evento
            const eventUrl = `https://www.e-leiloes.pt/evento/${reference}`;

            // ===== LIMPA CARD E RECONSTRÓI =====
            card.style.position = 'relative';

            // Remove COMPLETAMENTE os links nativos
            const nativeLinks = card.querySelectorAll('a[href*="/evento/"]');
            nativeLinks.forEach(link => {
                link.removeAttribute('href');
                link.style.cursor = 'default';
                link.style.pointerEvents = 'none';
                // Previne navegação
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                });
            });

            // ===== COLORIR PRIMEIRA PARTE DA REFERÊNCIA NATIVA (LO/NP) =====
            const nativeRefSpan = card.querySelector('.pi-tag + span');
            if (nativeRefSpan && reference) {
                const refText = nativeRefSpan.textContent.trim();
                const prefix = refText.substring(0, 2);
                const rest = refText.substring(2);
                const prefixClass = prefix.toLowerCase();
                nativeRefSpan.innerHTML = `<span class="native-ref-prefix ${prefixClass}">${prefix}</span>${rest}`;
                console.log(`🎨 Native reference colored: ${prefix} (${prefixClass})`);
            }

            // ===== REMOVE CLASSES DE BORDA DO DIV NATIVO =====
            const nativeCardBodies = card.querySelectorAll('.w-full');
            nativeCardBodies.forEach(div => {
                div.classList.remove('border-1', 'surface-border', 'border-round');
                div.style.border = 'none';
                div.style.borderRadius = '0';
            });

            // ===== ESTILIZAR ÍCONE DE MAPA NATIVO (pi-map-marker) =====
            const hasGPS = apiData.gps && apiData.gps.latitude;
            const nativeMapMarker = card.querySelector('.pi-map-marker');

            if (nativeMapMarker && hasGPS) {
                const mapsUrl = `https://www.google.com/maps?q=${apiData.gps.latitude},${apiData.gps.longitude}`;
                console.log(`🗺️ Styling native map marker with coords: ${apiData.gps.latitude}, ${apiData.gps.longitude}`);

                // Add our class for styling
                nativeMapMarker.classList.add('better-map-link');
                nativeMapMarker.title = 'Ver no Google Maps';
                nativeMapMarker.style.cursor = 'pointer';

                // Make the parent container clickable if it exists
                const mapContainer = nativeMapMarker.closest('.flex.align-items-center.gap-1');
                if (mapContainer) {
                    mapContainer.style.cursor = 'pointer';
                }

                // Add click handler
                nativeMapMarker.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    window.open(mapsUrl, '_blank', 'noopener,noreferrer');
                    console.log('🗺️ Map marker clicked - opening Maps in new tab');
                    return false;
                });

                console.log('✅ Native map marker styled and made clickable');
            }

            // ===== ROW 2: CAROUSEL DE IMAGENS =====
            const nativeImageDiv = card.querySelector('.p-evento-image');
            if (nativeImageDiv && apiData.imagens && apiData.imagens.length > 0) {
                // Limit to max 5 images
                const images = apiData.imagens.slice(0, CONFIG.MAX_CAROUSEL_IMAGES);

                if (images.length > 1) {
                    console.log(`🎠 Creating carousel with ${images.length} images (max ${CONFIG.MAX_CAROUSEL_IMAGES})`);

                    // Create carousel to replace native image
                    const carouselHTML = `
                        <div class="better-carousel" data-current="0">
                            <div class="better-carousel-track">
                                ${images.map(img => `
                                    <div class="better-carousel-slide" style="background-image: url('${img}');"></div>
                                `).join('')}
                            </div>
                            <button class="better-carousel-nav prev">‹</button>
                            <button class="better-carousel-nav next">›</button>
                            <div class="better-carousel-dots">
                                ${images.map((_, idx) => `
                                    <div class="better-carousel-dot ${idx === 0 ? 'active' : ''}" data-index="${idx}"></div>
                                `).join('')}
                            </div>
                            <div class="better-image-badge">📷 ${apiData.imagens.length}</div>
                        </div>
                    `;

                    // Replace native image with carousel
                    const carouselDiv = document.createElement('div');
                    carouselDiv.innerHTML = carouselHTML;

                    // Check if parentNode exists before replacing
                    if (nativeImageDiv.parentNode) {
                        nativeImageDiv.parentNode.replaceChild(carouselDiv.firstChild, nativeImageDiv);

                        // Add event handlers for the carousel
                        const carousel = card.querySelector('.better-carousel');
                        if (carousel) {
                            const track = carousel.querySelector('.better-carousel-track');
                            const prevBtn = carousel.querySelector('.better-carousel-nav.prev');
                            const nextBtn = carousel.querySelector('.better-carousel-nav.next');
                            const dots = carousel.querySelectorAll('.better-carousel-dot');

                            let currentSlide = 0;
                            const totalSlides = images.length;

                            function updateCarousel() {
                                if (track) {
                                    track.style.transform = `translateX(-${currentSlide * 100}%)`;
                                }
                                dots.forEach((dot, idx) => {
                                    dot.classList.toggle('active', idx === currentSlide);
                                });
                            }

                            if (prevBtn) {
                                prevBtn.addEventListener('click', (e) => {
                                    e.stopPropagation();
                                    e.preventDefault();
                                    currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
                                    updateCarousel();
                                });
                            }

                            if (nextBtn) {
                                nextBtn.addEventListener('click', (e) => {
                                    e.stopPropagation();
                                    e.preventDefault();
                                    currentSlide = (currentSlide + 1) % totalSlides;
                                    updateCarousel();
                                });
                            }

                            dots.forEach((dot, idx) => {
                                dot.addEventListener('click', (e) => {
                                    e.stopPropagation();
                                    e.preventDefault();
                                    currentSlide = idx;
                                    updateCarousel();
                                });
                            });

                            console.log('✅ Carousel created and configured');
                        } else {
                            console.warn('⚠️ Carousel element not found after insertion');
                        }
                    } else {
                        console.warn('⚠️ Native image div has no parent node');
                    }
                } else {
                    // Single image - just add badge showing total from API
                    nativeImageDiv.style.position = 'relative';
                    const imageBadge = document.createElement('div');
                    imageBadge.className = 'better-image-badge';
                    imageBadge.innerHTML = `📷 ${apiData.imagens.length}`;
                    nativeImageDiv.appendChild(imageBadge);
                }
            }

            // ===== ROW 3: DETALHES (APENAS MATRÍCULA PARA MÓVEIS) =====
            const det = apiData.detalhes || {};

            let detailsHTML = '';
            if (apiData.tipoEvento === 'movel' && det.matricula) {
                detailsHTML = `
                    <div class="better-details-row">
                        <div class="better-details-info">
                            <div class="better-matricula-badge">🚙 ${det.matricula}</div>
                        </div>
                    </div>
                `;
            }

            // ===== ROW 4: VALORES COMPACTOS =====
            let valoresHTML = '';
            if (apiData.valores) {
                const v = apiData.valores;
                const items = [];

                if (v.valorBase) {
                    items.push(`<div class="better-valor-item"><span class="better-valor-label">VB:</span><span class="better-valor-amount">${formatCurrency(v.valorBase)}</span></div>`);
                }
                if (v.valorAbertura) {
                    items.push(`<div class="better-valor-item"><span class="better-valor-label">VA:</span><span class="better-valor-amount">${formatCurrency(v.valorAbertura)}</span></div>`);
                }
                if (v.valorMinimo) {
                    items.push(`<div class="better-valor-item"><span class="better-valor-label">VM:</span><span class="better-valor-amount">${formatCurrency(v.valorMinimo)}</span></div>`);
                }
                // Lance atual sempre visível
                items.push(`<div class="better-valor-item lance-atual"><span class="better-valor-label">Lance:</span><span class="better-valor-amount">${v.lanceAtual ? formatCurrency(v.lanceAtual) : '0 €'}</span></div>`);

                valoresHTML = `<div class="better-valores-row">${items.join('')}</div>`;
            }

            // ===== ROW 5: COUNTDOWN OU DATAS =====
            let countdownHTML = '';
            if (apiData.dataFim) {
                const remaining = calculateTimeRemaining(apiData.dataFim);
                if (remaining) {
                    const now = new Date();
                    const end = new Date(apiData.dataFim);
                    const start = apiData.dataInicio ? new Date(apiData.dataInicio) : null;
                    const diffDays = Math.floor((end - now) / (1000 * 60 * 60 * 24));

                    // Se mais de 1 dia, mostra as datas
                    if (diffDays > 1 && start) {
                        const formatDate = (date) => {
                            return new Intl.DateTimeFormat('pt-PT', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                            }).format(date);
                        };

                        countdownHTML = `
                            <div class="better-countdown-row">
                                <div class="better-countdown">
                                    <span class="better-countdown-icon">📅</span>
                                    <span class="better-countdown-text">De:</span>
                                    <span class="better-countdown-time">${formatDate(start)}</span>
                                    <span class="better-countdown-text">a:</span>
                                    <span class="better-countdown-time">${formatDate(end)}</span>
                                </div>
                            </div>
                        `;
                    } else {
                        // Menos de 1 dia, mostra countdown LIVE
                        const countdownId = `countdown-${reference}`;
                        countdownHTML = `
                            <div class="better-countdown-row">
                                <div class="better-countdown">
                                    <span class="better-countdown-icon">⏱️</span>
                                    <span class="better-countdown-text">Termina em:</span>
                                    <span class="better-countdown-time ${remaining.isEnding ? 'ending-soon' : ''}"
                                          id="${countdownId}"
                                          data-end="${apiData.dataFim}">
                                        ${remaining.text}
                                    </span>
                                </div>
                            </div>
                        `;
                    }
                }
            }

            // Insere rows no card
            const cardBody = card.querySelector('.w-full');
            if (cardBody) {
                const newContent = detailsHTML + valoresHTML + countdownHTML;

                // Adiciona o conteúdo DEPOIS do conteúdo nativo
                const contentWrapper = document.createElement('div');
                contentWrapper.className = 'better-card-content';
                contentWrapper.innerHTML = newContent;
                cardBody.appendChild(contentWrapper);
                console.log('✅ Card body updated');
            }

            // ===== EVENT HANDLERS =====
            // Click no card inteiro abre em nova aba
            card.style.cursor = 'pointer';

            card.addEventListener('click', (e) => {
                // Ignore clicks on specific elements
                if (e.target.closest('.pi-map-marker') ||
                    e.target.closest('.better-map-link') ||
                    e.target.closest('.pi-star') ||
                    e.target.closest('.better-btn') ||
                    e.target.closest('.better-carousel-nav') ||
                    e.target.closest('.better-carousel-dot')) {
                    return;
                }

                e.preventDefault();
                e.stopPropagation();
                window.open(eventUrl, '_blank', 'noopener,noreferrer');
                return false;
            }, true);

            // Middle-click handler
            card.addEventListener('auxclick', (e) => {
                if (e.button === 1) {
                    e.preventDefault();
                    e.stopPropagation();
                    window.open(eventUrl, '_blank', 'noopener,noreferrer');
                    return false;
                }
            }, true);

            console.log(`✨ Card enhancement complete for ${reference}`);

        } catch (error) {
            console.error(`❌ Error enhancing card for ${reference}:`, error);
            console.error('Error stack:', error.stack);
        }
    }

    // ====================================
    // OBSERVADOR
    // ====================================

    function enhanceAllCards() {
        const cards = document.querySelectorAll('.p-evento');
        cards.forEach(card => enhanceCard(card));
    }

    const observer = new MutationObserver(() => {
        enhanceAllCards();
        integrateWithNativeFloatingButtons();
    });

    // ====================================
    // LIVE COUNTDOWN TIMER
    // ====================================

    function updateAllCountdowns() {
        const countdownElements = document.querySelectorAll('[data-end]');
        countdownElements.forEach(el => {
            const endDate = el.dataset.end;
            if (endDate) {
                const remaining = calculateTimeRemaining(endDate);
                if (remaining) {
                    el.textContent = remaining.text;
                    if (remaining.isEnding) {
                        el.classList.add('ending-soon');
                    } else {
                        el.classList.remove('ending-soon');
                    }
                }
            }
        });
    }

    // ====================================
    // INICIALIZAÇÃO
    // ====================================

    function init() {
        console.log('🚀 Better E-Leilões Card Enhancer v5.1');

        integrateWithNativeFloatingButtons();
        enhanceAllCards();

        // Start live countdown updates every second
        setInterval(updateAllCountdowns, 1000);
        console.log('⏱️ Live countdown timer started');

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('✅ Card enhancer v5.1 ativo - Native-style floating button, fixed carousel!');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
