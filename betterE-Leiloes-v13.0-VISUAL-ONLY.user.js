// ==UserScript==
// @name         betterE-Leiloes (Visual Enhancement Only)
// @namespace    http://tampermonkey.net/
// @version      13.0
// @description  Reorganiza visualmente os cards nativos do e-leiloes.pt sem usar API
// @author       Nuno Mansilhas
// @match        https://www.e-leiloes.pt/*
// @icon         https://www.e-leiloes.pt/favicon.ico
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // ====================================
    // ESTILOS CSS
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
    `;
    document.head.appendChild(styles);

    // ====================================
    // FUNÇÕES DE ENHANCEMENT
    // ====================================

    function enhanceNativeCards() {
        const cards = document.querySelectorAll('.p-evento:not([data-enhanced])');
        
        cards.forEach(card => {
            card.dataset.enhanced = 'true';
            
            // Extrai dados do HTML existente
            const cardData = extractCardData(card);
            
            // Reorganiza visualmente
            reorganizeCard(card, cardData);
        });
    }

    function extractCardData(card) {
        const data = { valores: {} };
        
        // Extrai referência
        const refSpan = card.querySelector('.pi-tag + span');
        if (refSpan) data.reference = refSpan.textContent.trim();
        
        // Extrai valores do footer original
        const footer = card.querySelector('.p-evento-footer');
        if (footer) {
            const allText = footer.textContent;
            
            // Padrões: VB: 124 181,62 €
            const vbMatch = allText.match(/VB:\s*([0-9\s,\.]+\s*€)/);
            const vmMatch = allText.match(/VM:\s*([0-9\s,\.]+\s*€)/);
            const laMatch = allText.match(/LA:\s*([0-9\s,\.]+\s*€)/);
            const pmaMatch = allText.match(/PMA:\s*([0-9\s,\.]+\s*€)/);
            const vaMatch = allText.match(/VA:\s*([0-9\s,\.]+\s*€)/);
            
            if (vbMatch) data.valores.VB = vbMatch[1].trim();
            if (vmMatch) data.valores.VM = vmMatch[1].trim();
            if (laMatch) data.valores.LA = laMatch[1].trim();
            if (pmaMatch) data.valores.PMA = pmaMatch[1].trim();
            if (vaMatch) data.valores.VA = vaMatch[1].trim();
            
            // Extrai data final (segunda data mencionada)
            const dateMatches = allText.match(/(\d{2}\/\d{2}\/\d{4})/g);
            if (dateMatches && dateMatches.length >= 2) {
                data.dataFim = dateMatches[1]; // Segunda data é a data fim
            }
        }
        
        return data;
    }

    function reorganizeCard(card, data) {
        // 1. ADICIONAR BADGES no header
        const headerDiv = card.querySelector('.flex.w-full.flex-wrap.align-items-center.justify-content-between.px-3.pt-3.gap-1');
        if (headerDiv && !headerDiv.querySelector('.eleiloes-badge')) {
            const badgesContainer = document.createElement('div');
            badgesContainer.style.cssText = 'display: flex; gap: 4px; margin-left: auto;';
            
            // Badge de lances (se tem LA ou PMA)
            if (data.valores.LA || data.valores.PMA) {
                const lancesBadge = document.createElement('span');
                lancesBadge.className = 'eleiloes-badge success';
                lancesBadge.title = 'Tem lances ativos';
                lancesBadge.textContent = '✓';
                badgesContainer.appendChild(lancesBadge);
            }
            
            // Badge de desconto (se tem VB e VM)
            if (data.valores.VM && data.valores.VB) {
                try {
                    const vm = parseFloat(data.valores.VM.replace(/\s/g, '').replace(',', '.').replace('€', ''));
                    const vb = parseFloat(data.valores.VB.replace(/\s/g, '').replace(',', '.').replace('€', ''));
                    const desconto = ((vm - vb) / vm * 100).toFixed(1);
                    
                    if (parseFloat(desconto) > 0) {
                        const descontoBadge = document.createElement('span');
                        descontoBadge.className = 'eleiloes-badge info';
                        descontoBadge.title = `Desconto: -${desconto}% face ao VM`;
                        descontoBadge.textContent = '?';
                        badgesContainer.appendChild(descontoBadge);
                    }
                } catch (e) {
                    console.warn('Erro ao calcular desconto:', e);
                }
            }
            
            if (badgesContainer.children.length > 0) {
                headerDiv.appendChild(badgesContainer);
            }
        }
        
        // 2. REORGANIZAR FOOTER com valores inline
        const footer = card.querySelector('.p-evento-footer');
        if (footer && !footer.dataset.simplified) {
            footer.dataset.simplified = 'true';
            footer.innerHTML = '';
            footer.style.cssText = 'display: flex; align-items: center; justify-content: space-between; margin-top: 0.5rem; padding: 0.5rem 0.75rem; background: rgb(241, 245, 249); border-radius: 0 0 8px 8px;';
            
            // Container de valores inline
            const valuesContainer = document.createElement('div');
            valuesContainer.className = 'eleiloes-values-inline';
            
            const items = [];
            if (data.valores.VB) items.push({ label: 'VB', value: data.valores.VB });
            if (data.valores.VM) items.push({ label: 'VM', value: data.valores.VM });
            if (data.valores.PMA) items.push({ label: 'PMA', value: data.valores.PMA, highlight: true });
            else if (data.valores.LA) items.push({ label: 'LA', value: data.valores.LA, highlight: true });
            else if (data.valores.VA) items.push({ label: 'VA', value: data.valores.VA });
            
            items.forEach((item, idx) => {
                if (idx > 0) {
                    const separator = document.createElement('span');
                    separator.className = 'value-separator';
                    separator.textContent = '|';
                    valuesContainer.appendChild(separator);
                }
                
                const itemSpan = document.createElement('span');
                itemSpan.className = 'value-inline-item';
                
                const label = document.createElement('span');
                label.className = 'value-inline-label';
                label.textContent = item.label + ':';
                
                const amount = document.createElement('span');
                amount.className = 'value-inline-amount' + (item.highlight ? ' highlight' : '');
                amount.textContent = item.value;
                
                itemSpan.appendChild(label);
                itemSpan.appendChild(amount);
                valuesContainer.appendChild(itemSpan);
            });
            
            footer.appendChild(valuesContainer);
            
            // Data relativa
            if (data.dataFim) {
                const dateRelative = document.createElement('div');
                dateRelative.className = 'eleiloes-date-relative';
                dateRelative.title = `Data exata: ${data.dataFim}`;
                
                const relativeText = getRelativeDateFromString(data.dataFim);
                dateRelative.textContent = relativeText;
                
                if (relativeText.includes('hoje') || relativeText.includes('amanhã')) {
                    dateRelative.classList.add('urgent');
                }
                
                footer.appendChild(dateRelative);
            }
        }
    }

    function getRelativeDateFromString(dateString) {
        // Converte DD/MM/YYYY HH:MM:SS para Date
        const parts = dateString.split(/[\s\/:-]/);
        if (parts.length >= 3) {
            const day = parseInt(parts[0]);
            const month = parseInt(parts[1]) - 1;
            const year = parseInt(parts[2]);
            const endDate = new Date(year, month, day);
            
            const now = new Date();
            now.setHours(0, 0, 0, 0);
            endDate.setHours(0, 0, 0, 0);
            
            const diffTime = endDate - now;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays < 0) return 'Terminado';
            if (diffDays === 0) return 'Termina hoje';
            if (diffDays === 1) return 'Termina amanhã';
            if (diffDays <= 7) return `Termina em ${diffDays} dias`;
            if (diffDays <= 30) return `Termina em ${Math.ceil(diffDays / 7)} semanas`;
            return `Termina em ${Math.ceil(diffDays / 30)} meses`;
        }
        
        return dateString;
    }

    // ====================================
    // INICIALIZAÇÃO E OBSERVAÇÃO
    // ====================================

    function init() {
        console.log('🎨 betterE-Leiloes v13.0 (Visual Only) iniciado!');
        
        // Processa cards existentes
        enhanceNativeCards();
        
        // Observa novos cards (paginação, filtros)
        const observer = new MutationObserver((mutations) => {
            enhanceNativeCards();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Aguarda página carregar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
