// ==UserScript==
// @name         betterE-Leiloes (View Only)
// @namespace    http://tampermonkey.net/
// @version      13.0
// @description  Extensão para E-Leiloes.pt com native card enrichment e visualização de dados (scraping gerido pelo servidor)
// @author       Nuno Mansilhas
// @match        https://www.e-leiloes.pt/*
// @icon         https://www.e-leiloes.pt/favicon.ico
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_deleteValue
// ==/UserScript==

(function() {
    'use strict';

    // ====================================
    // ESTILOS CSS PARA NATIVE CARDS
    // ====================================
    
    const styles = document.createElement('style');
    styles.textContent = `
        /* Badges superiores (✓ e ?) */
        .eleiloes-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            font-size: 11px;
            font-weight: 700;
            color: white;
            cursor: help;
            transition: transform 0.2s ease;
        }
        
        .eleiloes-badge:hover {
            transform: scale(1.15);
        }
        
        .eleiloes-badge.success {
            background: #10b981;
        }
        
        .eleiloes-badge.info {
            background: #3b82f6;
        }
        
        /* Ícone de mapa */
        .eleiloes-map-icon {
            font-size: 12px;
            color: #3b82f6;
            margin-left: 4px;
            cursor: pointer;
            transition: color 0.2s ease;
        }
        
        .eleiloes-map-icon:hover {
            color: #2563eb;
        }
        
        /* Valores inline */
        .eleiloes-values-inline {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
            font-size: 11px;
        }
        
        .value-inline-item {
            display: flex;
            gap: 4px;
            align-items: baseline;
        }
        
        .value-inline-label {
            font-weight: 600;
            color: #64748b;
        }
        
        .value-inline-amount {
            font-weight: 500;
            color: #334155;
        }
        
        .value-inline-amount.highlight {
            font-weight: 700;
            color: #059669;
        }
        
        .value-separator {
            color: #cbd5e1;
            font-weight: 300;
        }
        
        /* Data relativa */
        .eleiloes-date-relative {
            font-size: 11px;
            font-weight: 600;
            color: #64748b;
            white-space: nowrap;
        }
        
        .eleiloes-date-relative.urgent {
            color: #dc2626;
            font-weight: 700;
        }
        
        /* Loading overlay */
        .eleiloes-loading {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(2px);
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            z-index: 100;
        }
        
        /* Spinner animado */
        .eleiloes-spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #e2e8f0;
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: eleiloes-spin 0.8s linear infinite;
        }
        
        @keyframes eleiloes-spin {
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(styles);

    // ====================================
    // CONFIGURAÇÃO DA API
    // ====================================
    
    const CONFIG = {
        API_BASE_URL: 'http://localhost:8000/api',
        RETRY_ATTEMPTS: 3,
        RETRY_DELAY: 1000, // ms
        POLL_INTERVAL: 2000, // ms para polling de status
        CACHE_TTL: 3600000 // 1 hora em ms
    };

    // ====================================
    // FUNÇÕES DE API CLIENT
    // ====================================

    async function fetchWithRetry(url, options = {}, retries = CONFIG.RETRY_ATTEMPTS) {
        for (let i = 0; i < retries; i++) {
            try {
                const response = await fetch(url, {
                    ...options,
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return await response.json();
            } catch (error) {
                console.error(`Tentativa ${i + 1}/${retries} falhou:`, error);
                
                if (i === retries - 1) throw error;
                
                await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY));
            }
        }
    }

    async function getEventFromAPI(reference) {
        const url = `${CONFIG.API_BASE_URL}/events/${reference}`;
        return await fetchWithRetry(url);
    }

    async function listEventsFromAPI(page = 1, limit = 50, filters = {}) {
        let url = `${CONFIG.API_BASE_URL}/events?page=${page}&limit=${limit}`;

        if (filters.tipoEvento) url += `&tipo_evento=${encodeURIComponent(filters.tipoEvento)}`;
        if (filters.distrito) url += `&distrito=${encodeURIComponent(filters.distrito)}`;

        return await fetchWithRetry(url);
    }

    async function getAPIStats() {
        const url = `${CONFIG.API_BASE_URL}/stats`;
        return await fetchWithRetry(url);
    }

    // ====================================
    // EXTRAÇÃO DE REFERÊNCIAS DA PÁGINA
    // ====================================

    function extractReferencesFromPage() {
        const references = [];
        const cards = document.querySelectorAll('a[href*="/leilao/imovel/"]');
        
        cards.forEach(card => {
            const href = card.getAttribute('href');
            const match = href.match(/\/leilao\/imovel\/([^/]+)/);
            if (match && match[1]) {
                references.push(match[1]);
            }
        });
        
        return [...new Set(references)]; // Remove duplicados
    }

    // ====================================
    // INTEGRAÇÃO COM CARDS
    // ====================================

    // ==== VISUAL-ONLY ENHANCEMENT (NO API) ====
    // Enhances cards using only data already present in the HTML
    

    
    function extractCardDataFromHTML(card) {
        // Accepts a third argument: isApiData (default false)
        try {
            // Extract reference
            const refElement = card.querySelector('.pi-tag + span');
            const reference = refElement ? refElement.textContent.trim() : null;
            
            // Get all text from footer
            const footer = card.querySelector('.p-evento-footer');
            if (!footer) return null;
            
            const allText = footer.textContent;
            
            // Extract valores using regex
            const vbMatch = allText.match(/VB:\s*([0-9\s,\.]+\s*€)/);
            const vmMatch = allText.match(/VM:\s*([0-9\s,\.]+\s*€)/);
            const laMatch = allText.match(/LA:\s*([0-9\s,\.]+\s*€)/);
            const pmaMatch = allText.match(/PMA:\s*([0-9\s,\.]+\s*€)/);
            const vaMatch = allText.match(/VA:\s*([0-9\s,\.]+\s*€)/);
            
            // Extract dates (format: DD/MM/YYYY)
            const dateMatches = allText.match(/(\d{2}\/\d{2}\/\d{4})/g);
            const dataFim = dateMatches && dateMatches.length > 0 ? dateMatches[dateMatches.length - 1] : null;
            
            return {
                reference,
                valores: {
                    VB: vbMatch ? vbMatch[1].trim() : null,
                    VM: vmMatch ? vmMatch[1].trim() : null,
                    LA: laMatch ? laMatch[1].trim() : null,
                    PMA: pmaMatch ? pmaMatch[1].trim() : null,
                    VA: vaMatch ? vaMatch[1].trim() : null
                },
                dataFim
            };
        } catch (err) {
            console.error('Error extracting card data:', err);
            return null;
        }
    }
    
    function reorganizeCardVisual(card, data) {
        try {
            console.log('🔧 reorganizeCardVisual chamada para:', card);
            
            // ==== ADD BADGES TO HEADER ====
            // Procurar o header do card (primeiro flex container com título)
            const header = card.querySelector('.flex.w-full.flex-wrap.align-items-center.justify-content-between') || 
                           card.querySelector('.p-evento-header') ||
                           card.querySelector('[class*="header"]');
            
            if (!header) {
                console.warn('⚠️ Header não encontrado no card');
                console.log('Card HTML:', card.innerHTML.substring(0, 500));
                return;
            }
            
            console.log('✅ Header encontrado:', header.className);
            
            // Check if badges already exist
            let badgeContainer = header.querySelector('.eleiloes-badges-container');
            if (!badgeContainer) {
                badgeContainer = document.createElement('div');
                badgeContainer.className = 'eleiloes-badges-container';
                badgeContainer.style.cssText = 'display: flex; gap: 4px; margin-left: auto;';
                header.appendChild(badgeContainer);
            } else {
                badgeContainer.innerHTML = ''; // Clear existing badges
            }
            
            // Badge 1: Has lances (✓)
            if (data.valores.LA || data.valores.PMA) {
                const lanceBadge = document.createElement('span');
                lanceBadge.className = 'eleiloes-badge success';
                lanceBadge.textContent = '✓';
                lanceBadge.setAttribute('data-tooltip', 'Tem lances ativos');
                badgeContainer.appendChild(lanceBadge);
            }
            
            // Badge 2: Discount percentage (?)
            if (data.valores.VM && data.valores.VB) {
                const vm = parseFloat(data.valores.VM.replace(/[^\d,]/g, '').replace(',', '.'));
                const vb = parseFloat(data.valores.VB.replace(/[^\d,]/g, '').replace(',', '.'));
                
                if (!isNaN(vm) && !isNaN(vb) && vm > 0) {
                    const discount = ((vb - vm) / vm * 100).toFixed(1);
                    const discountBadge = document.createElement('span');
                    discountBadge.className = 'eleiloes-badge info';
                    discountBadge.textContent = '?';
                    discountBadge.setAttribute('data-tooltip', `Desconto: ${discount}% face ao VM`);
                    badgeContainer.appendChild(discountBadge);
                }
            }
            
            // ==== REORGANIZE FOOTER WITH INLINE VALUES ====
            // Procurar o footer (elemento com informações de valores)
            const footer = card.querySelector('.p-evento-footer') ||
                           card.querySelector('.gap-2.text-900.line-height-3') ||
                           card.querySelector('[class*="footer"]') ||
                           card.querySelector('.text-900.line-height-3');
            
            if (!footer) {
                console.warn('⚠️ Footer não encontrado no card');
                return;
            }
            
            console.log('✅ Footer encontrado:', footer.className);
            
            // Skip if already reorganized
            if (footer.hasAttribute('data-simplified')) {
                // If this is API data, allow update
                if (!arguments[2]) {
                    console.log('⏭️ Footer já reorganizado, skip');
                    return;
                }
            }
            
            // Store original content for debugging
            const originalContent = footer.innerHTML;
            console.log('📋 Original footer content length:', originalContent.length);
            
            // Clear footer completely - remove all children
            while (footer.firstChild) {
                footer.removeChild(footer.firstChild);
            }
            
            footer.setAttribute('data-simplified', 'true');
            
            // Create inline values container
            const valuesContainer = document.createElement('div');
            valuesContainer.className = 'eleiloes-values-inline';
            
            // Helper to add value item
            const addValueItem = (label, value, highlight = false) => {
                if (!value) return;
                
                const item = document.createElement('div');
                item.className = 'value-inline-item';
                
                const labelSpan = document.createElement('span');
                labelSpan.className = 'value-inline-label';
                labelSpan.textContent = label + ':';
                
                const amountSpan = document.createElement('span');
                amountSpan.className = 'value-inline-amount' + (highlight ? ' highlight' : '');
                amountSpan.textContent = value;
                
                item.appendChild(labelSpan);
                item.appendChild(document.createTextNode(' '));
                item.appendChild(amountSpan);
                
                valuesContainer.appendChild(item);
            };
            
            // Helper to add separator
            const addSeparator = () => {
                const separator = document.createElement('span');
                separator.className = 'value-separator';
                separator.textContent = '|';
                valuesContainer.appendChild(separator);
            };
            
            // Add values in order: VB | VM | Lance Atual (PMA/LA/VA)
            if (data.valores.VB) {
                addValueItem('VB', data.valores.VB);
                if (data.valores.VM || data.valores.PMA || data.valores.LA || data.valores.VA) {
                    addSeparator();
                }
            }
            
            if (data.valores.VM) {
                addValueItem('VM', data.valores.VM);
                if (data.valores.PMA || data.valores.LA || data.valores.VA) {
                    addSeparator();
                }
            }
            
            // Lance atual (prefer PMA > LA > VA) with highlight
            if (data.valores.PMA) {
                addValueItem('PMA', data.valores.PMA, true);
            } else if (data.valores.LA) {
                addValueItem('LA', data.valores.LA, true);
            } else if (data.valores.VA) {
                addValueItem('VA', data.valores.VA, true);
            }
            
            footer.appendChild(valuesContainer);
            
            // ==== ADD RELATIVE DATE ====
            if (data.dataFim) {
                const dateDiv = document.createElement('div');
                dateDiv.className = 'eleiloes-date-relative';
                const relativeText = getRelativeDate(data.dataFim);
                dateDiv.textContent = relativeText;
                dateDiv.setAttribute('data-exact-date', data.dataFim);
                
                console.log(`📅 Data relativa: "${relativeText}" (original: ${data.dataFim})`);
                
                // Add urgent class if ending today or tomorrow
                if (relativeText.includes('hoje') || relativeText.includes('amanhã')) {
                    dateDiv.classList.add('urgent');
                }
                
                footer.appendChild(dateDiv);
            }
            
            console.log('✅ Footer reorganizado com sucesso');
        } catch (err) {
            console.error('Error reorganizing card:', err);
        }
    }
    
    // ==== API-BASED ENRICHMENT (OPTIONAL) ====
    
    let enrichmentInProgress = false;
    let processedReferences = new Set();

    async function enrichCardsWithAPIData() {
        // Prevent concurrent enrichment
        if (enrichmentInProgress) return;
        enrichmentInProgress = true;
        const references = extractReferencesFromPage();

        // Instead of only new references, process ALL references that do not have data-api-enhanced
        const unenhancedReferences = references.filter(ref => {
            const cardLinks = document.querySelectorAll(`a[href*="${ref}"]`);
            // If any card for this reference does NOT have data-api-enhanced, process it
            return Array.from(cardLinks).some(link => {
                const parentCard = link.closest('.p-evento');
                return parentCard && !parentCard.getAttribute('data-api-enhanced');
            });
        });

        if (unenhancedReferences.length === 0) {
            console.log('[API ENRICH] Nenhum card para enriquecer.');
            enrichmentInProgress = false;
            return;
        }

        console.log(`[API ENRICH] ${unenhancedReferences.length} referências para enriquecer:`, unenhancedReferences);

        // Add loading overlay to all unenhanced cards
        unenhancedReferences.forEach(ref => {
            const cardLinks = document.querySelectorAll(`a[href*="${ref}"]`);
            cardLinks.forEach(link => {
                const parentCard = link.closest('.p-evento');
                if (parentCard && !parentCard.getAttribute('data-api-enhanced') && !parentCard.querySelector('.eleiloes-loading')) {
                    addLoadingOverlay(parentCard);
                }
            });
        });

        // Process each reference with API enrichment
        for (const ref of unenhancedReferences) {
            try {
                console.log(`[API ENRICH] Buscando dados da API para referência: ${ref}`);
                const data = await getEventFromAPI(ref);
                console.log(`[API ENRICH] Dados recebidos para ${ref}:`, data);
                addBadgesToCard(ref, data);
                console.log(`[API ENRICH] Card atualizado para referência: ${ref}`);
                processedReferences.add(ref);
                await new Promise(resolve => setTimeout(resolve, 50)); // 50ms delay entre cards
            } catch (error) {
                console.warn(`[API ENRICH] Erro ao buscar/enriquecer referência ${ref}:`, error);
                // Remove loading mesmo em erro
                const cardLinks = document.querySelectorAll(`a[href*="${ref}"]`);
                cardLinks.forEach(link => {
                    const parentCard = link.closest('.p-evento');
                    if (parentCard) {
                        const loadingOverlay = parentCard.querySelector('.eleiloes-loading');
                        if (loadingOverlay) loadingOverlay.remove();
                    }
                });
            }
        }

        enrichmentInProgress = false;
    }

    function addBadgesToCard(reference, data) {
        // Encontra todos os cards pela referência
        const cards = document.querySelectorAll(`a[href*="${reference}"]`);
        if (cards.length === 0) return;
        
        cards.forEach(cardLink => {
            const parentCard = cardLink.closest('.p-evento');
            if (!parentCard || parentCard.getAttribute('data-api-enhanced') === 'true') return;

            // Remove loading overlay
            const loadingOverlay = parentCard.querySelector('.eleiloes-loading');
            if (loadingOverlay) loadingOverlay.remove();

            parentCard.setAttribute('data-api-enhanced', 'true');

            // 1. Header: show colored 2-letter prefix for ref, remove event-type tag, add map+event badges
            const headerDiv = parentCard.querySelector('.flex.w-full.flex-wrap.align-items-center.justify-content-between') || parentCard.querySelector('.p-evento-header') || parentCard.querySelector('[class*="header"]');
            if (headerDiv) {
                try {
                    // Remove existing event-type tag if present (example: .pi-tag)
                    const piTag = headerDiv.querySelector('.pi-tag');
                    if (piTag) piTag.remove();

                    // Find reference element (common pattern: .pi-tag + span or strong)
                    let refElem = headerDiv.querySelector('.pi-tag + span') || headerDiv.querySelector('strong') || headerDiv.querySelector('span');
                    // If not found inside header, try searching the whole card
                    if (!refElem) refElem = parentCard.querySelector('.pi-tag + span') || parentCard.querySelector('strong');

                    const refText = reference || (refElem ? refElem.textContent.trim() : '');
                    const tipoNeg = getTipoNegocio(refText) || { color: '#6b7280' };

                    // Build styled reference: first two letters colored
                    const prefix = refText.substring(0,2);
                    const rest = refText.substring(2);
                    const styledRef = document.createElement('div');
                    styledRef.style.cssText = 'display:flex;align-items:center;gap:8px;';
                    const refSpan = document.createElement('span');
                    refSpan.innerHTML = `<span style="color: ${tipoNeg.color}; font-weight:700;">${prefix}</span>${rest}`;
                    refSpan.style.fontSize = '16px';
                    refSpan.style.fontWeight = '700';
                    styledRef.appendChild(refSpan);

                    // Badges container
                    let badgesContainer = headerDiv.querySelector('.eleiloes-badges-container');
                    if (!badgesContainer) {
                        badgesContainer = document.createElement('div');
                        badgesContainer.className = 'eleiloes-badges-container';
                        badgesContainer.style.cssText = 'display: flex; gap: 6px; margin-left: auto; align-items: center;';
                    }
                    badgesContainer.innerHTML = '';

                    // Badge: Google Maps (if GPS exists)
                    if (data.gps && data.gps.latitude) {
                        const mapsUrl = `https://www.google.com/maps?q=${data.gps.latitude},${data.gps.longitude}`;
                        const mapAnchor = document.createElement('a');
                        mapAnchor.href = mapsUrl;
                        mapAnchor.target = '_blank';
                        mapAnchor.rel = 'noopener noreferrer';
                        mapAnchor.title = 'Abrir no Google Maps';
                        const mapBadge = document.createElement('span');
                        mapBadge.className = 'eleiloes-badge info eleiloes-map-icon';
                        mapBadge.innerHTML = '📍';
                        mapAnchor.appendChild(mapBadge);
                        badgesContainer.appendChild(mapAnchor);
                    }

                    // Badge: Open event (opens new window)
                    const eventUrl = `https://www.e-leiloes.pt/evento/${encodeURIComponent(reference)}`;
                    const eventAnchor = document.createElement('a');
                    eventAnchor.href = eventUrl;
                    eventAnchor.target = '_blank';
                    eventAnchor.rel = 'noopener noreferrer';
                    eventAnchor.title = 'Abrir evento em nova janela';
                    const eventBadge = document.createElement('span');
                    eventBadge.className = 'eleiloes-badge info';
                    eventBadge.innerHTML = '🔗';
                    eventAnchor.appendChild(eventBadge);
                    badgesContainer.appendChild(eventAnchor);

                    // Note: API badge removed - only Maps and Event badges as per requirements

                    // Replace or inject styledRef into header
                    // Remove existing simple ref text if present
                    if (refElem && refElem.parentNode) {
                        refElem.parentNode.insertBefore(styledRef, refElem);
                        refElem.remove();
                    } else {
                        headerDiv.insertBefore(styledRef, headerDiv.firstChild);
                    }

                    // Ensure badges container is appended
                    if (!headerDiv.contains(badgesContainer)) headerDiv.appendChild(badgesContainer);
                } catch (err) {
                    console.warn('Erro ao atualizar header nativo:', err);
                }
            }

            // 2. Update card body with API details (matching modal structure)
            const infoContainers = parentCard.querySelectorAll('.p-evento-content, .p-evento-body, .flex.flex-column.gap-2');
            infoContainers.forEach(container => {
                container.innerHTML = '';
                container.style.cssText = 'display: flex; flex-direction: column; gap: 8px; padding: 0.75rem; font-size: 13px;';

                const detalhes = data.detalhes || {};
                const gps = data.gps || {};

                // Classificação (Tipo, Subtipo, Tipologia)
                if (detalhes.tipo || detalhes.subtipo || detalhes.tipologia) {
                    const classDiv = document.createElement('div');
                    classDiv.style.cssText = 'display: flex; flex-wrap: wrap; gap: 12px; padding: 8px; background: #f9fafb; border-radius: 6px; border: 1px solid #e5e7eb;';
                    const parts = [];
                    if (detalhes.tipo) parts.push(`<span style="color: #6b7280; font-size: 11px; font-weight: 600;">Tipo:</span> <span style="color: #111827; font-weight: 600; font-size: 13px;">${detalhes.tipo}</span>`);
                    if (detalhes.subtipo) parts.push(`<span style="color: #6b7280; font-size: 11px; font-weight: 600;">Subtipo:</span> <span style="color: #111827; font-weight: 500; font-size: 13px;">${detalhes.subtipo}</span>`);
                    if (detalhes.tipologia) parts.push(`<span style="color: #6b7280; font-size: 11px; font-weight: 600;">Tipologia:</span> <span style="color: #111827; font-weight: 500; font-size: 13px;">${detalhes.tipologia}</span>`);
                    classDiv.innerHTML = parts.join('<span style="color: #cbd5e1; margin: 0 4px;">|</span>');
                    container.appendChild(classDiv);
                }

                // Áreas (para imóveis)
                if (detalhes.areaPrivativa || detalhes.areaDependente || detalhes.areaTotal) {
                    const areaDiv = document.createElement('div');
                    areaDiv.style.cssText = 'display: flex; flex-wrap: wrap; gap: 12px; padding: 8px; background: #f0f9ff; border-radius: 6px; border: 1px solid #bae6fd;';
                    const parts = [];
                    if (detalhes.areaPrivativa) parts.push(`<span style="color: #0284c7; font-size: 11px; font-weight: 600;">Privativa:</span> <span style="color: #111827; font-weight: 600; font-size: 13px;">${formatArea(detalhes.areaPrivativa)} m²</span>`);
                    if (detalhes.areaDependente) parts.push(`<span style="color: #0284c7; font-size: 11px; font-weight: 600;">Dependente:</span> <span style="color: #111827; font-weight: 600; font-size: 13px;">${formatArea(detalhes.areaDependente)} m²</span>`);
                    if (detalhes.areaTotal) parts.push(`<span style="color: #0284c7; font-size: 11px; font-weight: 700;">Total:</span> <span style="color: #1e40af; font-weight: 700; font-size: 14px;">${formatArea(detalhes.areaTotal)} m²</span>`);
                    areaDiv.innerHTML = parts.join('<span style="color: #cbd5e1; margin: 0 4px;">|</span>');
                    container.appendChild(areaDiv);
                }

                // Características do Veículo (para móveis)
                if (detalhes.matricula || detalhes.marca || detalhes.modelo || detalhes.ano || detalhes.combustivel || detalhes.cilindrada || detalhes.cor) {
                    const carDiv = document.createElement('div');
                    carDiv.style.cssText = 'display: flex; flex-wrap: wrap; gap: 10px; padding: 8px; background: #fef3c7; border-radius: 6px; border: 1px solid #fde68a;';
                    const parts = [];
                    if (detalhes.matricula) parts.push(`<span style="color: #92400e; font-size: 11px; font-weight: 600;">Matrícula:</span> <span style="color: #111827; font-weight: 600; font-size: 12px;">${detalhes.matricula}</span>`);
                    if (detalhes.marca) parts.push(`<span style="color: #92400e; font-size: 11px; font-weight: 600;">Marca:</span> <span style="color: #111827; font-weight: 500; font-size: 12px;">${detalhes.marca}</span>`);
                    if (detalhes.modelo) parts.push(`<span style="color: #92400e; font-size: 11px; font-weight: 600;">Modelo:</span> <span style="color: #111827; font-weight: 500; font-size: 12px;">${detalhes.modelo}</span>`);
                    if (detalhes.ano) parts.push(`<span style="color: #92400e; font-size: 11px; font-weight: 600;">Ano:</span> <span style="color: #111827; font-weight: 500; font-size: 12px;">${detalhes.ano}</span>`);
                    if (detalhes.combustivel) parts.push(`<span style="color: #92400e; font-size: 11px; font-weight: 600;">Combustível:</span> <span style="color: #111827; font-weight: 500; font-size: 12px;">${detalhes.combustivel}</span>`);
                    if (detalhes.cilindrada) parts.push(`<span style="color: #92400e; font-size: 11px; font-weight: 600;">Cilindrada:</span> <span style="color: #111827; font-weight: 500; font-size: 12px;">${detalhes.cilindrada}</span>`);
                    if (detalhes.cor) parts.push(`<span style="color: #92400e; font-size: 11px; font-weight: 600;">Cor:</span> <span style="color: #111827; font-weight: 500; font-size: 12px;">${detalhes.cor}</span>`);
                    carDiv.innerHTML = parts.join('<span style="color: #cbd5e1; margin: 0 4px;">|</span>');
                    container.appendChild(carDiv);
                }

                // Localização
                if (detalhes.freguesia || detalhes.concelho || detalhes.distrito) {
                    const locDiv = document.createElement('div');
                    locDiv.style.cssText = 'display: flex; flex-wrap: wrap; gap: 12px; padding: 8px; background: #eff6ff; border-radius: 6px; border: 1px solid #93c5fd;';
                    const parts = [];
                    if (detalhes.freguesia) parts.push(`<span style="color: #1e40af; font-size: 11px; font-weight: 600;">Freguesia:</span> <span style="color: #1e40af; font-weight: 600; font-size: 13px;">${detalhes.freguesia}</span>`);
                    if (detalhes.concelho) parts.push(`<span style="color: #1e40af; font-size: 11px; font-weight: 600;">Concelho:</span> <span style="color: #1e40af; font-weight: 600; font-size: 13px;">${detalhes.concelho}</span>`);
                    if (detalhes.distrito) parts.push(`<span style="color: #1e40af; font-size: 11px; font-weight: 600;">Distrito:</span> <span style="color: #1e40af; font-weight: 600; font-size: 13px;">${detalhes.distrito}</span>`);
                    locDiv.innerHTML = parts.join('<span style="color: #cbd5e1; margin: 0 4px;">|</span>');
                    container.appendChild(locDiv);
                }
            });

            // 3. Update footer with values row (VB | VA | VM | PMA) and start/end datetime
            const footer = parentCard.querySelector('.p-evento-footer');
            if (footer) {
                try {
                    // Build values row
                    footer.dataset.simplified = 'true';
                    footer.innerHTML = '';
                    footer.style.cssText = 'display: flex; flex-direction: column; gap:6px; margin-top: 0.5rem; padding: 0.5rem 0.75rem; background: rgb(241, 245, 249); border-radius: 0 0 8px 8px;';

                    const valuesRow = document.createElement('div');
                    valuesRow.style.cssText = 'display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-weight:600;';
                    const v = data.valores || {};

                    // Helper to try many possible API keys for a monetary field
                    const getMonetaryField = (obj, keys) => {
                        for (const k of keys) {
                            if (!obj) continue;
                            if (Object.prototype.hasOwnProperty.call(obj, k) && obj[k] !== null && obj[k] !== undefined && obj[k] !== '') return obj[k];
                        }
                        return null;
                    };

                    const VB = getMonetaryField(v, ['valorBase', 'valor_base', 'VB', 'vb', 'base', 'valorBaseFormatted', 'valor_base_format']);
                    const VA = getMonetaryField(v, ['valorAbertura', 'valor_abertura', 'VA', 'va', 'valorAberturaFormatted', 'valorAbert']);
                    const VM = getMonetaryField(v, ['valorMercado', 'valor_mercado', 'VM', 'vm', 'valorMerc']);
                    const PMA = getMonetaryField(v, ['lanceAtual', 'lance_atual', 'PMA', 'pma', 'lanceAtualFormatted', 'lance', 'LA', 'la']);

                    const makeVal = (label, value, highlight) => {
                        if (!value && value !== 0) return null;
                        const item = document.createElement('div');
                        item.style.cssText = highlight
                            ? 'display:flex;align-items:baseline;gap:6px;padding:6px 12px;background:#d1fae5;border-radius:6px;'
                            : 'display:flex;align-items:baseline;gap:6px;';

                        const labelSpan = document.createElement('span');
                        labelSpan.style.cssText = highlight
                            ? 'color:#059669;font-size:11px;font-weight:700;'
                            : 'color:#6b7280;font-size:11px;font-weight:600;';
                        labelSpan.textContent = label + ':';

                        const amountSpan = document.createElement('span');
                        amountSpan.style.cssText = highlight
                            ? 'color:#059669;font-size:14px;font-weight:700;'
                            : 'color:#111827;font-size:13px;font-weight:600;';
                        amountSpan.textContent = formatMoneyValue(value);

                        item.appendChild(labelSpan);
                        item.appendChild(amountSpan);
                        return item;
                    };

                    const vbEl = makeVal('VB', VB, false);
                    const vaEl = makeVal('VA', VA, false);
                    const vmEl = makeVal('VM', VM, false);
                    const pmaEl = makeVal('PMA', PMA, true);

                    const addSeparator = () => {
                        const sep = document.createElement('span');
                        sep.style.cssText = 'color:#cbd5e1;font-weight:400;';
                        sep.textContent = '|';
                        return sep;
                    };

                    if (vbEl) {
                        valuesRow.appendChild(vbEl);
                        if (vaEl || vmEl || pmaEl) valuesRow.appendChild(addSeparator());
                    }
                    if (vaEl) {
                        valuesRow.appendChild(vaEl);
                        if (vmEl || pmaEl) valuesRow.appendChild(addSeparator());
                    }
                    if (vmEl) {
                        valuesRow.appendChild(vmEl);
                        if (pmaEl) valuesRow.appendChild(addSeparator());
                    }
                    if (pmaEl) valuesRow.appendChild(pmaEl);

                    footer.appendChild(valuesRow);

                    // Dates row
                    const datesRow = document.createElement('div');
                    datesRow.style.cssText = 'display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:12px;color:#334155;';
                    const inicio = data.dataInicio || data.inicio || data.start || null;
                    const fim = data.dataFim || data.fim || data.end || null;
                    if (inicio) {
                        const d1 = document.createElement('div');
                        d1.innerHTML = `<span style="color:#6b7280;font-weight:600;margin-right:6px;">Início:</span><span style=\"font-weight:700\">${formatDateTimePT(inicio)}</span>`;
                        datesRow.appendChild(d1);
                    }
                    if (fim) {
                        const d2 = document.createElement('div');
                        d2.innerHTML = `<span style="color:#6b7280;font-weight:600;margin-right:6px;">Fim:</span><span style=\"font-weight:700;color:#dc2626\">${formatDateTimePT(fim)}</span>`;
                        datesRow.appendChild(d2);
                    }
                    if (datesRow.children.length) footer.appendChild(datesRow);
                } catch (err) {
                    console.warn('Erro ao atualizar footer nativo:', err);
                }
            }

            // 4. Neutralize internal links and make clicks open event in a new window
            try {
                const internalAnchors = parentCard.querySelectorAll('a[href]');
                internalAnchors.forEach(a => {
                    const href = a.getAttribute('href') || '';
                    if (href.includes('/evento/') || href.includes('/leilao/')) {
                        a.addEventListener('click', (ev) => {
                            ev.preventDefault();
                            ev.stopPropagation();
                            window.open(eventUrl, '_blank');
                        });
                        a.removeAttribute('href');
                        a.style.cursor = 'pointer';
                    }
                });

                // Clicking the card opens event in new tab
                parentCard.style.cursor = 'pointer';
                parentCard.addEventListener('click', (ev) => {
                    // avoid when clicking on links/buttons inside
                    const tag = ev.target.tagName.toLowerCase();
                    if (tag === 'a' || tag === 'button' || ev.target.closest('a')) return;
                    window.open(eventUrl, '_blank');
                });
            } catch (err) {
                console.warn('Erro ao aplicar comportamento de clique no card:', err);
            }
        });
    }

    function addLoadingOverlay(cardElement) {
        const overlay = document.createElement('div');
        overlay.className = 'eleiloes-loading';
        overlay.innerHTML = `
            <div class="eleiloes-spinner"></div>
        `;
        cardElement.appendChild(overlay);
    }

    // Formata data para PT (DD/MM/YYYY)
    function formatDatePT(dateString) {
        const date = new Date(dateString);
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}/${month}/${year}`;
    }

    // Formata data e hora para PT (DD/MM/YYYY HH:MM:SS)
    function formatDateTimePT(dateString) {
        if (!dateString) return '';
        const d = new Date(dateString);
        if (isNaN(d.getTime())) return dateString;
        const day = String(d.getDate()).padStart(2, '0');
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const year = d.getFullYear();
        const hh = String(d.getHours()).padStart(2, '0');
        const mm = String(d.getMinutes()).padStart(2, '0');
        const ss = String(d.getSeconds()).padStart(2, '0');
        return `${day}/${month}/${year} ${hh}:${mm}:${ss}`;
    }

    // Calcula data relativa (Termina hoje, Termina em 2 dias, etc)
    function enhanceNativeCardsVisual() {
        const cards = document.querySelectorAll('.p-evento:not([data-visual-enhanced])');
        if (cards.length === 0) {
            console.log('⚠️ Nenhum card encontrado para enhancement');
            return;
        }
        console.log(`🎨 [v11 logic] Enhancing ${cards.length} cards visually (no API)`);
        let enhancedCount = 0;
        cards.forEach((card, index) => {
            try {
                if (card.hasAttribute('data-processing')) return;
                card.setAttribute('data-processing', 'true');
                // --- v11 extraction logic ---
                const footer = card.querySelector('.p-evento-footer');
                if (!footer) {
                    console.warn('⚠️ Footer não encontrado no card');
                    card.removeAttribute('data-processing');
                    return;
                }
                const refElement = card.querySelector('.pi-tag + span');
                const reference = refElement ? refElement.textContent.trim() : '';
                // Extract VB, VM, PMA/LA, endDate
                const footerText = footer.innerText || footer.textContent || '';
                const vbMatch = footerText.match(/VB:\s*([0-9\s,\.]+) ?€/);
                const vmMatch = footerText.match(/VM:\s*([0-9\s,\.]+) ?€/);
                const laMatch = footerText.match(/LA:\s*([0-9\s,\.]+) ?€/);
                const pmaMatch = footerText.match(/PMA:\s*([0-9\s,\.]+) ?€/);
                const vaMatch = footerText.match(/VA:\s*([0-9\s,\.]+) ?€/);
                const dateMatches = footerText.match(/(\d{2}\/\d{2}\/\d{4})/g);
                const endDate = dateMatches && dateMatches.length > 0 ? dateMatches[dateMatches.length - 1] : null;
                // Prefer PMA > LA > VA
                let lanceValue = pmaMatch ? pmaMatch[1].trim() : (laMatch ? laMatch[1].trim() : (vaMatch ? vaMatch[1].trim() : null));
                let lanceLabel = pmaMatch ? 'PMA' : (laMatch ? 'LA' : (vaMatch ? 'VA' : 'LANCE'));
                // --- v11 header badges ---
                const headerDiv = card.querySelector('.flex.w-full.flex-wrap.align-items-center.justify-content-between');
                if (headerDiv && !headerDiv.querySelector('.eleiloes-badge')) {
                    const hasLance = lanceValue && parseFloat(lanceValue.replace(/\s/g, '').replace(/\./g, '').replace(',', '.')) > 0;
                    const badge1 = document.createElement('span');
                    badge1.className = `eleiloes-badge ${hasLance ? 'success' : 'danger'}`;
                    badge1.innerHTML = hasLance ? '✓' : '✗';
                    badge1.setAttribute('data-tooltip', hasLance ? 'Tem lances ativos' : 'Sem lances');
                    const badge2 = document.createElement('span');
                    badge2.className = 'eleiloes-badge info';
                    badge2.innerHTML = '?';
                    const vmValue = vmMatch ? parseFloat(vmMatch[1].replace(/\s/g, '').replace(/\./g, '').replace(',', '.')) : 0;
                    const lanceNum = lanceValue ? parseFloat(lanceValue.replace(/\s/g, '').replace(/\./g, '').replace(',', '.')) : 0;
                    const discount = vmValue > 0 ? ((vmValue - lanceNum) / vmValue * 100).toFixed(1) : 0;
                    badge2.setAttribute('data-tooltip', `Desconto: ${discount}% face ao VM`);
                    const badgesContainer = document.createElement('div');
                    badgesContainer.style.display = 'flex';
                    badgesContainer.style.gap = '4px';
                    badgesContainer.style.marginLeft = 'auto';
                    badgesContainer.appendChild(badge1);
                    badgesContainer.appendChild(badge2);
                    headerDiv.appendChild(badgesContainer);
                }
                // --- v11 footer inline values ---
                if (!footer.getAttribute('data-simplified')) {
                    footer.setAttribute('data-simplified', 'true');
                    footer.innerHTML = '';
                    const valuesDiv = document.createElement('div');
                    valuesDiv.className = 'eleiloes-values-inline';
                    valuesDiv.innerHTML = `
                        <span class="value-inline-item">
                            <span class="value-inline-label">VB:</span>
                            <span class="value-inline-amount">${vbMatch ? vbMatch[1].trim() : 'N/A'} €</span>
                        </span>
                        <span class="value-separator">|</span>
                        <span class="value-inline-item">
                            <span class="value-inline-label">VM:</span>
                            <span class="value-inline-amount">${vmMatch ? vmMatch[1].trim() : 'N/A'} €</span>
                        </span>
                        <span class="value-separator">|</span>
                        <span class="value-inline-item">
                            <span class="value-inline-label">${lanceLabel}:</span>
                            <span class="value-inline-amount ${lanceValue && parseFloat(lanceValue.replace(/\s/g, '').replace(/\./g, '').replace(',', '.')) > 0 ? 'highlight' : ''}">${lanceValue ? lanceValue : 'N/A'} €</span>
                        </span>
                    `;
                    footer.appendChild(valuesDiv);
                    // --- v11 relative date ---
                    if (endDate) {
                        const now = new Date();
                        const parts = endDate.match(/(\d{2})\/(\d{2})\/(\d{4})/);
                        let relativeText = '';
                        if (parts) {
                            const endDateObj = new Date(parts[3], parts[2] - 1, parts[1]);
                            const diff = endDateObj - now;
                            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
                            if (days > 0) {
                                relativeText = `Daqui a ${days} dia${days !== 1 ? 's' : ''}`;
                            } else {
                                relativeText = 'Termina hoje';
                            }
                        }
                        const dateDiv = document.createElement('div');
                        dateDiv.className = `eleiloes-date-relative ${days <= 2 ? 'urgent' : ''}`;
                        dateDiv.textContent = relativeText;
                        dateDiv.setAttribute('data-exact-date', endDate);
                        footer.appendChild(dateDiv);
                    }
                }
                card.setAttribute('data-visual-enhanced', 'true');
                card.removeAttribute('data-processing');
                enhancedCount++;
            } catch (err) {
                console.error(`❌ Erro ao enhancing card ${index + 1}:`, err);
                card.removeAttribute('data-processing');
            }
        });
        console.log(`✅ ${enhancedCount}/${cards.length} cards enhanced com sucesso [v11 logic]`);
    }



    // ====================================
    // MODAL DE CONTROLO
    // ====================================

    function createControlPanel() {
        const panel = document.createElement('div');
        panel.id = 'better-eleiloes-panel';
        panel.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            padding: 15px;
            z-index: 10000;
            min-width: 200px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        panel.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 10px; font-size: 14px;">
                🚀 betterE-Leiloes v13.0
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <button id="btn-open-dashboard" style="${getButtonStyle('#10b981')}; font-size: 14px; padding: 12px 16px;">
                    🏠 Abrir Dashboard
                </button>
                <div style="border-top: 1px solid #e5e7eb; margin: 4px 0;"></div>
                <button id="btn-view-data" style="${getButtonStyle('#3b82f6')}">
                    👁️ Ver Dados
                </button>
                <button id="btn-stats" style="${getButtonStyle('#8b5cf6')}">
                    📊 Estatísticas
                </button>
                <button id="btn-clear-storage" style="${getButtonStyle('#f59e0b')}">
                    🧹 Limpar Storage Site
                </button>
            </div>
        `;

        document.body.appendChild(panel);

        // Event listeners
        document.getElementById('btn-open-dashboard').addEventListener('click', () => {
            window.open('http://localhost:8000/', '_blank');
        });
        document.getElementById('btn-view-data').addEventListener('click', handleViewData);
        document.getElementById('btn-stats').addEventListener('click', handleViewStats);
        document.getElementById('btn-clear-storage').addEventListener('click', handleClearBrowserStorage);
    }

    function getButtonStyle(color) {
        return `
            background: ${color};
            color: white;
            border: none;
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            width: 100%;
            text-align: left;
        `;
    }

    // ====================================
    // HANDLERS DOS BOTÕES
    // ====================================

    async function handleViewData() {
        try {
            console.log('📊 Abrindo modal de dados...');
            const modal = createDataModal();
            document.body.appendChild(modal);
            console.log('✅ Modal adicionada ao DOM:', modal);
            console.log('📏 Modal dimensions:', {
                width: modal.offsetWidth,
                height: modal.offsetHeight,
                zIndex: window.getComputedStyle(modal).zIndex,
                display: window.getComputedStyle(modal).display
            });
            
            console.log('🔍 Carregando dados (página 1, filtro: imovel)...');
            // Default: mostrar apenas imóveis
            await loadDataIntoModal(modal, 1, { tipoEvento: 'imovel' });
            
        } catch (error) {
            console.error('❌ Erro ao carregar dados:', error);
            alert(`❌ Erro ao carregar dados:\n${error.message}`);
        }
    }

    async function handleViewStats() {
        try {
            const stats = await getAPIStats();

            let message = `📊 ESTATÍSTICAS DA BASE DE DADOS\n\n`;
            message += `Total de eventos: ${stats.total_events}\n`;
            message += `Com GPS: ${stats.with_gps}\n`;
            message += `Sem GPS: ${stats.total_events - stats.with_gps}\n\n`;

            if (stats.by_type && Object.keys(stats.by_type).length > 0) {
                message += `Por tipo:\n`;
                Object.entries(stats.by_type).forEach(([tipo, count]) => {
                    message += `  • ${tipo}: ${count}\n`;
                });
            }

            alert(message);

        } catch (error) {
            alert(`❌ Erro ao carregar estatísticas:\n${error.message}`);
            console.error(error);
        }
    }


    function handleClearBrowserStorage() {
        const confirmed = confirm(
            '🧹 LIMPAR STORAGE E CACHE DO SITE\n\n' +
            'Isto vai:\n' +
            '✓ Apagar todo o localStorage do e-leiloes.pt\n' +
            '✓ Apagar todo o sessionStorage\n' +
            '✓ Limpar cookies do site\n' +
            '✓ Recarregar a página\n\n' +
            'Continuar?'
        );
        
        if (!confirmed) return;
        
        try {
            // Limpa localStorage
            const localStorageCount = localStorage.length;
            localStorage.clear();
            
            // Limpa sessionStorage
            const sessionStorageCount = sessionStorage.length;
            sessionStorage.clear();
            
            // Limpa cookies do domínio
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const eqPos = cookie.indexOf('=');
                const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
                document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
                document.cookie = name + '=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;domain=.e-leiloes.pt';
            }
            
            console.log(`🧹 Storage limpo: ${localStorageCount} localStorage items, ${sessionStorageCount} sessionStorage items, ${cookies.length} cookies`);
            
            alert(
                '✅ Storage e cache limpos com sucesso!\n\n' +
                `localStorage: ${localStorageCount} items removidos\n` +
                `sessionStorage: ${sessionStorageCount} items removidos\n` +
                `cookies: ${cookies.length} removidos\n\n` +
                'A página vai recarregar...'
            );
            
            // Recarrega a página com cache refresh (Ctrl+F5)
            location.reload(true);
            
        } catch (error) {
            alert(`❌ Erro ao limpar storage:\n${error.message}`);
            console.error(error);
        }
    }

    // ====================================
    // MODAL DE VISUALIZAÇÃO DE DADOS
    // ====================================

    function createDataModal() {
        const modal = document.createElement('div');
        modal.id = 'data-modal';
        modal.style.cssText = `
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            background: rgba(0,0,0,0.85) !important;
            z-index: 2147483647 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        `;
        
        modal.innerHTML = `
            <div style="
                background: white;
                border-radius: 12px;
                width: 95%;
                max-width: 1400px;
                max-height: 90%;
                display: flex;
                flex-direction: column;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            ">
                <!-- Header -->
                <div style="
                    padding: 20px;
                    border-bottom: 1px solid #e5e7eb;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <h2 style="margin: 0; font-size: 20px; font-weight: 700;">📊 Dados da API</h2>
                        <p id="modal-subtitle" style="margin: 5px 0 0 0; font-size: 13px; color: #6b7280;">Carregando...</p>
                    </div>
                    <button id="close-modal" style="
                        background: #ef4444;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-size: 14px;
                        font-weight: 600;
                        cursor: pointer;
                    ">✕ Fechar</button>
                </div>
                
                <!-- Filters -->
                <div id="modal-filters" style="padding: 15px 20px; border-bottom: 1px solid #e5e7eb;">
                    <div style="display: flex; gap: 10px;">
                        <select id="filter-tipo-evento" style="
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 13px;
                            flex: 1;
                            background: white;
                            cursor: pointer;
                        ">
                            <option value="">📋 Todos os Tipos</option>
                            <option value="imovel" selected>🏠 Apenas Imóveis</option>
                            <option value="movel">🚗 Apenas Móveis</option>
                        </select>
                        <input type="text" id="filter-distrito" placeholder="Filtrar por distrito..." style="
                            padding: 8px 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 6px;
                            font-size: 13px;
                            flex: 1;
                        ">
                        <button id="btn-apply-filters" style="
                            background: #3b82f6;
                            color: white;
                            border: none;
                            padding: 8px 16px;
                            border-radius: 6px;
                            font-size: 13px;
                            font-weight: 600;
                            cursor: pointer;
                        ">🔍 Filtrar</button>
                        <button id="btn-view-list" style="
                            background: #6b7280;
                            color: white;
                            border: none;
                            padding: 8px 12px;
                            border-radius: 6px;
                            font-size: 18px;
                            cursor: pointer;
                            width: 44px;
                            line-height: 1;
                        " title="Ver em Lista">☰</button>
                        <button id="btn-view-grid" style="
                            background: #10b981;
                            color: white;
                            border: none;
                            padding: 8px 12px;
                            border-radius: 6px;
                            font-size: 18px;
                            cursor: pointer;
                            width: 44px;
                            line-height: 1;
                        " title="Ver em Grelha">▦</button>
                    </div>
                </div>
                
                <!-- Content -->
                <div id="modal-content" style="
                    padding: 20px;
                    overflow-y: auto;
                    flex: 1;
                ">
                    <div style="text-align: center; padding: 40px;">
                        <div style="font-size: 40px;">⏳</div>
                        <p>Carregando dados...</p>
                    </div>
                </div>
                
                <!-- Pagination -->
                <div id="modal-pagination" style="
                    padding: 15px 20px;
                    border-top: 1px solid #e5e7eb;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <button id="btn-prev-page" style="
                        background: #6b7280;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-size: 13px;
                        font-weight: 600;
                        cursor: pointer;
                    ">◀ Anterior</button>
                    
                    <span id="page-info" style="font-size: 13px; color: #6b7280;">Página 1 de 1</span>
                    
                    <button id="btn-next-page" style="
                        background: #6b7280;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 6px;
                        font-size: 13px;
                        font-weight: 600;
                        cursor: pointer;
                    ">Próxima ▶</button>
                </div>
            </div>
        `;
        
        // Event listeners
        modal.querySelector('#close-modal').addEventListener('click', () => {
            modalEventListenersSetup = false;
            modal.remove();
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modalEventListenersSetup = false;
                modal.remove();
            }
        });
        
        return modal;
    }

    let currentViewMode = 'grid'; // 'list' ou 'grid'
    let modalEventListenersSetup = false;

    async function loadDataIntoModal(modal, page = 1, filters = {}) {
        const content = modal.querySelector('#modal-content');
        const subtitle = modal.querySelector('#modal-subtitle');
        const pageInfo = modal.querySelector('#page-info');
        const btnPrev = modal.querySelector('#btn-prev-page');
        const btnNext = modal.querySelector('#btn-next-page');
        const btnFilter = modal.querySelector('#btn-apply-filters');
        const btnViewList = modal.querySelector('#btn-view-list');
        const btnViewGrid = modal.querySelector('#btn-view-grid');
        const selectTipo = modal.querySelector('#filter-tipo-evento');
        const inputDistrito = modal.querySelector('#filter-distrito');
        
        // Setup event listeners only once to prevent infinite loop
        if (!modalEventListenersSetup) {
            modalEventListenersSetup = true;
            
            // Auto-filter on tipo change
            selectTipo.addEventListener('change', () => {
                const tipoEvento = selectTipo.value;
                const distrito = inputDistrito.value.trim();
                
                const newFilters = {};
                if (distrito) newFilters.distrito = distrito;
                if (tipoEvento) newFilters.tipoEvento = tipoEvento;
                
                loadDataIntoModal(modal, 1, newFilters);
            });
            
            // Filter button for distrito
            btnFilter.addEventListener('click', () => {
                const tipoEvento = selectTipo.value;
                const distrito = inputDistrito.value.trim();
                
                const newFilters = {};
                if (distrito) newFilters.distrito = distrito;
                if (tipoEvento) newFilters.tipoEvento = tipoEvento;
                
                loadDataIntoModal(modal, 1, newFilters);
            });
            
            // View mode buttons
            btnViewList.addEventListener('click', () => {
                currentViewMode = 'list';
                btnViewList.style.background = '#10b981';
                btnViewGrid.style.background = '#6b7280';
                loadDataIntoModal(modal, page, filters);
            });
            
            btnViewGrid.addEventListener('click', () => {
                currentViewMode = 'grid';
                btnViewList.style.background = '#6b7280';
                btnViewGrid.style.background = '#10b981';
                loadDataIntoModal(modal, page, filters);
            });
        }
        
        // Atualiza select com filtro atual
        if (filters.tipoEvento) {
            selectTipo.value = filters.tipoEvento;
        }
        if (filters.distrito) {
            inputDistrito.value = filters.distrito;
        }
        
        try {
            console.log(`📡 Chamando API: página ${page}, filtros:`, filters);
            const data = await listEventsFromAPI(page, 20, filters);
            console.log(`✅ Recebidos ${data.events.length} eventos de ${data.total} total`);
            
            // Enrich native cards with the loaded data
            data.events.forEach(event => {
                addBadgesToCard(event.reference, event);
            });
            
            subtitle.textContent = `${data.total} eventos encontrados`;
            pageInfo.textContent = `Página ${data.page} de ${data.pages}`;
            
            // Pagination buttons
            btnPrev.disabled = page <= 1;
            btnNext.disabled = page >= data.pages;
            
            // Update button styles based on disabled state
            if (btnPrev.disabled) {
                btnPrev.style.background = '#9ca3af';
                btnPrev.style.cursor = 'not-allowed';
                btnPrev.style.opacity = '0.6';
            } else {
                btnPrev.style.background = '#6b7280';
                btnPrev.style.cursor = 'pointer';
                btnPrev.style.opacity = '1';
            }
            
            if (btnNext.disabled) {
                btnNext.style.background = '#9ca3af';
                btnNext.style.cursor = 'not-allowed';
                btnNext.style.opacity = '0.6';
            } else {
                btnNext.style.background = '#6b7280';
                btnNext.style.cursor = 'pointer';
                btnNext.style.opacity = '1';
            }
            
            btnPrev.onclick = () => {
                if (page > 1) loadDataIntoModal(modal, page - 1, filters);
            };
            btnNext.onclick = () => {
                if (page < data.pages) loadDataIntoModal(modal, page + 1, filters);
            };
            
            // Update button states
            if (currentViewMode === 'grid') {
                btnViewList.style.background = '#6b7280';
                btnViewGrid.style.background = '#10b981';
            } else {
                btnViewList.style.background = '#10b981';
                btnViewGrid.style.background = '#6b7280';
            }
            
            // Render events
            if (data.events.length === 0) {
                content.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #6b7280;">
                        <div style="font-size: 40px;">📭</div>
                        <p>Nenhum evento encontrado</p>
                    </div>
                `;
                return;
            }
            
            if (currentViewMode === 'grid') {
                console.log('🎨 Renderizando em modo GRID');
                const cardsHtml = data.events.map(event => createEventCardCompact(event)).join('');
                console.log(`📦 Gerados ${data.events.length} cards (${cardsHtml.length} chars)`);
                content.innerHTML = `
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                        ${cardsHtml}
                    </div>
                `;
                console.log('✅ Cards inseridos no DOM');
            } else {
                console.log('📋 Renderizando em modo LISTA');
                content.innerHTML = data.events.map(event => createEventCard(event)).join('');
            }
            
        } catch (error) {
            console.error('❌ Erro ao renderizar modal:', error);
            content.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #ef4444;">
                    <div style="font-size: 40px;">❌</div>
                    <p>Erro ao carregar dados</p>
                    <p style="font-size: 12px; margin-top: 10px;">${error.message}</p>
                </div>
            `;
        }
    }

    // Determina tipo de negócio pela referência
    const getTipoNegocio = (reference) => {
        if (!reference) return null;
        const prefix = reference.substring(0, 2).toUpperCase();
        if (prefix === 'NP') return { tipo: 'Negociação Particular', badge: 'NP', color: '#10b981' };
        if (prefix === 'LO') return { tipo: 'Leilão Online', badge: 'LO', color: '#3b82f6' };
        return null;
    };

    // Formata valores monetários
    const formatMoney = (value) => {
        if (!value) return 'N/A';
        return new Intl.NumberFormat('pt-PT', { 
            style: 'currency', 
            currency: 'EUR',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value).replace(/\u00A0/g, ' ');
    };

    // Parse money-like strings to number. Accepts formats like "143 600,00 €", "143.600,00", "143600"
    function parseMoneyToNumber(val) {
        if (val === null || val === undefined) return null;
        if (typeof val === 'number' && !isNaN(val)) return val;
        if (typeof val !== 'string') return null;
        let s = val.trim();
        // Remove currency symbol
        s = s.replace(/€/g, '').replace(/\s+/g, ' ').trim();
        // If contains comma as decimal separator and dot/space as thousand, normalize
        // Examples: "143 600,00" -> "143600.00" ; "143.600,00" -> "143600.00"
        // Remove non-numeric except , and .
        // First handle comma decimal
        const commaDecimal = /,\d{1,2}$/.test(s);
        if (commaDecimal) {
            // remove thousand separators (dots or spaces)
            s = s.replace(/[\.\s]/g, '');
            s = s.replace(',', '.');
        } else {
            // remove spaces
            s = s.replace(/\s/g, '');
        }
        // Remove any non-digit/non-dot
        s = s.replace(/[^0-9.\-]/g, '');
        const n = parseFloat(s);
        if (isNaN(n)) return null;
        return n;
    }

    // Formats a money value which might be a number or a string; returns a readable string (with currency)
    function formatMoneyValue(val) {
        if (val === null || val === undefined) return 'N/A';
        if (typeof val === 'number' && !isNaN(val)) return formatMoney(val);
        if (typeof val === 'string') {
            // If already contains € or non-digit characters, try to preserve human-readable form
            const hasEuro = /€/g.test(val);
            const parsed = parseMoneyToNumber(val);
            if (parsed !== null) return formatMoney(parsed);
            // fallback: return trimmed string (keep currency symbol if present)
            return val.trim();
        }
        return 'N/A';
    }
    
    // Formata áreas com espaços (32 650m²)
    const formatArea = (value) => {
        if (!value) return null;
        return value.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1 ');
    };

    function createEventCard(event) {
        const detalhes = event.detalhes || {};
        const gps = event.gps || {};
        const valores = event.valores || {};
        const tipoEvento = event.tipoEvento || 'imovel';
        const eventoUrl = `https://www.e-leiloes.pt/evento/${event.reference}`;
        const mapsUrl = gps && gps.latitude ? `https://www.google.com/maps?q=${gps.latitude},${gps.longitude}` : null;
        
        return `
            <div style="
                background: white;
                border-radius: 16px;
                padding: 24px;
                margin-bottom: 16px;
                border: 2px solid #e5e7eb;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                transition: all 0.3s ease;
            " onmouseover="this.style.boxShadow='0 8px 24px rgba(0,0,0,0.15)'; this.style.transform='translateY(-2px)'" onmouseout="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.08)'; this.style.transform='translateY(0)'">
                <!-- Header -->
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 20px;">
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                            <span style="font-size: 13px; color: #9ca3af; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">REF</span>
                            <strong style="font-size: 22px; color: #111827; letter-spacing: 0.5px;">
                                ${(() => {
                                    const tipoNeg = getTipoNegocio(event.reference);
                                    if (tipoNeg) {
                                        return `<span style="color: ${tipoNeg.color}; font-weight: 700;">${event.reference.substring(0, 2)}</span>${event.reference.substring(2)}`;
                                    }
                                    return event.reference;
                                })()}
                            </strong>
                            ${(() => {
                                const tipoNeg = getTipoNegocio(event.reference);
                                if (tipoNeg) {
                                    return `<span style="background: ${tipoNeg.color}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;">${tipoNeg.badge}</span>`;
                                }
                                return '';
                            })()}
                        </div>
                        ${detalhes.tipo ? `<div style="font-size: 16px; color: #6b7280; font-weight: 600;">${detalhes.tipo}</div>` : ''}
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <a href="${eventoUrl}" target="_blank" style="
                            background: #3b82f6;
                            color: white;
                            padding: 10px 16px;
                            border-radius: 8px;
                            text-decoration: none;
                            font-size: 13px;
                            font-weight: 600;
                            transition: all 0.2s;
                            display: flex;
                            align-items: center;
                            gap: 6px;
                        " onmouseover="this.style.background='#2563eb'" onmouseout="this.style.background='#3b82f6'">
                            <span>🔗</span>
                            <span>Ver Evento</span>
                        </a>
                    </div>
                </div>
                
                <!-- Valores -->
                <div style="margin-bottom: 18px; padding: 16px; background: #f9fafb; border-radius: 10px; border: 1px solid #e5e7eb;">
                    <div style="font-weight: 600; font-size: 12px; color: #6b7280; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">💰 Valores</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: center;">
                        ${valores.valorBase ? `<div style="display: flex; align-items: baseline; gap: 6px;">
                            <span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Base:</span>
                            <span style="font-weight: 700; color: #111827; font-size: 16px;">${formatMoney(valores.valorBase)}</span>
                        </div>` : ''}
                        ${valores.valorAbertura ? `<div style="display: flex; align-items: baseline; gap: 6px;">
                            <span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Abertura:</span>
                            <span style="font-weight: 700; color: #111827; font-size: 16px;">${formatMoney(valores.valorAbertura)}</span>
                        </div>` : ''}
                        ${valores.valorMinimo ? `<div style="display: flex; align-items: baseline; gap: 6px;">
                            <span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Mínimo:</span>
                            <span style="font-weight: 700; color: #111827; font-size: 16px;">${formatMoney(valores.valorMinimo)}</span>
                        </div>` : ''}
                        ${valores.lanceAtual ? `<div style="display: flex; align-items: baseline; gap: 6px; padding: 6px 12px; background: #d1fae5; border-radius: 6px;">
                            <span style="color: #059669; font-size: 11px; font-weight: 700;">LANCE:</span>
                            <span style="font-weight: 700; color: #059669; font-size: 17px;">${formatMoney(valores.lanceAtual)}</span>
                        </div>` : ''}
                    </div>
                </div>
                
                <!-- Classificação -->
                ${detalhes.tipo || detalhes.subtipo || detalhes.tipologia ? `
                <div style="margin-bottom: 18px;">
                    <div style="font-weight: 600; font-size: 12px; color: #6b7280; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">📋 Classificação</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 16px;">
                        ${detalhes.tipo ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Tipo:</span><span style="color: #111827; font-weight: 600; font-size: 15px;">${detalhes.tipo}</span></div>` : ''}
                        ${detalhes.subtipo ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Subtipo:</span><span style="color: #111827; font-weight: 500; font-size: 15px;">${detalhes.subtipo}</span></div>` : ''}
                        ${detalhes.tipologia ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Tipologia:</span><span style="color: #111827; font-weight: 500; font-size: 15px;">${detalhes.tipologia}</span></div>` : ''}
                    </div>
                </div>
                ` : ''}
                
                <!-- Áreas (só imóveis) -->
                ${detalhes.areaPrivativa || detalhes.areaDependente || detalhes.areaTotal ? `
                <div style="margin-bottom: 18px;">
                    <div style="font-weight: 600; font-size: 12px; color: #6b7280; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">📐 Áreas</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                        ${detalhes.areaPrivativa ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Privativa:</span><span style="color: #111827; font-weight: 600; font-size: 15px;">${formatArea(detalhes.areaPrivativa)} m²</span></div>` : ''}
                        ${detalhes.areaDependente ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Dependente:</span><span style="color: #111827; font-weight: 600; font-size: 15px;">${formatArea(detalhes.areaDependente)} m²</span></div>` : ''}
                        ${detalhes.areaTotal ? `<div style="display: flex; align-items: baseline; gap: 6px; padding: 6px 12px; background: #dbeafe; border-radius: 6px;"><span style="color: #1e40af; font-size: 11px; font-weight: 700;">TOTAL:</span><span style="color: #1e40af; font-weight: 700; font-size: 16px;">${formatArea(detalhes.areaTotal)} m²</span></div>` : ''}
                    </div>
                </div>
                ` : ''}
                
                <!-- Características Veículo (só móveis) -->
                ${detalhes.matricula || detalhes.marca || detalhes.modelo || detalhes.ano || detalhes.combustivel || detalhes.cilindrada || detalhes.cor ? `
                <div style="margin-bottom: 18px;">
                    <div style="font-weight: 600; font-size: 12px; color: #6b7280; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">🚗 Características</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 16px;">
                        ${detalhes.matricula ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Matrícula:</span><span style="color: #111827; font-weight: 600; font-size: 14px;">${detalhes.matricula}</span></div>` : ''}
                        ${detalhes.marca ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Marca:</span><span style="color: #111827; font-weight: 500; font-size: 14px;">${detalhes.marca}</span></div>` : ''}
                        ${detalhes.modelo ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Modelo:</span><span style="color: #111827; font-weight: 500; font-size: 14px;">${detalhes.modelo}</span></div>` : ''}
                        ${detalhes.ano ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Ano:</span><span style="color: #111827; font-weight: 500; font-size: 14px;">${detalhes.ano}</span></div>` : ''}
                        ${detalhes.combustivel ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Combustível:</span><span style="color: #111827; font-weight: 500; font-size: 14px;">${detalhes.combustivel}</span></div>` : ''}
                        ${detalhes.cilindrada ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Cilindrada:</span><span style="color: #111827; font-weight: 500; font-size: 14px;">${detalhes.cilindrada}</span></div>` : ''}
                        ${detalhes.cor ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #9ca3af; font-size: 11px; font-weight: 600;">Cor:</span><span style="color: #111827; font-weight: 500; font-size: 14px;">${detalhes.cor}</span></div>` : ''}
                    </div>
                </div>
                ` : ''}
                
                <!-- Localização -->
                ${detalhes.freguesia || detalhes.concelho || detalhes.distrito || (gps && gps.latitude) ? `
                <div style="padding: 16px; background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-radius: 10px; border: 2px solid #93c5fd;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5">
                                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                                <circle cx="12" cy="10" r="3"></circle>
                            </svg>
                            <span style="font-weight: 700; font-size: 13px; color: #1e40af; text-transform: uppercase; letter-spacing: 0.5px;">Localização</span>
                        </div>
                        ${mapsUrl ? `
                            <a href="${mapsUrl}" target="_blank" style="
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                width: 36px;
                                height: 36px;
                                background: #3b82f6;
                                color: white;
                                text-decoration: none;
                                border-radius: 8px;
                                transition: all 0.2s;
                                box-shadow: 0 2px 6px rgba(59, 130, 246, 0.3);
                            " onmouseover="this.style.background='#2563eb'; this.style.transform='scale(1.1)'" onmouseout="this.style.background='#3b82f6'; this.style.transform='scale(1)'" title="Ver no Google Maps">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                                    <circle cx="12" cy="10" r="3"></circle>
                                </svg>
                            </a>
                        ` : ''}
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 16px;">
                        ${detalhes.freguesia ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #60a5fa; font-size: 11px; font-weight: 600;">Freguesia:</span><span style="color: #1e40af; font-weight: 600; font-size: 14px;">${detalhes.freguesia}</span></div>` : ''}
                        ${detalhes.concelho ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #60a5fa; font-size: 11px; font-weight: 600;">Concelho:</span><span style="color: #1e40af; font-weight: 600; font-size: 14px;">${detalhes.concelho}</span></div>` : ''}
                        ${detalhes.distrito ? `<div style="display: flex; align-items: baseline; gap: 6px;"><span style="color: #60a5fa; font-size: 11px; font-weight: 600;">Distrito:</span><span style="color: #1e40af; font-weight: 600; font-size: 14px;">${detalhes.distrito}</span></div>` : ''}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    }

    function createEventCardCompact(event) {
        const detalhes = event.detalhes || {};
        const gps = event.gps || {};
        const valores = event.valores || {};
        const tipoEvento = event.tipoEvento || 'imovel';
        const eventoUrl = `https://www.e-leiloes.pt/evento/${event.reference}`;
        const mapsUrl = gps && gps.latitude ? `https://www.google.com/maps?q=${gps.latitude},${gps.longitude}` : null;
        
        return `
            <div style="
                background: white;
                border-radius: 14px;
                padding: 18px;
                border: 2px solid ${tipoEvento === 'imovel' ? '#dbeafe' : '#fef3c7'};
                font-size: 12px;
                display: flex;
                flex-direction: column;
                gap: 12px;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            " onmouseover="this.style.boxShadow='0 8px 20px rgba(0,0,0,0.14)'; this.style.transform='translateY(-4px)'" onmouseout="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.06)'; this.style.transform='translateY(0)'">
                <!-- Header -->
                <div>
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                            <span style="font-size: 10px; color: #9ca3af; font-weight: 600; text-transform: uppercase;">REF</span>
                            <strong style="font-size: 15px; color: #111827; letter-spacing: 0.3px;">
                                ${(() => {
                                    const tipoNeg = getTipoNegocio(event.reference);
                                    if (tipoNeg) {
                                        return `<span style="color: ${tipoNeg.color}; font-weight: 700;">${event.reference.substring(0, 2)}</span>${event.reference.substring(2)}`;
                                    }
                                    return event.reference;
                                })()}
                            </strong>
                            ${(() => {
                                const tipoNeg = getTipoNegocio(event.reference);
                                if (tipoNeg) {
                                    return `<span style="background: ${tipoNeg.color}; color: white; padding: 3px 6px; border-radius: 4px; font-size: 9px; font-weight: 700; letter-spacing: 0.3px;">${tipoNeg.badge}</span>`;
                                }
                                return '';
                            })()}
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <a href="${eventoUrl}" target="_blank" 
                               onclick="event.stopPropagation()" style="
                                color: #3b82f6;
                                text-decoration: none;
                                font-size: 18px;
                                transition: transform 0.2s;
                            " title="Ver Evento" onmouseover="this.style.transform='scale(1.3)'" onmouseout="this.style.transform='scale(1)'">🔗</a>
                            ${mapsUrl ? `
                                <a href="${mapsUrl}" target="_blank" 
                                   onclick="event.stopPropagation()" style="
                                    color: #3b82f6;
                                    text-decoration: none;
                                    font-size: 18px;
                                    transition: transform 0.2s;
                                " title="Ver no Mapa" onmouseover="this.style.transform='scale(1.3)'" onmouseout="this.style.transform='scale(1)'">📍</a>
                            ` : ''}
                        </div>
                    </div>
                    ${detalhes.tipo ? `<div style="font-size: 13px; color: #6b7280; font-weight: 600; margin-bottom: 8px;">${detalhes.tipo}</div>` : ''}
                </div>
                
                <!-- Valores -->
                <div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; min-height: 70px;">
                    <div style="font-weight: 600; font-size: 10px; color: #6b7280; margin-bottom: 8px; letter-spacing: 0.5px;">💰 VALORES</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center;">
                        ${valores.valorBase ? `<div style="display: flex; align-items: baseline; gap: 4px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Base:</span><span style="font-weight: 600; color: #111827; font-size: 11px;">${formatMoney(valores.valorBase)}</span></div>` : ''}
                        ${valores.valorMinimo ? `<div style="display: flex; align-items: baseline; gap: 4px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Mín:</span><span style="font-weight: 600; color: #6b7280; font-size: 11px;">${formatMoney(valores.valorMinimo)}</span></div>` : ''}
                        ${valores.lanceAtual ? `<div style="display: flex; align-items: baseline; gap: 4px; padding: 4px 8px; background: #d1fae5; border-radius: 4px;"><span style="color: #059669; font-size: 9px; font-weight: 700;">LANCE:</span><span style="font-weight: 700; color: #059669; font-size: 12px;">${formatMoney(valores.lanceAtual)}</span></div>` : ''}
                    </div>
                </div>
                
                <!-- Classificação -->
                ${detalhes.tipo || detalhes.subtipo || detalhes.tipologia ? `
                <div style="padding: 10px; background: white; border-radius: 8px; border: 1px solid #e5e7eb; min-height: 60px;">
                    <div style="font-weight: 600; font-size: 10px; color: #6b7280; margin-bottom: 6px; letter-spacing: 0.5px;">📋 CLASSIFICAÇÃO</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px; font-size: 11px;">
                        ${detalhes.tipo ? `<div style="display: flex; align-items: baseline; gap: 4px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Tipo:</span><span style="color: #111827; font-weight: 600;">${detalhes.tipo}</span></div>` : ''}
                        ${detalhes.subtipo ? `<div style="display: flex; align-items: baseline; gap: 4px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Subtipo:</span><span style="color: #111827; font-weight: 500;">${detalhes.subtipo}</span></div>` : ''}
                        ${detalhes.tipologia ? `<div style="display: flex; align-items: baseline; gap: 4px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Tipologia:</span><span style="color: #111827; font-weight: 500;">${detalhes.tipologia}</span></div>` : ''}
                    </div>
                </div>
                ` : ''}
                
                <!-- Áreas -->
                ${detalhes.areaPrivativa || detalhes.areaDependente || detalhes.areaTotal ? `
                <div style="padding: 10px; background: white; border-radius: 8px; border: 1px solid #e5e7eb; min-height: 60px;">
                    <div style="font-weight: 600; font-size: 10px; color: #6b7280; margin-bottom: 6px; letter-spacing: 0.5px;">📐 ÁREAS</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center; font-size: 11px;">
                        ${detalhes.areaPrivativa ? `<div style="display: flex; align-items: baseline; gap: 4px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Privativa:</span><span style="color: #111827; font-weight: 600;">${formatArea(detalhes.areaPrivativa)} m²</span></div>` : ''}
                        ${detalhes.areaDependente ? `<div style="display: flex; align-items: baseline; gap: 4px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Depend.:</span><span style="color: #111827; font-weight: 600;">${formatArea(detalhes.areaDependente)} m²</span></div>` : ''}
                        ${detalhes.areaTotal ? `<div style="display: flex; align-items: baseline; gap: 4px; padding: 4px 8px; background: #dbeafe; border-radius: 4px;"><span style="color: #1e40af; font-size: 9px; font-weight: 700;">TOTAL:</span><span style="color: #1e40af; font-weight: 700;">${formatArea(detalhes.areaTotal)} m²</span></div>` : ''}
                    </div>
                </div>
                ` : ''}
                
                <!-- Características Veículo -->
                ${detalhes.matricula || detalhes.marca || detalhes.modelo || detalhes.ano || detalhes.combustivel || detalhes.cilindrada || detalhes.cor ? `
                <div style="padding: 10px; background: white; border-radius: 8px; border: 1px solid #e5e7eb; min-height: 60px;">
                    <div style="font-weight: 600; font-size: 10px; color: #6b7280; margin-bottom: 6px; letter-spacing: 0.5px;">🚗 CARACTERÍSTICAS</div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; font-size: 10px;">
                        ${detalhes.matricula ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Mat.:</span><span style="color: #111827; font-weight: 600;">${detalhes.matricula}</span></div>` : ''}
                        ${detalhes.marca ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Marca:</span><span style="color: #111827; font-weight: 500;">${detalhes.marca}</span></div>` : ''}
                        ${detalhes.modelo ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Modelo:</span><span style="color: #111827; font-weight: 500;">${detalhes.modelo}</span></div>` : ''}
                        ${detalhes.ano ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Ano:</span><span style="color: #111827; font-weight: 500;">${detalhes.ano}</span></div>` : ''}
                        ${detalhes.combustivel ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Comb.:</span><span style="color: #111827; font-weight: 500;">${detalhes.combustivel}</span></div>` : ''}
                        ${detalhes.cilindrada ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Cilind.:</span><span style="color: #111827; font-weight: 500;">${detalhes.cilindrada}</span></div>` : ''}
                        ${detalhes.cor ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #9ca3af; font-size: 9px; font-weight: 600;">Cor:</span><span style="color: #111827; font-weight: 500;">${detalhes.cor}</span></div>` : ''}
                    </div>
                </div>
                ` : ''}
                
                <!-- Localização BOX AZUL -->
                ${detalhes.freguesia || detalhes.concelho || detalhes.distrito || (gps && gps.latitude) ? `
                <div style="padding: 10px; background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-radius: 8px; border: 2px solid #93c5fd; min-height: 75px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <div style="display: flex; align-items: center; gap: 4px;">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5">
                                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                                <circle cx="12" cy="10" r="3"></circle>
                            </svg>
                            <span style="font-weight: 700; font-size: 9px; color: #1e40af; letter-spacing: 0.5px;">LOCALIZAÇÃO</span>
                        </div>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; font-size: 10px;">
                        ${detalhes.freguesia ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #60a5fa; font-size: 9px; font-weight: 600;">Freg.:</span><span style="color: #1e40af; font-weight: 600;">${detalhes.freguesia}</span></div>` : ''}
                        ${detalhes.concelho ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #60a5fa; font-size: 9px; font-weight: 600;">Conc.:</span><span style="color: #1e40af; font-weight: 600;">${detalhes.concelho}</span></div>` : ''}
                        ${detalhes.distrito ? `<div style="display: flex; align-items: baseline; gap: 3px;"><span style="color: #60a5fa; font-size: 9px; font-weight: 600;">Dist.:</span><span style="color: #1e40af; font-weight: 600;">${detalhes.distrito}</span></div>` : ''}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
    }

    // ====================================
    // INICIALIZAÇÃO
    // ====================================

    let observerTimeout = null;

    function init() {
        console.log('🚀 betterE-Leiloes v12.6 com Visual Enhancement + API iniciado!');
        
        // Cria painel de controlo
        createControlPanel();
        
        // IMMEDIATE: Enhance cards visually using existing HTML (no API needed)
        enhanceNativeCardsVisual();
        
        // OPTIONAL: Enrich cards with API data (triggered by user button or auto)
        enrichCardsWithAPIData();
        
        // Observer para novas páginas (SPA) com debounce
        const observer = new MutationObserver(() => {
            if (observerTimeout) clearTimeout(observerTimeout);
            observerTimeout = setTimeout(() => {
                // FIRST: Visual enhancement (fast, no API)
                enhanceNativeCardsVisual();
                // THEN: API enrichment (if enabled)
                // Re-aplica API enhancement a cards que perderam
                document.querySelectorAll('.p-evento').forEach(card => {
                    if (!card.getAttribute('data-api-enhanced')) {
                        // Try to get reference
                        const refElement = card.querySelector('.pi-tag + span');
                        const reference = refElement ? refElement.textContent.trim() : null;
                        if (reference) {
                            getEventFromAPI(reference).then(data => {
                                addBadgesToCard(reference, data);
                            }).catch(() => {});
                        }
                    }
                });
            }, 500);
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('✅ Extensão pronta! Visual enhancement ativo. API: ' + CONFIG.API_BASE_URL);
    }

    // Aguarda DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
