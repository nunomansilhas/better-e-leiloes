/**
 * Better E-Leilões - Card Enhancer
 * Chrome Extension Version 12.0 - ZERO WAIT
 * Instant DOM enhancement - API only for extra data
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

    function parsePrice(text) {
        if (!text) return null;
        const clean = text.replace(/[^\d,.-]/g, '').replace(',', '.');
        const num = parseFloat(clean);
        return isNaN(num) ? null : num;
    }

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
    // INSTANT CARD ENHANCEMENT (NO API!)
    // ====================================
    function enhanceCard(card) {
        if (card.dataset.enhanced) return;
        card.dataset.enhanced = '1';

        // Get reference
        const refSpan = card.querySelector('.pi-tag + span');
        const ref = refSpan?.textContent?.trim();
        if (!ref) return;

        card.dataset.ref = ref;

        // ===== INSTANT VISUAL ENHANCEMENTS =====

        // 1. Style the card
        card.style.cssText = `
            border-radius: 12px !important;
            border: 1px solid #e2e8f0 !important;
            overflow: hidden !important;
            transition: all 0.15s ease !important;
            cursor: pointer !important;
        `;

        // 2. Color reference prefix
        const prefix = ref.substring(0, 2);
        refSpan.innerHTML = `<span style="color:${prefix === 'LO' ? '#3b82f6' : '#f59e0b'};font-weight:700">${prefix}</span>${ref.substring(2)}`;

        // 3. Remove native borders
        card.querySelectorAll('.w-full').forEach(div => {
            div.style.border = 'none';
        });

        // 4. Extract native price from card (e-leiloes shows price on cards)
        const priceEl = card.querySelector('.text-primary, [class*="price"], .font-bold');
        const nativePrice = priceEl ? parsePrice(priceEl.textContent) : null;

        // 5. Extract native image
        const nativeImg = card.querySelector('img[src*="foto"], img[src*="image"], .p-evento-image img');
        const nativeImgSrc = nativeImg?.src;

        // 6. Add action buttons next to star
        const star = card.querySelector('.pi-star');
        if (star?.parentElement && !card.querySelector('.better-btns')) {
            const btns = document.createElement('div');
            btns.className = 'better-btns';
            btns.style.cssText = 'display:flex;gap:6px;margin-left:8px;';
            btns.innerHTML = `
                <button class="better-btn sync" title="Sync com API" style="background:none;border:none;cursor:pointer;padding:4px;color:#64748b;border-radius:4px;">
                    <i class="pi pi-sync" style="font-size:1rem;"></i>
                </button>
            `;
            btns.querySelector('.sync').onclick = e => {
                e.stopPropagation();
                syncCard(card, ref);
            };
            star.parentElement.appendChild(btns);
        }

        // 7. Add info bar with native data
        if (nativePrice && !card.querySelector('.better-info')) {
            const info = document.createElement('div');
            info.className = 'better-info';
            info.style.cssText = `
                background: linear-gradient(90deg, #fef3c7 0%, #fffbeb 100%);
                padding: 8px 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 12px;
                border-top: 1px solid #e5e7eb;
            `;
            info.innerHTML = `
                <span style="color:#92400e;font-weight:600;">Lance Atual</span>
                <span style="color:#92400e;font-weight:700;font-size:14px;">${formatCurrency(nativePrice)}</span>
            `;
            card.appendChild(info);
        }

        // 8. Click handler to open event
        card.addEventListener('click', e => {
            if (e.target.closest('.pi-star, .better-btn')) return;
            e.preventDefault();
            e.stopPropagation();
            window.open(`https://www.e-leiloes.pt/evento/${ref}`, '_blank');
        }, true);

        // 9. Disable native context menu
        card.addEventListener('contextmenu', e => e.stopPropagation(), true);

        // 10. Hover effect
        card.addEventListener('mouseenter', () => {
            card.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
            card.style.borderColor = '#3b82f6';
        });
        card.addEventListener('mouseleave', () => {
            card.style.boxShadow = '';
            card.style.borderColor = '#e2e8f0';
        });

        // Queue API fetch for extra data (non-blocking)
        if (CONFIG.ENABLE_API) {
            queueFetch(ref);
        }
    }

    // ====================================
    // API DATA ENRICHMENT (background)
    // ====================================
    const cache = {};
    const pendingRefs = new Set();
    let fetchTimer = null;

    function queueFetch(ref) {
        if (cache[ref]) {
            enrichWithAPI(ref, cache[ref]);
            return;
        }
        pendingRefs.add(ref);
        clearTimeout(fetchTimer);
        fetchTimer = setTimeout(fetchBatch, 50);
    }

    async function fetchBatch() {
        const refs = [...pendingRefs];
        pendingRefs.clear();
        if (refs.length === 0) return;

        try {
            const res = await fetch(`${CONFIG.API_BASE}/events/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ references: refs })
            });

            if (res.ok) {
                const data = await res.json();
                Object.entries(data.events || {}).forEach(([ref, evt]) => {
                    cache[ref] = evt;
                    enrichWithAPI(ref, evt);
                });
            }
        } catch (e) {
            // API not available - that's fine, cards already enhanced
            console.log('Better E-Leilões: API offline, using native data only');
        }
    }

    function enrichWithAPI(ref, data) {
        if (!data || data._notFound) return;
        const card = document.querySelector(`.p-evento[data-ref="${ref}"]`);
        if (!card || card.dataset.apiEnriched) return;
        card.dataset.apiEnriched = '1';

        // Add map button if GPS available
        if (data.latitude && data.longitude) {
            const btns = card.querySelector('.better-btns');
            if (btns && !btns.querySelector('.map')) {
                const mapBtn = document.createElement('button');
                mapBtn.className = 'better-btn map';
                mapBtn.title = 'Google Maps';
                mapBtn.style.cssText = 'background:none;border:none;cursor:pointer;padding:4px;color:#64748b;border-radius:4px;';
                mapBtn.innerHTML = '<i class="pi pi-map-marker" style="font-size:1rem;"></i>';
                mapBtn.onclick = e => {
                    e.stopPropagation();
                    window.open(`https://www.google.com/maps?q=${data.latitude},${data.longitude}`, '_blank');
                };
                btns.insertBefore(mapBtn, btns.firstChild);
            }
        }

        // Add carousel if photos available
        const images = (data.fotos || []).slice(0, CONFIG.MAX_IMAGES).map(f => f.image || f.thumbnail || f).filter(Boolean);
        if (images.length > 1) {
            const nativeImg = card.querySelector('.p-evento-image');
            if (nativeImg && !card.querySelector('.better-carousel')) {
                createCarousel(card, nativeImg, images);
            }
        }

        // Update info bar with API data
        const info = card.querySelector('.better-info');
        if (info && data.lance_atual) {
            info.querySelector('span:last-child').textContent = formatCurrency(data.lance_atual);
        }

        // Add countdown if end date available
        if (data.data_fim && !card.querySelector('.better-countdown')) {
            const time = getTimeRemaining(data.data_fim);
            if (time) {
                const countdown = document.createElement('div');
                countdown.className = 'better-countdown';
                countdown.style.cssText = `
                    background: #f8fafc;
                    padding: 6px 12px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 6px;
                    font-size: 11px;
                    border-top: 1px solid #e5e7eb;
                `;
                countdown.innerHTML = `
                    <span style="color:#6b7280;">⏱️ Termina:</span>
                    <span class="time" data-end="${data.data_fim}" style="color:${time.urgent ? '#dc2626' : '#059669'};font-weight:700;">${time.text}</span>
                `;
                card.appendChild(countdown);
            }
        }
    }

    // ====================================
    // CAROUSEL
    // ====================================
    function createCarousel(card, nativeImg, images) {
        nativeImg.style.display = 'none';

        const carousel = document.createElement('div');
        carousel.className = 'better-carousel';
        carousel.style.cssText = 'position:relative;width:100%;height:160px;overflow:hidden;background:#f1f5f9;';
        carousel.innerHTML = `
            <div class="carousel-track" style="display:flex;height:100%;transition:transform 0.3s ease;">
                ${images.map((img, i) => `<div class="carousel-slide" style="min-width:100%;height:100%;background:url('${img}') center/cover;cursor:zoom-in;" data-i="${i}"></div>`).join('')}
            </div>
            <span style="position:absolute;top:8px;left:8px;background:rgba(0,0,0,0.6);color:white;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;">${images.length} 📷</span>
            ${images.length > 1 ? `
                <button class="carousel-nav prev" style="position:absolute;left:8px;top:50%;transform:translateY(-50%);background:rgba(255,255,255,0.9);border:none;width:28px;height:28px;border-radius:50%;cursor:pointer;font-weight:bold;opacity:0;transition:opacity 0.2s;">‹</button>
                <button class="carousel-nav next" style="position:absolute;right:8px;top:50%;transform:translateY(-50%);background:rgba(255,255,255,0.9);border:none;width:28px;height:28px;border-radius:50%;cursor:pointer;font-weight:bold;opacity:0;transition:opacity 0.2s;">›</button>
                <div class="carousel-dots" style="position:absolute;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:4px;">
                    ${images.map((_, i) => `<div class="carousel-dot" data-i="${i}" style="width:6px;height:6px;border-radius:50%;background:${i === 0 ? 'white' : 'rgba(255,255,255,0.5)'};cursor:pointer;border:1px solid rgba(0,0,0,0.2);"></div>`).join('')}
                </div>
            ` : ''}
        `;

        nativeImg.parentNode.insertBefore(carousel, nativeImg.nextSibling);

        // Show/hide nav on hover
        carousel.addEventListener('mouseenter', () => {
            carousel.querySelectorAll('.carousel-nav').forEach(n => n.style.opacity = '1');
        });
        carousel.addEventListener('mouseleave', () => {
            carousel.querySelectorAll('.carousel-nav').forEach(n => n.style.opacity = '0');
        });

        if (images.length > 1) {
            let idx = 0;
            const track = carousel.querySelector('.carousel-track');
            const dots = carousel.querySelectorAll('.carousel-dot');
            const go = n => {
                idx = (n + images.length) % images.length;
                track.style.transform = `translateX(-${idx * 100}%)`;
                dots.forEach((d, i) => d.style.background = i === idx ? 'white' : 'rgba(255,255,255,0.5)');
            };
            carousel.querySelector('.prev')?.addEventListener('click', e => { e.stopPropagation(); go(idx - 1); });
            carousel.querySelector('.next')?.addEventListener('click', e => { e.stopPropagation(); go(idx + 1); });
            dots.forEach((d, i) => d.addEventListener('click', e => { e.stopPropagation(); go(i); }));
        }

        // Lightbox on click
        carousel.querySelectorAll('.carousel-slide').forEach((s, i) => {
            s.addEventListener('click', e => { e.stopPropagation(); openLightbox(images, i); });
        });
    }

    // ====================================
    // SYNC BUTTON
    // ====================================
    async function syncCard(card, ref) {
        const btn = card.querySelector('.better-btn.sync i');
        if (btn) {
            btn.style.animation = 'spin 0.8s linear infinite';
        }

        try {
            const res = await fetch(`${CONFIG.API_BASE}/scrape/stage2/api?references=${ref}&save_to_db=true`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                if (data.events?.[0]) {
                    cache[ref] = data.events[0];
                    delete card.dataset.apiEnriched;
                    enrichWithAPI(ref, cache[ref]);
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
        lb.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(0,0,0,0.92);z-index:99999;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity 0.3s;';
        lb.innerHTML = `
            <button style="position:absolute;top:20px;right:20px;width:44px;height:44px;background:rgba(255,255,255,0.15);border:none;border-radius:50%;color:white;font-size:28px;cursor:pointer;">×</button>
            <button class="lb-prev" style="position:absolute;left:20px;top:50%;transform:translateY(-50%);width:50px;height:50px;background:rgba(255,255,255,0.15);border:none;border-radius:50%;color:white;font-size:24px;cursor:pointer;">‹</button>
            <img class="lb-img" src="${images[start]}" style="max-width:90vw;max-height:90vh;object-fit:contain;border-radius:4px;">
            <button class="lb-next" style="position:absolute;right:20px;top:50%;transform:translateY(-50%);width:50px;height:50px;background:rgba(255,255,255,0.15);border:none;border-radius:50%;color:white;font-size:24px;cursor:pointer;">›</button>
            <div class="lb-count" style="position:absolute;bottom:20px;left:50%;transform:translateX(-50%);color:white;font-size:14px;background:rgba(0,0,0,0.6);padding:6px 16px;border-radius:20px;">${start + 1} / ${images.length}</div>
        `;
        document.body.appendChild(lb);
        requestAnimationFrame(() => lb.style.opacity = '1');

        const img = lb.querySelector('.lb-img');
        const count = lb.querySelector('.lb-count');
        const update = () => { img.src = lbImages[lbIdx]; count.textContent = `${lbIdx + 1} / ${lbImages.length}`; };

        lb.querySelector('button').onclick = closeLightbox;
        lb.querySelector('.lb-prev').onclick = () => { lbIdx = (lbIdx - 1 + lbImages.length) % lbImages.length; update(); };
        lb.querySelector('.lb-next').onclick = () => { lbIdx = (lbIdx + 1) % lbImages.length; update(); };
        lb.onclick = e => { if (e.target === lb) closeLightbox(); };

        document.addEventListener('keydown', lbKeys);
    }

    function closeLightbox() {
        const lb = document.getElementById('better-lb');
        if (lb) { lb.style.opacity = '0'; setTimeout(() => lb.remove(), 300); }
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
        btn.style.cssText = 'position:fixed;bottom:20px;right:20px;width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#3b82f6 0%,#2563eb 100%);color:white;border:none;cursor:pointer;box-shadow:0 4px 14px rgba(59,130,246,0.4);z-index:9999;display:flex;align-items:center;justify-content:center;transition:transform 0.2s;';
        btn.innerHTML = '<span class="pi pi-home" style="font-size:20px;"></span>';
        btn.onclick = () => window.open(CONFIG.DASHBOARD_URL, '_blank');
        btn.onmouseenter = () => btn.style.transform = 'scale(1.1)';
        btn.onmouseleave = () => btn.style.transform = '';
        document.body.appendChild(btn);
    }

    // ====================================
    // COUNTDOWN UPDATE
    // ====================================
    function updateCountdowns() {
        document.querySelectorAll('[data-end]').forEach(el => {
            const t = getTimeRemaining(el.dataset.end);
            if (t) {
                el.textContent = t.text;
                el.style.color = t.urgent ? '#dc2626' : '#059669';
            }
        });
    }

    // ====================================
    // INIT
    // ====================================
    function processCards() {
        document.querySelectorAll('.p-evento:not([data-enhanced])').forEach(enhanceCard);
    }

    const observer = new MutationObserver(processCards);

    async function init() {
        console.log('🚀 Better E-Leilões v12.0 - ZERO WAIT');
        await loadConfig();

        // Add spin animation
        const style = document.createElement('style');
        style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
        document.head.appendChild(style);

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
