// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      10.0
// @description  Melhorias subtis aos cards - botões de ação, carousel, fontes consistentes
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
        MAX_CAROUSEL_IMAGES: 10
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
    // ESTILOS CSS - SUBTIL E LIMPO
    // ====================================

    const styles = document.createElement('style');
    styles.textContent = `
        /* ============================================ */
        /* MELHORIAS SUBTIS AOS CARDS                  */
        /* ============================================ */

        .p-evento {
            transition: all 0.3s ease !important;
        }

        .p-evento:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 8px 25px rgba(0,0,0,0.12) !important;
        }

        .p-evento[data-better-enhanced="true"] {
            position: relative !important;
        }

        /* Fonte consistente em todo o card */
        .p-evento[data-better-enhanced="true"] * {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* Hide context menu */
        .p-contextmenu.p-component {
            display: none !important;
        }

        /* ============================================ */
        /* BOTÕES DE AÇÃO - BONITOS E FUNCIONAIS       */
        /* ============================================ */

        .better-action-bar {
            position: absolute;
            top: 8px;
            right: 8px;
            display: flex;
            gap: 6px;
            z-index: 20;
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        .p-evento:hover .better-action-bar {
            opacity: 1;
        }

        .better-btn {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            backdrop-filter: blur(8px);
        }

        .better-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        }

        .better-btn.favorite {
            background: rgba(255,255,255,0.95);
            color: #d1d5db;
        }

        .better-btn.favorite:hover {
            color: #ef4444;
        }

        .better-btn.favorite.active {
            background: #fef2f2;
            color: #ef4444;
        }

        .better-btn.map {
            background: rgba(59, 130, 246, 0.95);
            color: white;
        }

        .better-btn.map:hover {
            background: #2563eb;
        }

        .better-btn.refresh {
            background: rgba(16, 185, 129, 0.95);
            color: white;
        }

        .better-btn.refresh:hover {
            background: #059669;
        }

        .better-btn.sync {
            background: rgba(139, 92, 246, 0.95);
            color: white;
        }

        .better-btn.sync:hover {
            background: #7c3aed;
        }

        .better-btn.dashboard {
            background: rgba(59, 130, 246, 0.95);
            color: white;
        }

        .better-btn.loading {
            pointer-events: none;
            opacity: 0.7;
        }

        .better-btn.loading::after {
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
        /* CAROUSEL DE IMAGENS                         */
        /* ============================================ */

        .better-carousel {
            position: relative;
            width: 100%;
            height: 100%;
            overflow: hidden;
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
            background: rgba(0, 0, 0, 0.5);
            color: white;
            border: none;
            width: 30px;
            height: 30px;
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
        }

        .better-carousel-nav.prev { left: 8px; }
        .better-carousel-nav.next { right: 8px; }

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

        .better-carousel-dots {
            position: absolute;
            bottom: 8px;
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

        .better-carousel-dot:hover,
        .better-carousel-dot.active {
            background: white;
        }

        .better-carousel-dot.active {
            width: 18px;
            border-radius: 3px;
        }

        /* ============================================ */
        /* BADGE DE URGÊNCIA                           */
        /* ============================================ */

        .better-urgency-badge {
            position: absolute;
            top: 8px;
            left: 8px;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            z-index: 15;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }

        .better-urgency-badge.critical {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
            animation: pulse-badge 1s infinite;
        }

        .better-urgency-badge.ending-soon {
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
        }

        @keyframes pulse-badge {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
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
        }

        .better-lightbox-close {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 44px;
            height: 44px;
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
    `;
    document.head.appendChild(styles);

    // ====================================
    // UTILITÁRIOS
    // ====================================

    function calculateTimeRemaining(endDate) {
        if (!endDate) return null;

        const now = new Date();
        const end = new Date(endDate);
        const diff = end - now;

        if (diff <= 0) return null;

        const totalHours = diff / (1000 * 60 * 60);
        return {
            hours: totalHours,
            isCritical: totalHours < 1,
            isEndingSoon: totalHours < 24
        };
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
            if (img) img.src = lightboxImages[lightboxIndex];
            if (counter) counter.textContent = `${lightboxIndex + 1} / ${lightboxImages.length}`;
        }
        if (e.key === 'ArrowRight') {
            lightboxIndex = (lightboxIndex + 1) % lightboxImages.length;
            if (img) img.src = lightboxImages[lightboxIndex];
            if (counter) counter.textContent = `${lightboxIndex + 1} / ${lightboxImages.length}`;
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
    // CARD ENHANCEMENT - SUBTIL
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
            const hasData = apiData && !apiData._notFound;

            // Add action buttons bar
            addActionBar(card, reference, hasData, apiData);

            if (!hasData) return; // Keep original card if no data

            const eventUrl = `https://www.e-leiloes.pt/evento/${reference}`;

            // Add urgency badge if needed
            if (apiData.data_fim) {
                const timeInfo = calculateTimeRemaining(apiData.data_fim);
                if (timeInfo && (timeInfo.isCritical || timeInfo.isEndingSoon)) {
                    const badge = document.createElement('div');
                    badge.className = `better-urgency-badge ${timeInfo.isCritical ? 'critical' : 'ending-soon'}`;
                    badge.textContent = timeInfo.isCritical ? '🔥 < 1h' : '⏰ < 24h';
                    card.appendChild(badge);
                }
            }

            // Add carousel if we have images
            const nativeImageDiv = card.querySelector('.p-evento-image');
            if (nativeImageDiv && apiData.imagens && apiData.imagens.length > 0) {
                const images = apiData.imagens.slice(0, CONFIG.MAX_CAROUSEL_IMAGES);

                // Create carousel inside native image container
                const carousel = document.createElement('div');
                carousel.className = 'better-carousel';
                carousel.innerHTML = `
                    <div class="better-carousel-track">
                        ${images.map((img, idx) => `<div class="better-carousel-slide" style="background-image: url('${img}');" data-index="${idx}"></div>`).join('')}
                    </div>
                    ${images.length > 1 ? `
                        <button class="better-carousel-nav prev">‹</button>
                        <button class="better-carousel-nav next">›</button>
                        <div class="better-carousel-dots">
                            ${images.map((_, idx) => `<div class="better-carousel-dot ${idx === 0 ? 'active' : ''}" data-index="${idx}"></div>`).join('')}
                        </div>
                    ` : ''}
                    <div class="better-carousel-counter">${images.length} 📷</div>
                `;

                // Replace native image content
                nativeImageDiv.innerHTML = '';
                nativeImageDiv.appendChild(carousel);

                // Carousel navigation
                if (images.length > 1) {
                    const track = carousel.querySelector('.better-carousel-track');
                    const dots = carousel.querySelectorAll('.better-carousel-dot');
                    let currentSlide = 0;

                    function updateCarousel() {
                        track.style.transform = `translateX(-${currentSlide * 100}%)`;
                        dots.forEach((d, i) => d.classList.toggle('active', i === currentSlide));
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

                    dots.forEach((dot, idx) => {
                        dot.addEventListener('click', (e) => {
                            e.stopPropagation();
                            currentSlide = idx;
                            updateCarousel();
                        });
                    });
                }

                // Lightbox on click
                carousel.querySelectorAll('.better-carousel-slide').forEach((slide, idx) => {
                    slide.addEventListener('click', (e) => {
                        e.stopPropagation();
                        openLightbox(images, idx);
                    });
                });
            }

            // Make card clickable
            card.style.cursor = 'pointer';
            card.addEventListener('click', (e) => {
                if (e.target.closest('.better-btn, .better-carousel-nav, .better-carousel-dot, .better-carousel-slide')) return;
                window.open(eventUrl, '_blank');
            });

        } catch (error) {
            console.error(`❌ Error enhancing card for ${reference}:`, error);
        }
    }

    function addActionBar(card, reference, hasData, apiData) {
        const bar = document.createElement('div');
        bar.className = 'better-action-bar';

        // Favorite button
        const isFav = favorites.includes(reference);
        const favBtn = document.createElement('button');
        favBtn.className = `better-btn favorite ${isFav ? 'active' : ''}`;
        favBtn.title = isFav ? 'Remover dos favoritos' : 'Adicionar aos favoritos';
        favBtn.innerHTML = isFav ? '❤️' : '🤍';
        favBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const nowFav = toggleFavorite(reference);
            favBtn.classList.toggle('active', nowFav);
            favBtn.innerHTML = nowFav ? '❤️' : '🤍';
            favBtn.title = nowFav ? 'Remover dos favoritos' : 'Adicionar aos favoritos';
        });
        bar.appendChild(favBtn);

        // Map button (if has GPS)
        if (hasData && apiData.latitude && apiData.longitude) {
            const mapBtn = document.createElement('button');
            mapBtn.className = 'better-btn map';
            mapBtn.title = 'Ver no Google Maps';
            mapBtn.innerHTML = '📍';
            mapBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                window.open(`https://www.google.com/maps?q=${apiData.latitude},${apiData.longitude}`, '_blank');
            });
            bar.appendChild(mapBtn);
        }

        if (hasData) {
            // Refresh button
            const refreshBtn = document.createElement('button');
            refreshBtn.className = 'better-btn refresh';
            refreshBtn.title = 'Atualizar dados';
            refreshBtn.innerHTML = '🔄';
            refreshBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                refreshBtn.classList.add('loading');
                refreshBtn.innerHTML = '';

                const success = await triggerScrape(reference);
                refreshBtn.classList.remove('loading');
                refreshBtn.innerHTML = success ? '✅' : '❌';
                setTimeout(() => { refreshBtn.innerHTML = '🔄'; }, 2000);

                if (success) {
                    setTimeout(() => location.reload(), 2500);
                }
            });
            bar.appendChild(refreshBtn);
        }

        // Sync button
        const syncBtn = document.createElement('button');
        syncBtn.className = 'better-btn sync';
        syncBtn.title = hasData ? 'Sincronizar' : 'Adicionar à BD';
        syncBtn.innerHTML = '⬇️';
        syncBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            syncBtn.classList.add('loading');
            syncBtn.innerHTML = '';

            const success = await triggerScrape(reference);
            syncBtn.classList.remove('loading');
            syncBtn.innerHTML = success ? '✅' : '❌';
            setTimeout(() => { syncBtn.innerHTML = '⬇️'; }, 2000);

            if (success && !hasData) {
                setTimeout(() => location.reload(), 2500);
            }
        });
        bar.appendChild(syncBtn);

        card.appendChild(bar);
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

    function init() {
        console.log('🚀 Better E-Leilões v10.0 - Melhorias subtis');

        integrateWithNativeFloatingButtons();
        enhanceAllCards();

        observer.observe(document.body, { childList: true, subtree: true });

        console.log('✅ v10.0 - Botões bonitos, carousel, favoritos, GPS!');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
