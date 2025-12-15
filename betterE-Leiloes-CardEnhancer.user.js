// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      3.0
// @description  Design moderno e organizado para os cards com layout melhorado e navegação otimizada
// @author       Nuno Mansilhas
// @match        https://www.e-leiloes.pt/*
// @icon         https://www.e-leiloes.pt/favicon.ico
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ====================================
    // CONFIGURAÇÃO
    // ====================================

    const CONFIG = {
        API_BASE: 'http://localhost:8000/api',
        DASHBOARD_URL: 'http://localhost:8000',
        ENABLE_API_ENRICHMENT: true
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

        /* Esconde os elementos nativos que vamos substituir */
        .p-evento[data-better-enhanced="true"] .flex.align-items-center.justify-content-between.mt-2 {
            display: none !important;
        }

        /* Esconde os valores nativos na parte inferior */
        .p-evento[data-better-enhanced="true"] .surface-100.border-round-bottom {
            display: none !important;
        }

        /* Fix para links abrirem em nova aba */
        .p-evento a[href*="/evento/"] {
            pointer-events: none !important;
        }

        .p-evento a {
            cursor: default !important;
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

        .better-header-actions {
            display: flex;
            gap: 8px;
            align-items: center;
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
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 4px;
            color: #374151;
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

        /* Detalhes - Row 3 */
        .better-details-row {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
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

        /* Valores - Row 4 */
        .better-valores-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 8px;
            padding: 12px 16px;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-bottom: 1px solid #bae6fd;
        }

        .better-valor-item {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .better-valor-label {
            font-size: 9px;
            font-weight: 700;
            text-transform: uppercase;
            color: #0369a1;
            letter-spacing: 0.5px;
        }

        .better-valor-amount {
            font-size: 13px;
            font-weight: 700;
            color: #0c4a6e;
        }

        /* Countdown - Row 5 */
        .better-countdown-row {
            padding: 10px 16px;
            background: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .better-countdown {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }

        .better-countdown-icon {
            font-size: 16px;
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

        /* Botão flutuante dashboard */
        .better-dashboard-btn {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border: none;
            border-radius: 50%;
            width: 56px;
            height: 56px;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
            z-index: 9999;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .better-dashboard-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 16px rgba(16, 185, 129, 0.6);
        }
    `;
    document.head.appendChild(styles);

    // ====================================
    // UTILITÁRIOS
    // ====================================

    function formatCurrency(value) {
        if (!value) return '-';
        return new Intl.NumberFormat('pt-PT', {
            style: 'currency',
            currency: 'EUR',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
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

        let text = '';
        const isEnding = days === 0 && hours < 24;

        if (days > 0) {
            text = `${days}d ${hours}h`;
        } else if (hours > 0) {
            text = `${hours}h ${minutes}m`;
        } else {
            text = `${minutes}m`;
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
    // BOTÃO DASHBOARD
    // ====================================

    function createDashboardButton() {
        const btn = document.createElement('button');
        btn.className = 'better-dashboard-btn';
        btn.innerHTML = '🏠';
        btn.title = 'Abrir Dashboard Better E-Leilões';
        btn.onclick = () => {
            window.open(CONFIG.DASHBOARD_URL, '_blank');
        };
        document.body.appendChild(btn);
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

        try {
            const reference = extractReferenceFromCard(card);
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

            // ===== ROW 1: HEADER =====
            let headerHTML = `
            <div class="better-card-header">
                <div class="better-ref-badge">${reference}</div>
                <div class="better-header-actions">
                    <div class="better-tipo-badge ${apiData.tipoEvento}">
                        ${apiData.tipoEvento === 'movel' ? '🚗' : '🏠'}
                        ${apiData.tipoEvento === 'movel' ? 'Móvel' : 'Imóvel'}
                    </div>
                    ${apiData.gps && apiData.gps.latitude ? `
                        <button class="better-btn better-btn-map" data-lat="${apiData.gps.latitude}" data-lon="${apiData.gps.longitude}">
                            📍 Mapa
                        </button>
                    ` : ''}
                    <button class="better-btn better-btn-primary" data-url="${eventUrl}">
                        👁️ Ver Mais
                    </button>
                </div>
            </div>
        `;

        // Insere header no início do card
        const firstChild = card.firstChild;
        console.log('🔧 First child:', firstChild);
        const headerDiv = document.createElement('div');
        headerDiv.innerHTML = headerHTML;
        console.log('🔧 Header HTML created:', headerDiv.innerHTML.length, 'chars');
        card.insertBefore(headerDiv.firstChild, firstChild);
        console.log('✅ Header inserted');

        // ===== ROW 2: CAROUSEL (MANTÉM O NATIVO) =====
        // Adiciona badge de contagem
        const galleryContainer = card.querySelector('.p-galleria, .p-evento-header');
        if (galleryContainer && apiData.imagens && apiData.imagens.length > 0) {
            galleryContainer.style.position = 'relative';
            const imageBadge = document.createElement('div');
            imageBadge.className = 'better-image-badge';
            imageBadge.innerHTML = `📷 ${apiData.imagens.length}`;
            galleryContainer.appendChild(imageBadge);
        }

        // ===== ROW 3: DETALHES =====
        const det = apiData.detalhes || {};
        const icon = apiData.tipoEvento === 'movel' ? '🚗' : '🏠';

        let detailsHTML = `
            <div class="better-details-row">
                <div class="better-icon-box">${icon}</div>
                <div class="better-details-info">
                    ${det.tipo ? `
                        <div class="better-detail-item">
                            <span class="better-detail-label">Tipo:</span>
                            <span class="better-detail-value">${det.tipo}</span>
                            ${det.subtipo ? `<span class="better-detail-value">- ${det.subtipo}</span>` : ''}
                        </div>
                    ` : ''}
                    ${det.matricula ? `<div class="better-matricula-badge">🚙 ${det.matricula}</div>` : ''}
                    ${det.tipologia ? `<div class="better-tipologia-badge">🏘️ ${det.tipologia}</div>` : ''}
                    ${det.areaPrivativa ? `
                        <div class="better-detail-item">
                            <span class="better-detail-label">📐</span>
                            <span class="better-detail-value">${det.areaPrivativa}m²</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        // ===== ROW 4: VALORES =====
        let valoresHTML = '';
        if (apiData.valores) {
            const v = apiData.valores;
            valoresHTML = `
                <div class="better-valores-row">
                    ${v.valorBase ? `
                        <div class="better-valor-item">
                            <div class="better-valor-label">VB</div>
                            <div class="better-valor-amount">${formatCurrency(v.valorBase)}</div>
                        </div>
                    ` : ''}
                    ${v.valorAbertura ? `
                        <div class="better-valor-item">
                            <div class="better-valor-label">VA</div>
                            <div class="better-valor-amount">${formatCurrency(v.valorAbertura)}</div>
                        </div>
                    ` : ''}
                    ${v.valorMinimo ? `
                        <div class="better-valor-item">
                            <div class="better-valor-label">VM</div>
                            <div class="better-valor-amount">${formatCurrency(v.valorMinimo)}</div>
                        </div>
                    ` : ''}
                    ${v.lanceAtual ? `
                        <div class="better-valor-item">
                            <div class="better-valor-label">LA</div>
                            <div class="better-valor-amount">${formatCurrency(v.lanceAtual)}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // ===== ROW 5: COUNTDOWN =====
        let countdownHTML = '';
        if (apiData.dataFim) {
            const remaining = calculateTimeRemaining(apiData.dataFim);
            if (remaining) {
                countdownHTML = `
                    <div class="better-countdown-row">
                        <div class="better-countdown">
                            <span class="better-countdown-icon">⏱️</span>
                            <span class="better-countdown-text">Termina em:</span>
                            <span class="better-countdown-time ${remaining.isEnding ? 'ending-soon' : ''}">
                                ${remaining.text}
                            </span>
                        </div>
                    </div>
                `;
            }
        }

        // ===== LOCALIZAÇÃO (OPCIONAL) =====
        let locationHTML = '';
        if (det.distrito || det.concelho || det.freguesia || (apiData.gps && apiData.gps.latitude)) {
            locationHTML = `<div class="better-location-row">`;
            if (det.distrito) locationHTML += `<span class="better-location-tag">📍 ${det.distrito}</span>`;
            if (det.concelho) locationHTML += `<span class="better-location-tag">${det.concelho}</span>`;
            if (det.freguesia) locationHTML += `<span class="better-location-tag">${det.freguesia}</span>`;
            if (apiData.gps && apiData.gps.latitude) {
                locationHTML += `<span class="better-gps-badge">🗺️ GPS: ${apiData.gps.latitude.toFixed(4)}, ${apiData.gps.longitude.toFixed(4)}</span>`;
            }
            locationHTML += `</div>`;
        }

        // Insere rows no card - usa o primeiro div filho
        const cardBody = card.querySelector('.w-full.border-1.surface-border.border-round');
        console.log('🔧 Card body found:', cardBody);
        if (cardBody) {
            const newContent = detailsHTML + valoresHTML + countdownHTML + locationHTML;
            console.log('🔧 New content length:', newContent.length, 'chars');

            // Adiciona o conteúdo DEPOIS do conteúdo nativo (não substitui)
            const contentWrapper = document.createElement('div');
            contentWrapper.className = 'better-card-content';
            contentWrapper.innerHTML = newContent;
            cardBody.appendChild(contentWrapper);
            console.log('✅ Card body updated');
        } else {
            console.error('❌ Card body (.w-full.border-1) not found!');
        }

        // ===== EVENT HANDLERS =====
        // Botão "Ver Mais"
        const verMaisBtn = card.querySelector('.better-btn-primary');
        if (verMaisBtn) {
            verMaisBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                window.open(eventUrl, '_blank');
            });
        }

        // Botão "Mapa"
        const mapaBtn = card.querySelector('.better-btn-map');
        if (mapaBtn) {
            mapaBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const lat = mapaBtn.dataset.lat;
                const lon = mapaBtn.dataset.lon;
                window.open(`https://www.google.com/maps?q=${lat},${lon}`, '_blank');
            });
        }

        // Click no card inteiro abre em nova aba (SEM atualizar atual)
        card.style.cursor = 'pointer';
        card.addEventListener('click', (e) => {
            // Previne navegação padrão
            e.preventDefault();
            e.stopPropagation();

            // Ignora se clicou num botão
            if (e.target.closest('.better-btn')) return;

            // Abre APENAS em nova aba, não atualiza a atual
            window.open(eventUrl, '_blank');
            return false;
        }, true); // useCapture = true para capturar antes

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
    });

    // ====================================
    // INICIALIZAÇÃO
    // ====================================

    function init() {
        console.log('🚀 Better E-Leilões Card Enhancer v3.0');

        createDashboardButton();
        enhanceAllCards();

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('✅ Card enhancer v3.0 ativo - Design moderno e organizado!');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
