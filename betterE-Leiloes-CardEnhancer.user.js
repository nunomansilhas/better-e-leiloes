// ==UserScript==
// @name         Better E-Leilões - Card Enhancer
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Melhora visualmente os cards nativos do e-leiloes.pt com dados da nossa API (SEM scraping)
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

        /* Indicador de GPS */
        .better-gps-indicator {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: #3b82f6;
            font-size: 11px;
            font-weight: 600;
            margin-top: 4px;
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
            padding: 6px 10px;
            border-radius: 6px;
            border-left: 3px solid #3b82f6;
            margin-top: 8px;
            font-size: 12px;
        }

        .better-value-highlight strong {
            color: #1e40af;
            font-weight: 700;
        }

        /* Contador de imagens */
        .better-image-count {
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            z-index: 10;
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
            badge.textContent = '✓ Dados';
            badge.title = 'Evento está na nossa base de dados';
            card.appendChild(badge);

            // Se tem GPS, adiciona indicador
            if (apiData.gps && apiData.gps.latitude && apiData.gps.longitude) {
                const gpsIndicator = document.createElement('div');
                gpsIndicator.className = 'better-gps-indicator';
                gpsIndicator.innerHTML = `📍 GPS Disponível`;
                gpsIndicator.title = `Lat: ${apiData.gps.latitude}, Lon: ${apiData.gps.longitude}`;

                // Insere no card (procura um bom lugar)
                const cardBody = card.querySelector('.p-evento-body') || card;
                cardBody.appendChild(gpsIndicator);
            }

            // Se tem imagens, mostra contador
            if (apiData.imagens && apiData.imagens.length > 0) {
                const imageCount = document.createElement('div');
                imageCount.className = 'better-image-count';
                imageCount.textContent = `📷 ${apiData.imagens.length}`;
                imageCount.title = `${apiData.imagens.length} imagens disponíveis`;
                card.appendChild(imageCount);
            }

            // Destaca valores se disponíveis
            if (apiData.valores && apiData.valores.valorBase) {
                const valuesSection = card.querySelector('.p-evento-footer, .p-evento-body');
                if (valuesSection) {
                    const highlight = document.createElement('div');
                    highlight.className = 'better-value-highlight';

                    let html = '';
                    if (apiData.valores.valorBase) {
                        html += `<strong>Base:</strong> ${formatCurrency(apiData.valores.valorBase)} `;
                    }
                    if (apiData.valores.lanceAtual) {
                        html += `<strong>Atual:</strong> ${formatCurrency(apiData.valores.lanceAtual)}`;
                    }

                    highlight.innerHTML = html;
                    valuesSection.appendChild(highlight);
                }
            }
        } else {
            // ====== SEM DADOS DA API - APENAS MELHORIAS VISUAIS ======

            // Pode adicionar melhorias visuais mesmo sem API
            // Por exemplo, formatar melhor os valores que já existem no card nativo
            // (Implementar conforme necessário)
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
        console.log('🚀 Better E-Leilões Card Enhancer v1.0');

        // Cria botão flutuante
        createDashboardButton();

        // Melhora cards existentes
        enhanceAllCards();

        // Observa novos cards
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('✅ Card enhancer ativo');
    }

    // Aguarda DOM estar pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
