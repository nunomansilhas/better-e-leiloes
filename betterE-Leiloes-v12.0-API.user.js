// ==UserScript==
// @name         betterE-Leiloes (API Version)
// @namespace    http://tampermonkey.net/
// @version      12.4
// @description  Extensão para E-Leiloes.pt com dados reais via API backend
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

    async function triggerFullScrape(maxPages = null) {
        let url = `${CONFIG.API_BASE_URL}/scrape/all`;
        if (maxPages) url += `?max_pages=${maxPages}`;
        
        return await fetchWithRetry(url, { method: 'POST' });
    }

    async function getScrapeStatus() {
        const url = `${CONFIG.API_BASE_URL}/scrape/status`;
        return await fetchWithRetry(url);
    }

    async function getAPIStats() {
        const url = `${CONFIG.API_BASE_URL}/stats`;
        return await fetchWithRetry(url);
    }

    async function clearAPICache() {
        const url = `${CONFIG.API_BASE_URL}/cache`;
        return await fetchWithRetry(url, { method: 'DELETE' });
    }

    async function clearDatabase() {
        const url = `${CONFIG.API_BASE_URL}/database`;
        console.log('🔗 Chamando DELETE:', url);
        return await fetchWithRetry(url, { method: 'DELETE' });
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

    async function enrichCardsWithAPIData() {
        const references = extractReferencesFromPage();
        
        console.log(`🔍 ${references.length} eventos encontrados na página`);
        
        for (const ref of references) {
            try {
                const data = await getEventFromAPI(ref);
                addBadgesToCard(ref, data);
            } catch (error) {
                console.warn(`⚠️ Evento ${ref} não disponível na API:`, error.message);
            }
        }
    }

    function addBadgesToCard(reference, data) {
        const cards = document.querySelectorAll(`a[href*="${reference}"]`);
        
        cards.forEach(card => {
            // Remove badges existentes
            const existingBadges = card.querySelector('.better-eleiloes-badges');
            if (existingBadges) existingBadges.remove();
            
            // Container de badges
            const badgesContainer = document.createElement('div');
            badgesContainer.className = 'better-eleiloes-badges';
            badgesContainer.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                display: flex;
                flex-direction: column;
                gap: 5px;
                z-index: 100;
            `;
            
            // Badge GPS (apenas imóveis)
            if (data.gps && data.gps.latitude && data.gps.longitude) {
                const gpsBadge = createGPSBadge(data.gps);
                badgesContainer.appendChild(gpsBadge);
            }
            
            // Badge Valores
            if (data.valores && (data.valores.valorBase || data.valores.lanceAtual)) {
                const valoresBadge = createValoresBadge(data.valores);
                badgesContainer.appendChild(valoresBadge);
            }
            
            // Badge Detalhes
            if (data.detalhes) {
                const detailsBadge = createDetailsBadge(data.detalhes, data.tipoEvento);
                badgesContainer.appendChild(detailsBadge);
            }
            
            // Adiciona ao card
            card.style.position = 'relative';
            card.appendChild(badgesContainer);
        });
    }

    function createGPSBadge(gps) {
        const badge = document.createElement('div');
        badge.style.cssText = `
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        `;
        badge.innerHTML = '📍 GPS';
        badge.title = `Lat: ${gps.latitude}, Lon: ${gps.longitude}`;
        
        badge.addEventListener('mouseenter', () => {
            badge.style.transform = 'scale(1.1)';
        });
        
        badge.addEventListener('mouseleave', () => {
            badge.style.transform = 'scale(1)';
        });
        
        badge.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            window.open(`https://www.google.com/maps?q=${gps.latitude},${gps.longitude}`, '_blank');
        });
        
        return badge;
    }

    function createValoresBadge(valores) {
        const badge = document.createElement('div');
        badge.style.cssText = `
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        `;
        
        const formatShort = (value) => {
            if (!value) return 'N/A';
            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M€`;
            if (value >= 1000) return `${(value / 1000).toFixed(0)}k€`;
            return `${value}€`;
        };
        
        let text = '💰';
        if (valores.lanceAtual) {
            text += ` Lance: ${formatShort(valores.lanceAtual)}`;
        } else if (valores.valorBase) {
            text += ` Base: ${formatShort(valores.valorBase)}`;
        }
        
        badge.innerHTML = text;
        
        const tooltipParts = [];
        if (valores.valorBase) tooltipParts.push(`Base: ${valores.valorBase}€`);
        if (valores.valorAbertura) tooltipParts.push(`Abertura: ${valores.valorAbertura}€`);
        if (valores.valorMinimo) tooltipParts.push(`Mínimo: ${valores.valorMinimo}€`);
        if (valores.lanceAtual) tooltipParts.push(`Lance Atual: ${valores.lanceAtual}€`);
        
        badge.title = tooltipParts.join('\n');
        
        badge.addEventListener('mouseenter', () => {
            badge.style.transform = 'scale(1.1)';
        });
        
        badge.addEventListener('mouseleave', () => {
            badge.style.transform = 'scale(1)';
        });
        
        return badge;
    }

    function createDetailsBadge(detalhes, tipoEvento) {
        const badge = document.createElement('div');
        badge.style.cssText = `
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        `;
        
        let text = tipoEvento === 'imovel' ? '🏠' : '🚗';
        
        if (tipoEvento === 'imovel') {
            if (detalhes.tipologia) text += ` ${detalhes.tipologia}`;
            if (detalhes.areaTotal) text += ` | ${detalhes.areaTotal}m²`;
        } else {
            if (detalhes.subtipo) text += ` ${detalhes.subtipo}`;
            if (detalhes.matricula) text += ` | ${detalhes.matricula}`;
        }
        
        badge.innerHTML = text;
        
        badge.title = [
            detalhes.tipo,
            detalhes.subtipo,
            detalhes.distrito,
            detalhes.concelho
        ].filter(Boolean).join(' • ');
        
        badge.addEventListener('mouseenter', () => {
            badge.style.transform = 'scale(1.1)';
        });
        
        badge.addEventListener('mouseleave', () => {
            badge.style.transform = 'scale(1)';
        });
        
        return badge;
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
                🚀 betterE-Leiloes v12.0
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <button id="btn-scrape-all" style="${getButtonStyle('#10b981')}">
                    📥 Recolher Tudo (API)
                </button>
                <button id="btn-view-data" style="${getButtonStyle('#3b82f6')}">
                    👁️ Ver Dados
                </button>
                <button id="btn-stats" style="${getButtonStyle('#8b5cf6')}">
                    📊 Estatísticas
                </button>
                <button id="btn-clear-cache" style="${getButtonStyle('#ef4444')}">
                    🗑️ Limpar Base de Dados
                </button>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        // Event listeners
        document.getElementById('btn-scrape-all').addEventListener('click', handleScrapeAll);
        document.getElementById('btn-view-data').addEventListener('click', handleViewData);
        document.getElementById('btn-stats').addEventListener('click', handleViewStats);
        document.getElementById('btn-clear-cache').addEventListener('click', handleClearCache);
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

    async function handleScrapeAll() {
        const confirmed = confirm(
            '🚨 Isto vai iniciar a recolha de TODOS os eventos no servidor.\n\n' +
            'Pode demorar várias horas dependendo do número de eventos.\n\n' +
            'O processo corre em background no servidor.\n\n' +
            'Continuar?'
        );
        
        if (!confirmed) return;
        
        try {
            const btn = document.getElementById('btn-scrape-all');
            btn.disabled = true;
            btn.textContent = '⏳ A iniciar...';
            
            await triggerFullScrape();
            
            alert('✅ Scraping iniciado no servidor!\n\nUsa o botão "📊 Estatísticas" para ver o progresso.');
            
            // Inicia polling de status
            pollScrapeStatus();
            
        } catch (error) {
            alert(`❌ Erro ao iniciar scraping:\n${error.message}`);
            console.error(error);
        } finally {
            const btn = document.getElementById('btn-scrape-all');
            btn.disabled = false;
            btn.textContent = '📥 Recolher Tudo (API)';
        }
    }

    let pollInterval = null;

    async function pollScrapeStatus() {
        if (pollInterval) clearInterval(pollInterval);
        
        pollInterval = setInterval(async () => {
            try {
                const status = await getScrapeStatus();
                
                if (status.is_running) {
                    const btn = document.getElementById('btn-scrape-all');
                    btn.textContent = `⏳ ${status.events_processed} eventos`;
                } else {
                    clearInterval(pollInterval);
                    const btn = document.getElementById('btn-scrape-all');
                    btn.textContent = '📥 Recolher Tudo (API)';
                    
                    if (status.events_processed > 0) {
                        alert(`✅ Scraping concluído!\n\n${status.events_processed} eventos recolhidos\n${status.events_failed} falhas`);
                    }
                }
            } catch (error) {
                console.error('Erro ao verificar status:', error);
            }
        }, CONFIG.POLL_INTERVAL);
    }

    async function handleViewData() {
        try {
            const modal = createDataModal();
            document.body.appendChild(modal);
            
            await loadDataIntoModal(modal);
            
        } catch (error) {
            alert(`❌ Erro ao carregar dados:\n${error.message}`);
            console.error(error);
        }
    }

    async function handleViewStats() {
        try {
            const stats = await getAPIStats();
            const status = await getScrapeStatus();
            
            let message = `📊 ESTATÍSTICAS DO SERVIDOR\n\n`;
            message += `Total de eventos: ${stats.total_events}\n`;
            message += `Com GPS: ${stats.with_gps}\n`;
            message += `Sem GPS: ${stats.total_events - stats.with_gps}\n\n`;
            
            if (stats.by_type && Object.keys(stats.by_type).length > 0) {
                message += `Por tipo:\n`;
                Object.entries(stats.by_type).forEach(([tipo, count]) => {
                    message += `  • ${tipo}: ${count}\n`;
                });
            }
            
            message += `\n📡 STATUS DO SCRAPER\n\n`;
            message += `Estado: ${status.is_running ? '🟢 A correr' : '⚪ Parado'}\n`;
            
            if (status.is_running) {
                message += `Eventos processados: ${status.events_processed}\n`;
                message += `Falhas: ${status.events_failed}\n`;
                message += `Página atual: ${status.current_page || 'N/A'}\n`;
            }
            
            alert(message);
            
        } catch (error) {
            alert(`❌ Erro ao carregar estatísticas:\n${error.message}`);
            console.error(error);
        }
    }

    async function handleClearCache() {
        const confirmed1 = confirm(
            '⚠️ ATENÇÃO: Isto vai APAGAR TODOS os eventos da base de dados!\n\n' +
            'Esta operação é IRREVERSÍVEL!\n\n' +
            'Continuar?'
        );
        if (!confirmed1) return;
        
        const confirmed2 = confirm(
            '🚨 ÚLTIMA CONFIRMAÇÃO\n\n' +
            'Tens a CERTEZA que queres apagar TODOS os dados?\n\n' +
            'Vais perder TODOS os eventos recolhidos!'
        );
        if (!confirmed2) return;
        
        try {
            console.log('🗑️ Chamando clearDatabase()...');
            const result = await clearDatabase();
            console.log('✅ Resultado:', result);
            alert(`✅ Base de dados limpa com sucesso!\n\n${result.deleted_events} eventos apagados.`);
            
            // Recarrega a página para limpar o UI
            location.reload();
        } catch (error) {
            alert(`❌ Erro ao limpar base de dados:\n${error.message}`);
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
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        modal.innerHTML = `
            <div style="
                background: white;
                border-radius: 12px;
                width: 90%;
                max-width: 1200px;
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
                            <option value="imovel">🏠 Apenas Imóveis</option>
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
                            background: #10b981;
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
                            background: #6b7280;
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
        modal.querySelector('#close-modal').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        return modal;
    }

    let currentViewMode = 'list'; // 'list' ou 'grid'

    async function loadDataIntoModal(modal, page = 1, filters = {}) {
        const content = modal.querySelector('#modal-content');
        const subtitle = modal.querySelector('#modal-subtitle');
        const pageInfo = modal.querySelector('#page-info');
        const btnPrev = modal.querySelector('#btn-prev-page');
        const btnNext = modal.querySelector('#btn-next-page');
        const btnFilter = modal.querySelector('#btn-apply-filters');
        const btnViewList = modal.querySelector('#btn-view-list');
        const btnViewGrid = modal.querySelector('#btn-view-grid');
        
        try {
            const data = await listEventsFromAPI(page, 20, filters);
            
            subtitle.textContent = `${data.total} eventos encontrados`;
            pageInfo.textContent = `Página ${data.page} de ${data.pages}`;
            
            // Pagination buttons
            btnPrev.disabled = page <= 1;
            btnNext.disabled = page >= data.pages;
            
            btnPrev.onclick = () => loadDataIntoModal(modal, page - 1, filters);
            btnNext.onclick = () => loadDataIntoModal(modal, page + 1, filters);
            
            // Filter button
            btnFilter.onclick = () => {
                const tipoEvento = modal.querySelector('#filter-tipo-evento').value;
                const distrito = modal.querySelector('#filter-distrito').value.trim();
                
                const newFilters = {};
                if (distrito) newFilters.distrito = distrito;
                if (tipoEvento) newFilters.tipoEvento = tipoEvento;
                
                loadDataIntoModal(modal, 1, newFilters);
            };
            
            // View mode buttons
            btnViewList.onclick = () => {
                currentViewMode = 'list';
                btnViewList.style.background = '#10b981';
                btnViewGrid.style.background = '#6b7280';
                loadDataIntoModal(modal, page, filters);
            };
            
            btnViewGrid.onclick = () => {
                currentViewMode = 'grid';
                btnViewList.style.background = '#6b7280';
                btnViewGrid.style.background = '#10b981';
                loadDataIntoModal(modal, page, filters);
            };
            
            // Update button states
            if (currentViewMode === 'list') {
                btnViewList.style.background = '#10b981';
                btnViewGrid.style.background = '#6b7280';
            } else {
                btnViewList.style.background = '#6b7280';
                btnViewGrid.style.background = '#10b981';
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
                content.innerHTML = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;">
                        ${data.events.map(event => createEventCardCompact(event)).join('')}
                    </div>
                `;
            } else {
                content.innerHTML = data.events.map(event => createEventCard(event)).join('');
            }
            
        } catch (error) {
            content.innerHTML = `
                <div style="text-align: center; padding: 40px; color: #ef4444;">
                    <div style="font-size: 40px;">❌</div>
                    <p>Erro ao carregar dados</p>
                    <p style="font-size: 12px; margin-top: 10px;">${error.message}</p>
                </div>
            `;
        }
    }

    // Formata valores monetários
    const formatMoney = (value) => {
        if (!value) return 'N/A';
        return new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' }).format(value);
    };

    function createEventCard(event) {
        const detalhes = event.detalhes || {};
        const gps = event.gps || {};
        const valores = event.valores || {};
        const tipoEvento = event.tipoEvento || 'imovel';
        
        return `
            <div style="
                background: #f9fafb;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 10px;
                border: 1px solid #e5e7eb;
                border-left: 4px solid ${tipoEvento === 'imovel' ? '#3b82f6' : '#f59e0b'};
            ">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <strong style="font-size: 15px; color: #111827;">${event.reference}</strong>
                            <span style="
                                background: ${tipoEvento === 'imovel' ? '#dbeafe' : '#fef3c7'};
                                color: ${tipoEvento === 'imovel' ? '#1e40af' : '#92400e'};
                                padding: 2px 8px;
                                border-radius: 12px;
                                font-size: 10px;
                                font-weight: 600;
                                text-transform: uppercase;
                            ">${tipoEvento === 'imovel' ? '🏠 Imóvel' : '🚗 Móvel'}</span>
                        </div>
                        ${detalhes.tipo ? `<div style="font-size: 12px; color: #6b7280; margin-top: 4px;">${detalhes.tipo}</div>` : ''}
                    </div>
                    ${gps && gps.latitude ? `
                        <a href="https://www.google.com/maps?q=${gps.latitude},${gps.longitude}" target="_blank" style="
                            background: #3b82f6;
                            color: white;
                            padding: 6px 12px;
                            border-radius: 6px;
                            text-decoration: none;
                            font-size: 12px;
                            font-weight: 600;
                        ">📍 Ver no Mapa</a>
                    ` : ''}
                </div>
                
                <!-- Valores do Leilão -->
                <div style="
                    background: #fff;
                    border-radius: 6px;
                    padding: 10px;
                    margin-bottom: 10px;
                    border: 1px solid #e5e7eb;
                ">
                    <div style="font-weight: 600; font-size: 11px; color: #6b7280; margin-bottom: 6px; text-transform: uppercase;">💰 Valores do Leilão</div>
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px;">
                        <div><strong>Base:</strong> ${formatMoney(valores.valorBase)}</div>
                        <div><strong>Abertura:</strong> ${formatMoney(valores.valorAbertura)}</div>
                        <div><strong>Mínimo:</strong> ${formatMoney(valores.valorMinimo)}</div>
                        <div style="color: #059669; font-weight: 600;"><strong>Lance Atual:</strong> ${formatMoney(valores.lanceAtual)}</div>
                    </div>
                </div>
                
                <!-- Detalhes -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; font-size: 13px;">
                    ${detalhes.subtipo ? `<div><strong>Subtipo:</strong> ${detalhes.subtipo}</div>` : ''}
                    ${detalhes.matricula ? `<div><strong>Matrícula:</strong> ${detalhes.matricula}</div>` : ''}
                    ${detalhes.tipologia ? `<div><strong>Tipologia:</strong> ${detalhes.tipologia}</div>` : ''}
                    ${detalhes.areaPrivativa ? `<div><strong>Área Privativa:</strong> ${detalhes.areaPrivativa}m²</div>` : ''}
                    ${detalhes.areaDependente ? `<div><strong>Área Dependente:</strong> ${detalhes.areaDependente}m²</div>` : ''}
                    ${detalhes.areaTotal ? `<div><strong>Área Total:</strong> ${detalhes.areaTotal}m²</div>` : ''}
                    ${detalhes.distrito ? `<div><strong>Distrito:</strong> ${detalhes.distrito}</div>` : ''}
                    ${detalhes.concelho ? `<div><strong>Concelho:</strong> ${detalhes.concelho}</div>` : ''}
                    ${detalhes.freguesia ? `<div><strong>Freguesia:</strong> ${detalhes.freguesia}</div>` : ''}
                </div>
                
                ${gps && gps.latitude ? `
                    <div style="margin-top: 10px; font-size: 11px; color: #9ca3af;">
                        GPS: ${gps.latitude}, ${gps.longitude}
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
        
        const formatShort = (value) => {
            if (!value) return 'N/A';
            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M€`;
            if (value >= 1000) return `${(value / 1000).toFixed(0)}k€`;
            return `${value}€`;
        };
        
        return `
            <div style="
                background: #f9fafb;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #e5e7eb;
                border-top: 3px solid ${tipoEvento === 'imovel' ? '#3b82f6' : '#f59e0b'};
                font-size: 12px;
                display: flex;
                flex-direction: column;
                gap: 8px;
                transition: all 0.2s;
                cursor: pointer;
            " onmouseover="this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'" onmouseout="this.style.boxShadow='none'">
                <!-- Header -->
                <div>
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                        <span style="
                            background: ${tipoEvento === 'imovel' ? '#dbeafe' : '#fef3c7'};
                            color: ${tipoEvento === 'imovel' ? '#1e40af' : '#92400e'};
                            padding: 2px 6px;
                            border-radius: 10px;
                            font-size: 9px;
                            font-weight: 700;
                            text-transform: uppercase;
                        ">${tipoEvento === 'imovel' ? '🏠' : '🚗'}</span>
                        ${gps && gps.latitude ? `
                            <a href="https://www.google.com/maps?q=${gps.latitude},${gps.longitude}" target="_blank" 
                               onclick="event.stopPropagation()" style="
                                color: #3b82f6;
                                text-decoration: none;
                                font-size: 14px;
                            " title="Ver no Mapa">📍</a>
                        ` : ''}
                    </div>
                    <strong style="font-size: 13px; color: #111827; display: block;">${event.reference}</strong>
                    ${detalhes.tipo ? `<div style="font-size: 10px; color: #6b7280; margin-top: 2px;">${detalhes.tipo}</div>` : ''}
                </div>
                
                <!-- Valores -->
                <div style="
                    background: #fff;
                    border-radius: 4px;
                    padding: 8px;
                    border: 1px solid #e5e7eb;
                ">
                    ${valores.lanceAtual ? `
                        <div style="color: #059669; font-weight: 700; font-size: 14px;">💰 ${formatShort(valores.lanceAtual)}</div>
                        <div style="font-size: 10px; color: #6b7280; margin-top: 2px;">Lance Atual</div>
                    ` : valores.valorBase ? `
                        <div style="color: #3b82f6; font-weight: 700; font-size: 14px;">💵 ${formatShort(valores.valorBase)}</div>
                        <div style="font-size: 10px; color: #6b7280; margin-top: 2px;">Valor Base</div>
                    ` : '<div style="color: #9ca3af; font-size: 11px;">Sem valores</div>'}
                </div>
                
                <!-- Detalhes principais -->
                <div style="font-size: 11px; color: #4b5563; line-height: 1.4;">
                    ${tipoEvento === 'imovel' ? `
                        ${detalhes.tipologia ? `<div><strong>Tipologia:</strong> ${detalhes.tipologia}</div>` : ''}
                        ${detalhes.areaTotal ? `<div><strong>Área:</strong> ${detalhes.areaTotal}m²</div>` : ''}
                    ` : `
                        ${detalhes.subtipo ? `<div><strong>Tipo:</strong> ${detalhes.subtipo}</div>` : ''}
                        ${detalhes.matricula ? `<div><strong>Mat:</strong> ${detalhes.matricula}</div>` : ''}
                    `}
                    ${detalhes.distrito ? `<div><strong>📍</strong> ${detalhes.distrito}${detalhes.concelho ? ', ' + detalhes.concelho : ''}</div>` : ''}
                </div>
            </div>
        `;
    }

    // ====================================
    // INICIALIZAÇÃO
    // ====================================

    function init() {
        console.log('🚀 betterE-Leiloes v12.0 (API Version) iniciado!');
        
        // Cria painel de controlo
        createControlPanel();
        
        // Enriquece cards da página atual
        enrichCardsWithAPIData();
        
        // Observer para novas páginas (SPA)
        const observer = new MutationObserver(() => {
            enrichCardsWithAPIData();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('✅ Extensão pronta! API: ' + CONFIG.API_BASE_URL);
    }

    // Aguarda DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
