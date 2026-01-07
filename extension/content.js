/**
 * Better E-Leilões - Card Enhancer
 * Chrome Extension Version 11.1
 * Converted from Tampermonkey userscript
 */

(function() {
    'use strict';

    // ====================================
    // CONFIGURATION (loaded from chrome.storage)
    // ====================================

    let CONFIG = {
        API_BASE: 'http://localhost:8000/api',
        DASHBOARD_URL: 'http://localhost:8000',
        ENABLE_API_ENRICHMENT: true,
        MAX_CAROUSEL_IMAGES: 10
    };

    // Load configuration from chrome.storage
    async function loadConfig() {
        return new Promise((resolve) => {
            if (typeof chrome !== 'undefined' && chrome.storage) {
                chrome.storage.sync.get({
                    apiUrl: 'http://localhost:8000',
                    enableApiEnrichment: true,
                    maxCarouselImages: 10
                }, (items) => {
                    CONFIG.API_BASE = items.apiUrl + '/api';
                    CONFIG.DASHBOARD_URL = items.apiUrl;
                    CONFIG.ENABLE_API_ENRICHMENT = items.enableApiEnrichment;
                    CONFIG.MAX_CAROUSEL_IMAGES = items.maxCarouselImages;
                    resolve();
                });
            } else {
                resolve();
            }
        });
    }

    // ====================================
    // UTILITIES
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
    // API (using fetch instead of GM_xmlhttpRequest)
    // ====================================

    // Cache for batch-fetched events
    let eventsCache = {};

    // Batch fetch multiple events in ONE request
    async function getEventsBatch(references) {
        if (!CONFIG.ENABLE_API_ENRICHMENT || references.length === 0) return {};

        try {
            const response = await fetch(`${CONFIG.API_BASE}/events/batch`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ references })
            });

            if (response.status === 200) {
                const data = await response.json();
                // Cache all events
                Object.assign(eventsCache, data.events);
                // Mark not found
                data.not_found.forEach(ref => {
                    eventsCache[ref] = { _notFound: true };
                });
                return data.events;
            }
            return {};
        } catch (error) {
            console.error('❌ Batch API error:', error);
            return {};
        }
    }

    // Get single event (from cache or individual request)
    async function getEventFromAPI(reference) {
        if (!CONFIG.ENABLE_API_ENRICHMENT) return null;

        // Check cache first
        if (eventsCache[reference]) {
            return eventsCache[reference];
        }

        try {
            const response = await fetch(`${CONFIG.API_BASE}/events/${reference}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (response.status === 200) {
                const event = await response.json();
                eventsCache[reference] = event;
                return event;
            } else if (response.status === 404) {
                eventsCache[reference] = { _notFound: true };
                return { _notFound: true };
            } else {
                return null;
            }
        } catch (error) {
            console.error(`❌ API error for ${reference}:`, error);
            return null;
        }
    }

    // Scrape event via backend (uses official API + saves to DB)
    async function scrapeEventViaBackend(reference) {
        try {
            const response = await fetch(`${CONFIG.API_BASE}/scrape/stage2/api?references=${reference}&save_to_db=true`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (response.status === 200) {
                const data = await response.json();
                return data.events && data.events.length > 0 ? data.events[0] : null;
            } else {
                console.error(`❌ Scrape failed for ${reference}:`, response.status);
                return null;
            }
        } catch (error) {
            console.error(`❌ Scrape error for ${reference}:`, error);
            return null;
        }
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

    // SYNC version - uses cached data directly, no await
    function enhanceCardSync(card, apiData) {
        if (card.dataset.betterEnhanced) return;
        card.dataset.betterEnhanced = 'true';

        const reference = extractReferenceFromCard(card);
        if (!reference) return;

        // If no data, just add sync button
        if (!apiData || apiData._notFound) {
            addActionButtons(card, reference, false, null);
            return;
        }

        const eventUrl = `https://www.e-leiloes.pt/evento/${reference}`;
        card.style.position = 'relative';

        // Add action buttons
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

        // Style map marker
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

        // Carousel
        const nativeImageDiv = card.querySelector('.p-evento-image');
        const images = (apiData.fotos || [])
            .slice(0, CONFIG.MAX_CAROUSEL_IMAGES)
            .map(f => f.image || f.thumbnail || f)
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

            // Lightbox
            carousel.querySelectorAll('.better-carousel-slide').forEach((slide, idx) => {
                slide.addEventListener('click', (e) => {
                    e.stopPropagation();
                    openLightbox(images, idx);
                });
            });
        }

        // Values
        let valuesHTML = '';
        if (apiData.valor_base) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VB</span><span class="better-value-amount">${formatCurrency(apiData.valor_base)}</span></div>`;
        if (apiData.valor_abertura) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VA</span><span class="better-value-amount">${formatCurrency(apiData.valor_abertura)}</span></div>`;
        if (apiData.valor_minimo) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VM</span><span class="better-value-amount">${formatCurrency(apiData.valor_minimo)}</span></div>`;
        valuesHTML += `<div class="better-value-row highlight"><span class="better-value-label">Lance</span><span class="better-value-amount">${apiData.lance_atual ? formatCurrency(apiData.lance_atual) : '0 €'}</span></div>`;

        // Details
        let detailsHTML = '';
        const tipoId = apiData.tipo_id || 0;
        const isImovel = tipoId === 1 || (apiData.tipo && apiData.tipo.toLowerCase().includes('imov'));
        const isVeiculo = tipoId === 2 || (apiData.tipo && (apiData.tipo.toLowerCase().includes('veic') || apiData.tipo.toLowerCase().includes('auto')));

        if (isImovel) {
            if (apiData.tipologia) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipologia}</span></div>`;
            if (apiData.area_util) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Área</span><span class="better-detail-value">${apiData.area_util} m²</span></div>`;
            else if (apiData.area_bruta) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Área</span><span class="better-detail-value">${apiData.area_bruta} m²</span></div>`;
            if (apiData.subtipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Subtipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
        } else if (isVeiculo) {
            if (apiData.matricula) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Matrícula</span><span class="better-detail-value">${apiData.matricula}</span></div>`;
            if (apiData.marca) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Marca</span><span class="better-detail-value">${apiData.marca}</span></div>`;
            if (apiData.modelo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Modelo</span><span class="better-detail-value">${apiData.modelo}</span></div>`;
            if (apiData.subtipo && !apiData.marca) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
        } else {
            if (apiData.subtipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Subtipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
            if (apiData.tipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipo}</span></div>`;
        }

        if (apiData.concelho) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Local</span><span class="better-detail-value" title="${apiData.concelho}${apiData.distrito ? ', ' + apiData.distrito : ''}">${apiData.concelho}</span></div>`;
        else if (apiData.distrito) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Distrito</span><span class="better-detail-value">${apiData.distrito}</span></div>`;

        if (!detailsHTML && apiData.tipo) {
            detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipo}</span></div>`;
        }

        const valoresHTML = `<div class="better-content-grid"><div class="better-values-col">${valuesHTML}</div><div class="better-details-col">${detailsHTML}</div></div>`;

        // Countdown
        let countdownHTML = '';
        if (apiData.data_fim) {
            const remaining = calculateTimeRemaining(apiData.data_fim);
            if (remaining) {
                countdownHTML = `
                    <div class="better-countdown-row">
                        <div class="better-countdown">
                            <span class="better-countdown-icon">⏱️</span>
                            <span class="better-countdown-text">Termina:</span>
                            <span class="better-countdown-time ${remaining.isEnding ? 'ending-soon' : ''}" data-end="${apiData.data_fim}">${remaining.text}</span>
                        </div>
                    </div>
                `;
            }
        }

        // Insert content
        const wrapper = document.createElement('div');
        wrapper.className = 'better-card-content';
        wrapper.innerHTML = valoresHTML + countdownHTML;
        card.appendChild(wrapper);

        // Click handler
        card.style.cursor = 'pointer';
        card.addEventListener('click', (e) => {
            if (e.target.closest('.pi-map-marker, .better-carousel-nav, .better-carousel-dot, .better-carousel-slide, .pi-star, .better-action-btn')) return;
            e.preventDefault();
            e.stopPropagation();
            window.open(eventUrl, '_blank', 'noopener,noreferrer');
        }, true);

        card.addEventListener('contextmenu', (e) => {
            e.stopPropagation();
        }, true);
    }

    // Legacy async version for individual card refresh
    async function enhanceCard(card) {
        if (card.dataset.betterEnhanced) return;
        card.dataset.betterEnhanced = 'true';

        const reference = extractReferenceFromCard(card);

        try {
            if (!reference) return;

            const apiData = await getEventFromAPI(reference);

            // If API returned 404 or null, keep original card but add action buttons
            if (!apiData || apiData._notFound) {
                addActionButtons(card, reference, false, null);
                return;
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

            // Style map marker
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

            // Carousel - show all images from fotos field
            const nativeImageDiv = card.querySelector('.p-evento-image');
            const images = (apiData.fotos || [])
                .slice(0, CONFIG.MAX_CAROUSEL_IMAGES)
                .map(f => f.image || f.thumbnail || f)
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

            // Values - Side-by-side layout
            let valuesHTML = '';
            if (apiData.valor_base) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VB</span><span class="better-value-amount">${formatCurrency(apiData.valor_base)}</span></div>`;
            if (apiData.valor_abertura) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VA</span><span class="better-value-amount">${formatCurrency(apiData.valor_abertura)}</span></div>`;
            if (apiData.valor_minimo) valuesHTML += `<div class="better-value-row"><span class="better-value-label">VM</span><span class="better-value-amount">${formatCurrency(apiData.valor_minimo)}</span></div>`;
            valuesHTML += `<div class="better-value-row highlight"><span class="better-value-label">Lance</span><span class="better-value-amount">${apiData.lance_atual ? formatCurrency(apiData.lance_atual) : '0 €'}</span></div>`;

            // Details based on event type
            let detailsHTML = '';
            const tipoId = apiData.tipo_id || 0;
            const isImovel = tipoId === 1 || (apiData.tipo && apiData.tipo.toLowerCase().includes('imov'));
            const isVeiculo = tipoId === 2 || (apiData.tipo && (apiData.tipo.toLowerCase().includes('veic') || apiData.tipo.toLowerCase().includes('auto')));

            if (isImovel) {
                if (apiData.tipologia) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipologia}</span></div>`;
                if (apiData.area_util) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Área</span><span class="better-detail-value">${apiData.area_util} m²</span></div>`;
                else if (apiData.area_bruta) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Área</span><span class="better-detail-value">${apiData.area_bruta} m²</span></div>`;
                if (apiData.subtipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Subtipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
            } else if (isVeiculo) {
                if (apiData.matricula) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Matrícula</span><span class="better-detail-value">${apiData.matricula}</span></div>`;
                if (apiData.marca) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Marca</span><span class="better-detail-value">${apiData.marca}</span></div>`;
                if (apiData.modelo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Modelo</span><span class="better-detail-value">${apiData.modelo}</span></div>`;
                if (apiData.subtipo && !apiData.marca) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
            } else {
                if (apiData.subtipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Subtipo</span><span class="better-detail-value">${apiData.subtipo}</span></div>`;
                if (apiData.tipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipo}</span></div>`;
            }

            if (apiData.concelho) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Local</span><span class="better-detail-value" title="${apiData.concelho}${apiData.distrito ? ', ' + apiData.distrito : ''}">${apiData.concelho}</span></div>`;
            else if (apiData.distrito) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Distrito</span><span class="better-detail-value">${apiData.distrito}</span></div>`;

            if (!detailsHTML) {
                if (apiData.tipo) detailsHTML += `<div class="better-detail-row"><span class="better-detail-label">Tipo</span><span class="better-detail-value">${apiData.tipo}</span></div>`;
            }

            const valoresHTML = `<div class="better-content-grid"><div class="better-values-col">${valuesHTML}</div><div class="better-details-col">${detailsHTML}</div></div>`;

            // Countdown
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
            const wrapper = document.createElement('div');
            wrapper.className = 'better-card-content';
            wrapper.innerHTML = valoresHTML + countdownHTML;
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

        // Map button
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

        // Refresh button
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

                setTimeout(async () => {
                    refreshBtn.innerHTML = '<i class="pi pi-sync"></i>';
                    delete card.dataset.betterEnhanced;
                    card.querySelectorAll('.better-carousel, .better-card-content, .better-action-buttons').forEach(el => el.remove());
                    const nativeImg = card.querySelector('.p-evento-image');
                    if (nativeImg) nativeImg.style.display = '';
                    await enhanceCard(card);
                }, 1000);
            } else {
                refreshBtn.classList.remove('loading');
                refreshBtn.innerHTML = '<i class="pi pi-times"></i>';
                setTimeout(() => { refreshBtn.innerHTML = '<i class="pi pi-sync"></i>'; }, 2000);
            }
        });
        buttonsDiv.appendChild(refreshBtn);

        // Find native star's container
        const nativeStar = card.querySelector('.pi-star');
        if (nativeStar && nativeStar.parentElement) {
            nativeStar.parentElement.appendChild(buttonsDiv);
        } else {
            const headerArea = card.querySelector('.flex.align-items-center.gap-1') || card.querySelector('.w-full:first-of-type');
            if (headerArea) {
                headerArea.appendChild(buttonsDiv);
            } else {
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

    // Process cards - INSTANT with batch fetch + sync enhancement
    async function enhanceAllCards() {
        const cards = Array.from(document.querySelectorAll('.p-evento:not([data-better-enhanced])'));
        if (cards.length === 0) return;

        const startTime = performance.now();

        // Step 1: Extract all references
        const references = [];
        cards.forEach(card => {
            const ref = extractReferenceFromCard(card);
            if (ref && !eventsCache[ref]) {
                references.push(ref);
            }
        });

        // Step 2: ONE batch request (only if cache miss)
        if (references.length > 0) {
            await getEventsBatch(references);
        }

        // Step 3: SYNC enhance all cards (no await, instant!)
        cards.forEach(card => {
            const ref = extractReferenceFromCard(card);
            const apiData = ref ? eventsCache[ref] : null;
            enhanceCardSync(card, apiData);
        });

        console.log(`✅ ${cards.length} cards in ${(performance.now() - startTime).toFixed(0)}ms`);
    }

    // Debounced observer to avoid excessive API calls
    let enhanceTimeout = null;
    let isEnhancing = false;

    const observer = new MutationObserver(() => {
        if (isEnhancing) return;

        clearTimeout(enhanceTimeout);
        enhanceTimeout = setTimeout(async () => {
            isEnhancing = true;
            await enhanceAllCards();
            isEnhancing = false;
        }, 100); // Debounce 100ms
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

    async function init() {
        console.log('🚀 Better E-Leilões Card Enhancer v11.1 (Chrome Extension)');

        await loadConfig();

        integrateWithNativeFloatingButtons();
        await enhanceAllCards();

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
