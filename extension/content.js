/**
 * Better E-Leilões - Card Enhancer
 * Chrome Extension Version 11.2 - INSTANT RENDERING
 * Two-phase: instant styling + async data enrichment
 */

(function() {
    'use strict';

    // ====================================
    // CONFIG
    // ====================================
    let CONFIG = {
        API_BASE: 'http://localhost:8000/api',
        DASHBOARD_URL: 'http://localhost:8000',
        ENABLE_API: true,
        MAX_IMAGES: 10
    };

    async function loadConfig() {
        if (typeof chrome !== 'undefined' && chrome.storage) {
            return new Promise(resolve => {
                chrome.storage.sync.get({
                    apiUrl: 'http://localhost:8000',
                    enableApiEnrichment: true
                }, items => {
                    CONFIG.API_BASE = items.apiUrl + '/api';
                    CONFIG.DASHBOARD_URL = items.apiUrl;
                    CONFIG.ENABLE_API = items.enableApiEnrichment;
                    resolve();
                });
            });
        }
    }

    // ====================================
    // UTILITIES
    // ====================================
    const formatCurrency = v => v == null ? '0 €' :
        new Intl.NumberFormat('pt-PT', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(v) + ' €';

    function getTimeRemaining(endDate) {
        if (!endDate) return null;
        const diff = new Date(endDate) - new Date();
        if (diff <= 0) return { text: 'Terminado', urgent: false };

        const d = Math.floor(diff / 86400000);
        const h = Math.floor((diff % 86400000) / 3600000);
        const m = Math.floor((diff % 3600000) / 60000);
        const s = Math.floor((diff % 60000) / 1000);

        return {
            text: d > 0 ? `${d}d ${h}h ${m}m` : h > 0 ? `${h}h ${m}m ${s}s` : m > 0 ? `${m}m ${s}s` : `${s}s`,
            urgent: d === 0 && h < 24
        };
    }

    // ====================================
    // DATA CACHE & API
    // ====================================
    const cache = {};
    const pendingRefs = new Set();
    let fetchTimer = null;

    async function fetchBatch(refs) {
        if (!CONFIG.ENABLE_API || refs.length === 0) return;

        try {
            const res = await fetch(`${CONFIG.API_BASE}/events/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ references: refs })
            });

            if (res.ok) {
                const data = await res.json();
                Object.entries(data.events).forEach(([ref, evt]) => cache[ref] = evt);
                data.not_found?.forEach(ref => cache[ref] = { _notFound: true });

                // Enrich cards that were waiting
                refs.forEach(ref => {
                    const card = document.querySelector(`.p-evento[data-ref="${ref}"]`);
                    if (card && cache[ref]) enrichCard(card, cache[ref]);
                });
            }
        } catch (e) {
            console.error('API Error:', e);
        }
    }

    function queueFetch(ref) {
        if (cache[ref]) return; // Already have data
        pendingRefs.add(ref);

        clearTimeout(fetchTimer);
        fetchTimer = setTimeout(() => {
            const refs = [...pendingRefs];
            pendingRefs.clear();
            if (refs.length > 0) fetchBatch(refs);
        }, 10); // 10ms debounce - fast!
    }

    // ====================================
    // PHASE 1: INSTANT ENHANCEMENT (no API)
    // ====================================
    function enhanceInstant(card) {
        if (card.dataset.enhanced) return;
        card.dataset.enhanced = '1';

        const ref = card.querySelector('.pi-tag + span')?.textContent?.trim();
        if (!ref) return;

        card.dataset.ref = ref;
        card.style.cursor = 'pointer';

        // Color reference prefix
        const refSpan = card.querySelector('.pi-tag + span');
        if (refSpan) {
            const prefix = ref.substring(0, 2);
            refSpan.innerHTML = `<span style="color:${prefix === 'LO' ? '#3b82f6' : '#f59e0b'};font-weight:600">${prefix}</span>${ref.substring(2)}`;
        }

        // Remove native borders
        card.querySelectorAll('.w-full').forEach(div => {
            div.style.border = 'none';
        });

        // Add action buttons
        const star = card.querySelector('.pi-star');
        if (star?.parentElement) {
            const btns = document.createElement('div');
            btns.className = 'better-btns';
            btns.innerHTML = `<button class="better-btn sync" title="Sync"><i class="pi pi-sync"></i></button>`;
            btns.querySelector('.sync').onclick = e => {
                e.stopPropagation();
                syncCard(card, ref);
            };
            star.parentElement.appendChild(btns);
        }

        // Click to open event
        card.addEventListener('click', e => {
            if (e.target.closest('.pi-star, .better-btn, .carousel-nav, .carousel-dot, .carousel-slide')) return;
            e.preventDefault();
            e.stopPropagation();
            window.open(`https://www.e-leiloes.pt/evento/${ref}`, '_blank');
        }, true);

        // Disable native context menu hijacking
        card.addEventListener('contextmenu', e => e.stopPropagation(), true);

        // Queue data fetch (non-blocking)
        queueFetch(ref);

        // If we already have cached data, enrich immediately
        if (cache[ref] && !cache[ref]._notFound) {
            enrichCard(card, cache[ref]);
        }
    }

    // ====================================
    // PHASE 2: DATA ENRICHMENT (with API data)
    // ====================================
    function enrichCard(card, data) {
        if (card.dataset.enriched || !data || data._notFound) return;
        card.dataset.enriched = '1';

        const ref = card.dataset.ref;

        // Add map button if GPS available
        if (data.latitude && data.longitude) {
            const btns = card.querySelector('.better-btns');
            if (btns && !btns.querySelector('.map')) {
                const mapBtn = document.createElement('button');
                mapBtn.className = 'better-btn map';
                mapBtn.title = 'Google Maps';
                mapBtn.innerHTML = '<i class="pi pi-map-marker"></i>';
                mapBtn.onclick = e => {
                    e.stopPropagation();
                    window.open(`https://www.google.com/maps?q=${data.latitude},${data.longitude}`, '_blank');
                };
                btns.insertBefore(mapBtn, btns.firstChild);
            }
        }

        // Carousel
        const nativeImg = card.querySelector('.p-evento-image');
        const images = (data.fotos || []).slice(0, CONFIG.MAX_IMAGES).map(f => f.image || f.thumbnail || f).filter(Boolean);

        if (nativeImg && images.length > 0) {
            nativeImg.style.display = 'none';

            const carousel = document.createElement('div');
            carousel.className = 'better-carousel';
            carousel.innerHTML = `
                <div class="carousel-track">${images.map((img, i) =>
                    `<div class="carousel-slide" style="background-image:url('${img}')" data-i="${i}"></div>`
                ).join('')}</div>
                <span class="carousel-count">${images.length} 📷</span>
                ${images.length > 1 ? `
                    <button class="carousel-nav prev">‹</button>
                    <button class="carousel-nav next">›</button>
                    <div class="carousel-dots">${images.map((_, i) =>
                        `<div class="carousel-dot${i === 0 ? ' active' : ''}" data-i="${i}"></div>`
                    ).join('')}</div>
                ` : ''}
            `;

            nativeImg.parentNode.insertBefore(carousel, nativeImg.nextSibling);

            if (images.length > 1) {
                let idx = 0;
                const track = carousel.querySelector('.carousel-track');
                const dots = carousel.querySelectorAll('.carousel-dot');
                const go = n => {
                    idx = (n + images.length) % images.length;
                    track.style.transform = `translateX(-${idx * 100}%)`;
                    dots.forEach((d, i) => d.classList.toggle('active', i === idx));
                };
                carousel.querySelector('.prev').onclick = e => { e.stopPropagation(); go(idx - 1); };
                carousel.querySelector('.next').onclick = e => { e.stopPropagation(); go(idx + 1); };
                dots.forEach((d, i) => d.onclick = e => { e.stopPropagation(); go(i); });
            }

            // Lightbox
            carousel.querySelectorAll('.carousel-slide').forEach((s, i) => {
                s.onclick = e => { e.stopPropagation(); openLightbox(images, i); };
            });
        }

        // Values + Details Grid
        const content = document.createElement('div');
        content.className = 'better-content';

        // Values column
        let vals = '';
        if (data.valor_base) vals += `<div class="val-row"><span class="val-lbl">VB</span><span class="val-amt">${formatCurrency(data.valor_base)}</span></div>`;
        if (data.valor_abertura) vals += `<div class="val-row"><span class="val-lbl">VA</span><span class="val-amt">${formatCurrency(data.valor_abertura)}</span></div>`;
        if (data.valor_minimo) vals += `<div class="val-row"><span class="val-lbl">VM</span><span class="val-amt">${formatCurrency(data.valor_minimo)}</span></div>`;
        vals += `<div class="val-row highlight"><span class="val-lbl">Lance</span><span class="val-amt">${formatCurrency(data.lance_atual || 0)}</span></div>`;

        // Details column
        let details = '';
        const tipo = data.tipo_id || 0;
        const isImov = tipo === 1 || data.tipo?.toLowerCase().includes('imov');
        const isVeic = tipo === 2 || data.tipo?.toLowerCase().includes('veic');

        if (isImov) {
            if (data.tipologia) details += `<div class="det-row"><span class="det-lbl">Tipo</span><span class="det-val">${data.tipologia}</span></div>`;
            if (data.area_util || data.area_bruta) details += `<div class="det-row"><span class="det-lbl">Área</span><span class="det-val">${data.area_util || data.area_bruta} m²</span></div>`;
        } else if (isVeic) {
            if (data.matricula) details += `<div class="det-row"><span class="det-lbl">Matrícula</span><span class="det-val">${data.matricula}</span></div>`;
            if (data.marca) details += `<div class="det-row"><span class="det-lbl">Marca</span><span class="det-val">${data.marca}</span></div>`;
        }
        if (data.concelho) details += `<div class="det-row"><span class="det-lbl">Local</span><span class="det-val">${data.concelho}</span></div>`;
        if (!details && data.subtipo) details += `<div class="det-row"><span class="det-lbl">Tipo</span><span class="det-val">${data.subtipo}</span></div>`;

        content.innerHTML = `<div class="vals-col">${vals}</div><div class="dets-col">${details}</div>`;
        card.appendChild(content);

        // Countdown
        if (data.data_fim) {
            const time = getTimeRemaining(data.data_fim);
            if (time) {
                const countdown = document.createElement('div');
                countdown.className = 'better-countdown';
                countdown.innerHTML = `<span>⏱️ Termina:</span><span class="time${time.urgent ? ' urgent' : ''}" data-end="${data.data_fim}">${time.text}</span>`;
                card.appendChild(countdown);
            }
        }
    }

    // ====================================
    // SYNC BUTTON HANDLER
    // ====================================
    async function syncCard(card, ref) {
        const btn = card.querySelector('.better-btn.sync i');
        if (btn) btn.style.animation = 'spin 0.8s linear infinite';

        try {
            const res = await fetch(`${CONFIG.API_BASE}/scrape/stage2/api?references=${ref}&save_to_db=true`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                if (data.events?.[0]) {
                    cache[ref] = data.events[0];
                    // Remove old enrichment and re-enrich
                    card.querySelectorAll('.better-carousel, .better-content, .better-countdown').forEach(el => el.remove());
                    card.querySelector('.p-evento-image')?.style.removeProperty('display');
                    delete card.dataset.enriched;
                    enrichCard(card, cache[ref]);
                }
            }
        } catch (e) {
            console.error('Sync error:', e);
        }

        if (btn) btn.style.animation = '';
    }

    // ====================================
    // LIGHTBOX
    // ====================================
    let lbImages = [], lbIdx = 0;

    function openLightbox(images, start) {
        lbImages = images;
        lbIdx = start;

        const lb = document.createElement('div');
        lb.id = 'better-lb';
        lb.innerHTML = `
            <button class="lb-close">×</button>
            <button class="lb-nav prev">‹</button>
            <img class="lb-img" src="${images[start]}">
            <button class="lb-nav next">›</button>
            <div class="lb-count">${start + 1} / ${images.length}</div>
        `;
        document.body.appendChild(lb);
        requestAnimationFrame(() => lb.classList.add('active'));

        const img = lb.querySelector('.lb-img');
        const count = lb.querySelector('.lb-count');
        const update = () => { img.src = lbImages[lbIdx]; count.textContent = `${lbIdx + 1} / ${lbImages.length}`; };

        lb.querySelector('.lb-close').onclick = closeLightbox;
        lb.querySelector('.lb-nav.prev').onclick = () => { lbIdx = (lbIdx - 1 + lbImages.length) % lbImages.length; update(); };
        lb.querySelector('.lb-nav.next').onclick = () => { lbIdx = (lbIdx + 1) % lbImages.length; update(); };
        lb.onclick = e => { if (e.target === lb) closeLightbox(); };

        document.addEventListener('keydown', lbKeys);
    }

    function closeLightbox() {
        const lb = document.getElementById('better-lb');
        if (lb) { lb.classList.remove('active'); setTimeout(() => lb.remove(), 300); }
        document.removeEventListener('keydown', lbKeys);
    }

    function lbKeys(e) {
        if (e.key === 'Escape') closeLightbox();
        if (e.key === 'ArrowLeft') { lbIdx = (lbIdx - 1 + lbImages.length) % lbImages.length; document.querySelector('.lb-img').src = lbImages[lbIdx]; document.querySelector('.lb-count').textContent = `${lbIdx + 1} / ${lbImages.length}`; }
        if (e.key === 'ArrowRight') { lbIdx = (lbIdx + 1) % lbImages.length; document.querySelector('.lb-img').src = lbImages[lbIdx]; document.querySelector('.lb-count').textContent = `${lbIdx + 1} / ${lbImages.length}`; }
    }

    // ====================================
    // DASHBOARD BUTTON
    // ====================================
    function addDashboardBtn() {
        if (document.querySelector('.better-dash-btn')) return;
        const btn = document.createElement('button');
        btn.className = 'better-dash-btn';
        btn.title = 'Dashboard';
        btn.innerHTML = '<span class="pi pi-home"></span>';
        btn.onclick = () => window.open(CONFIG.DASHBOARD_URL, '_blank');
        document.body.appendChild(btn);
    }

    // ====================================
    // OBSERVER & INIT
    // ====================================
    function processCards() {
        document.querySelectorAll('.p-evento:not([data-enhanced])').forEach(enhanceInstant);
    }

    function updateCountdowns() {
        document.querySelectorAll('[data-end]').forEach(el => {
            const t = getTimeRemaining(el.dataset.end);
            if (t) { el.textContent = t.text; el.classList.toggle('urgent', t.urgent); }
        });
    }

    // INSTANT processing - no debounce!
    const observer = new MutationObserver(processCards);

    async function init() {
        console.log('🚀 Better E-Leilões v11.2 - INSTANT');
        await loadConfig();
        addDashboardBtn();
        processCards();
        setInterval(updateCountdowns, 1000);
        observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
