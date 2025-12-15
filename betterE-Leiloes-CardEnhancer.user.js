// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Enriquece os cards com dados detalhados: GPS, localização, matrícula, tipologia, áreas, valores e imagens
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
        ENABLE_API_ENRICHMENT: true  // Se false, só melhora visualmente sem chamar API
    };

    // ====================================
    // ESTILOS CSS
    // ====================================

    const styles = document.createElement('style');
    styles.textContent = `
        /* Badge de dados disponíveis */
        .better-badge {
            position: absolute;
            top: 8px;
            right: 8px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
            z-index: 10;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        /* Badge tipo de evento */
        .better-tipo-badge {
            position: absolute;
            top: 8px;
            left: 8px;
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
            z-index: 10;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .better-tipo-badge.movel {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        }

        /* Painel de informações detalhadas */
        .better-info-panel {
            background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
            border-radius: 8px;
            padding: 10px;
            margin-top: 10px;
            border-left: 3px solid #10b981;
            font-size: 11px;
            line-height: 1.6;
        }

        .better-info-row {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 4px;
        }

        .better-info-row:last-child {
            margin-bottom: 0;
        }

        .better-info-icon {
            font-size: 14px;
            min-width: 18px;
        }

        .better-info-label {
            font-weight: 600;
            color: #374151;
        }

        .better-info-value {
            color: #1f2937;
        }

        /* Localização compacta */
        .better-location {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 6px;
            font-size: 10px;
        }

        .better-location-item {
            background: #e0f2fe;
            color: #0369a1;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }

        /* GPS Coordenadas */
        .better-gps-coords {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
            color: #1e40af;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 600;
            margin-top: 6px;
        }

        /* Botão flutuante para dashboard */
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

        /* Valores destacados */
        .better-value-highlight {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            padding: 8px 10px;
            border-radius: 6px;
            border-left: 3px solid #3b82f6;
            margin-top: 8px;
            font-size: 11px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 6px;
        }

        .better-value-item {
            display: flex;
            flex-direction: column;
        }

        .better-value-label {
            color: #64748b;
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 2px;
        }

        .better-value-amount {
            color: #1e40af;
            font-weight: 700;
            font-size: 12px;
        }

        /* Contador de imagens */
        .better-image-count {
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.75);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            z-index: 10;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* Matrícula destaque */
        .better-matricula {
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            color: #92400e;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
            display: inline-block;
            margin-top: 6px;
            border: 1px solid #fbbf24;
        }

        /* Tipologia imóvel */
        .better-tipologia {
            background: linear-gradient(135deg, #ddd6fe 0%, #c4b5fd 100%);
            color: #5b21b6;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
            display: inline-block;
            margin-top: 6px;
        }
    `;
    document.head.appendChild(styles);

    // ====================================
    // BOTÃO FLUTUANTE DASHBOARD
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
    // FUNÇÕES DE API
    // ====================================

    async function getEventFromAPI(reference) {
        if (!CONFIG.ENABLE_API_ENRICHMENT) return null;

        try {
            const response = await fetch(`${CONFIG.API_BASE}/events/${reference}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            // Silently fail - API pode não estar disponível
            console.debug(`API not available for ${reference}`);
        }
        return null;
    }

    // ====================================
    // MELHORAR CARDS NATIVOS
    // ====================================

    function extractReferenceFromCard(card) {
        // Procura pelo elemento que contém a referência
        const refElement = card.querySelector('.pi-tag + span');
        if (refElement) {
            return refElement.textContent.trim();
        }
        return null;
    }

    async function enhanceCard(card) {
        // Evita processar o mesmo card duas vezes
        if (card.dataset.betterEnhanced) return;
        card.dataset.betterEnhanced = 'true';

        const reference = extractReferenceFromCard(card);
        if (!reference) return;

        // Adiciona posicionamento relativo para badges
        card.style.position = 'relative';

        // Tenta buscar dados da nossa API
        const apiData = await getEventFromAPI(reference);

        if (apiData) {
            // ====== ENRIQUECIMENTO COM DADOS DA API ======

            // Badge verde = dados disponíveis na nossa BD
            const badge = document.createElement('div');
            badge.className = 'better-badge';
            badge.textContent = '✓ BD';
            badge.title = 'Evento na nossa base de dados';
            card.appendChild(badge);

            // Badge do tipo de evento (móvel/imóvel)
            const tipoBadge = document.createElement('div');
            tipoBadge.className = `better-tipo-badge ${apiData.tipoEvento}`;
            tipoBadge.textContent = apiData.tipoEvento === 'movel' ? '🚗 Móvel' : '🏠 Imóvel';
            tipoBadge.title = `Tipo: ${apiData.tipoEvento}`;
            card.appendChild(tipoBadge);

            // Se tem imagens, mostra contador
            if (apiData.imagens && apiData.imagens.length > 0) {
                const imageCount = document.createElement('div');
                imageCount.className = 'better-image-count';
                imageCount.innerHTML = `📷 ${apiData.imagens.length}`;
                imageCount.title = `${apiData.imagens.length} imagens disponíveis`;
                card.appendChild(imageCount);
            }

            // Procura local para inserir o painel
            const cardBody = card.querySelector('.p-evento-body') || card;

            // ===== PAINEL DE INFORMAÇÕES =====
            const infoPanel = document.createElement('div');
            infoPanel.className = 'better-info-panel';

            let panelHTML = '';

            // DETALHES (Tipo, Subtipo, etc.)
            if (apiData.detalhes) {
                const det = apiData.detalhes;

                // Tipo e Subtipo
                if (det.tipo || det.subtipo) {
                    panelHTML += `<div class="better-info-row">`;
                    panelHTML += `<span class="better-info-icon">🏷️</span>`;
                    panelHTML += `<span class="better-info-label">Tipo:</span>`;
                    panelHTML += `<span class="better-info-value">${det.tipo || 'N/A'}`;
                    if (det.subtipo) panelHTML += ` - ${det.subtipo}`;
                    panelHTML += `</span></div>`;
                }

                // Matrícula (Móveis)
                if (det.matricula) {
                    panelHTML += `<div class="better-matricula">🚙 ${det.matricula}</div>`;
                }

                // Tipologia (Imóveis)
                if (det.tipologia) {
                    panelHTML += `<div class="better-tipologia">🏘️ ${det.tipologia}</div>`;
                }

                // Áreas (Imóveis)
                if (det.areaPrivativa || det.areaTotal) {
                    panelHTML += `<div class="better-info-row">`;
                    panelHTML += `<span class="better-info-icon">📐</span>`;
                    panelHTML += `<span class="better-info-label">Área:</span>`;
                    panelHTML += `<span class="better-info-value">`;
                    if (det.areaPrivativa) panelHTML += `${det.areaPrivativa}m²`;
                    if (det.areaTotal && det.areaTotal !== det.areaPrivativa) {
                        panelHTML += ` (Total: ${det.areaTotal}m²)`;
                    }
                    panelHTML += `</span></div>`;
                }

                // Localização (Distrito/Concelho/Freguesia)
                if (det.distrito || det.concelho || det.freguesia) {
                    panelHTML += `<div class="better-location">`;
                    if (det.distrito) panelHTML += `<span class="better-location-item">${det.distrito}</span>`;
                    if (det.concelho) panelHTML += `<span class="better-location-item">${det.concelho}</span>`;
                    if (det.freguesia) panelHTML += `<span class="better-location-item">${det.freguesia}</span>`;
                    panelHTML += `</div>`;
                }
            }

            // GPS
            if (apiData.gps && apiData.gps.latitude && apiData.gps.longitude) {
                panelHTML += `<div class="better-gps-coords">`;
                panelHTML += `📍 GPS: ${apiData.gps.latitude.toFixed(5)}, ${apiData.gps.longitude.toFixed(5)}`;
                panelHTML += `</div>`;
            }

            infoPanel.innerHTML = panelHTML;
            cardBody.appendChild(infoPanel);

            // ===== VALORES =====
            if (apiData.valores) {
                const valuesSection = card.querySelector('.p-evento-footer') || cardBody;
                const highlight = document.createElement('div');
                highlight.className = 'better-value-highlight';

                let valuesHTML = '';
                if (apiData.valores.valorBase) {
                    valuesHTML += `<div class="better-value-item">
                        <span class="better-value-label">Base</span>
                        <span class="better-value-amount">${formatCurrency(apiData.valores.valorBase)}</span>
                    </div>`;
                }
                if (apiData.valores.valorAbertura) {
                    valuesHTML += `<div class="better-value-item">
                        <span class="better-value-label">Abertura</span>
                        <span class="better-value-amount">${formatCurrency(apiData.valores.valorAbertura)}</span>
                    </div>`;
                }
                if (apiData.valores.lanceAtual) {
                    valuesHTML += `<div class="better-value-item">
                        <span class="better-value-label">Lance Atual</span>
                        <span class="better-value-amount">${formatCurrency(apiData.valores.lanceAtual)}</span>
                    </div>`;
                }
                if (apiData.valores.valorMinimo) {
                    valuesHTML += `<div class="better-value-item">
                        <span class="better-value-label">Mínimo</span>
                        <span class="better-value-amount">${formatCurrency(apiData.valores.valorMinimo)}</span>
                    </div>`;
                }

                highlight.innerHTML = valuesHTML;
                valuesSection.appendChild(highlight);
            }
        } else {
            // ====== SEM DADOS DA API - APENAS MELHORIAS VISUAIS ======
            // Pode adicionar melhorias visuais mesmo sem API
        }
    }

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

    // ====================================
    // OBSERVADOR PARA NOVOS CARDS
    // ====================================

    function enhanceAllCards() {
        const cards = document.querySelectorAll('.p-evento');
        cards.forEach(card => enhanceCard(card));
    }

    // Observa mudanças no DOM para cards novos (SPA)
    const observer = new MutationObserver(() => {
        enhanceAllCards();
    });

    // ====================================
    // INICIALIZAÇÃO
    // ====================================

    function init() {
        console.log('🚀 Better E-Leilões Card Enhancer v2.0');

        // Cria botão flutuante
        createDashboardButton();

        // Melhora cards existentes
        enhanceAllCards();

        // Observa novos cards
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('✅ Card enhancer v2.0 ativo - Mostrando GPS, localização, matrícula, tipologia e muito mais!');
    }

    // Aguarda DOM estar pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
