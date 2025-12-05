// ==UserScript==
// @name         betterE-Leiloes v11.1
// @namespace    http://tampermonkey.net/
// @version      11.1
// @description  Cards modernos com recolha automática optimizada
// @author       Nuno
// @match        https://www.e-leiloes.pt/*
// @match        https://e-leiloes.pt/*
// @grant        GM_addStyle
// ==/UserScript==

(function() {
    'use strict';

    // 🔒 Proteção contra múltiplas execuções
    if (window.betterEleiloesLoaded) {
        console.log('⚠️ betterE-Leiloes já está ativo, ignorando re-injeção');
        return;
    }
    window.betterEleiloesLoaded = true;

    console.log('🚗 betterE-Leiloes v11.1 INICIADO!');

    GM_addStyle(`
        /* Cards com design moderno e limpo */
        .p-evento {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            cursor: pointer !important;
        }

        .p-evento:hover {
            transform: translateY(-8px) !important;
        }

        .p-evento > div {
            border: 2px solid #e5e7eb !important;
            transition: all 0.3s ease !important;
            background: white !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
        }

        .p-evento:hover > div {
            border-color: #3b82f6 !important;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 
                        0 10px 10px -5px rgba(0, 0, 0, 0.04),
                        0 0 0 3px rgba(59, 130, 246, 0.1) !important;
        }

        /* Imagem com zoom suave */
        .p-evento-image {
            transition: transform 0.4s ease !important;
            overflow: hidden !important;
        }

        .p-evento:hover .p-evento-image {
            transform: scale(1.05) !important;
        }

        /* Footer redesenhado - valores inline */
        .p-evento-footer {
            display: flex !important;
            flex-direction: column !important;
            gap: 10px !important;
            padding: 14px !important;
            background: linear-gradient(to bottom, #fafafa, #ffffff) !important;
            border-top: 1px solid #f0f0f0 !important;
        }

        /* Valores inline no formato: VB: X € | VM: X € | PMA: X € */
        .eleiloes-values-inline {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: white;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 11.5px;
            border: 1px solid #e5e7eb;
            width: 100%;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }

        .value-inline-item {
            display: inline;
            white-space: nowrap;
        }

        .value-inline-label {
            font-weight: 700;
            color: #6b7280;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.5px;
        }

        .value-inline-amount {
            font-weight: 800;
            color: #1f2937;
            margin-left: 4px;
            font-size: 11.5px;
        }

        .value-inline-amount.highlight {
            color: #ef4444;
            font-weight: 900;
        }

        .value-separator {
            color: #d1d5db;
            margin: 0 10px;
            font-weight: 300;
        }

        /* Data relativa com tooltip */
        .eleiloes-date-relative {
            text-align: center;
            padding: 10px 12px;
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-radius: 8px;
            font-size: 11.5px;
            font-weight: 700;
            color: #92400e;
            position: relative;
            cursor: help;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            transition: all 0.2s ease;
        }

        .eleiloes-date-relative:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .eleiloes-date-relative.urgent {
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            color: #991b1b;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.9; }
        }

        .eleiloes-date-relative:hover::after {
            content: attr(data-exact-date);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.95);
            color: white;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 10px;
            white-space: nowrap;
            margin-bottom: 8px;
            z-index: 100;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }

        .eleiloes-date-relative:hover::before {
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 6px solid transparent;
            border-top-color: rgba(0, 0, 0, 0.95);
            margin-bottom: 2px;
        }

        /* Ícone Google Maps */
        .eleiloes-map-icon {
            color: #3b82f6 !important;
            cursor: pointer !important;
            font-size: 14px !important;
            margin-left: 6px !important;
            transition: all 0.2s ease !important;
            display: inline-flex !important;
            align-items: center !important;
        }

        .eleiloes-map-icon:hover {
            color: #2563eb !important;
            transform: scale(1.3) !important;
        }

        /* Badges redondas com tooltip */
        .eleiloes-badge {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
            cursor: help;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            position: relative;
            margin-left: 6px;
        }

        .eleiloes-badge:hover {
            transform: scale(1.15);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }

        .eleiloes-badge.success {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
        }

        .eleiloes-badge.danger {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
        }

        .eleiloes-badge.info {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
        }

        /* Tooltip das badges */
        .eleiloes-badge::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%) scale(0);
            background: rgba(0, 0, 0, 0.95);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11px;
            white-space: nowrap;
            pointer-events: none;
            opacity: 0;
            transition: all 0.2s ease;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .eleiloes-badge::before {
            content: '';
            position: absolute;
            bottom: calc(100% + 2px);
            left: 50%;
            transform: translateX(-50%) scale(0);
            border: 6px solid transparent;
            border-top-color: rgba(0, 0, 0, 0.95);
            pointer-events: none;
            opacity: 0;
            transition: all 0.2s ease;
        }

        .eleiloes-badge:hover::after {
            transform: translateX(-50%) scale(1);
            opacity: 1;
        }

        .eleiloes-badge:hover::before {
            transform: translateX(-50%) scale(1);
            opacity: 1;
        }

        /* Header do card (referência + tipo) */
        .p-evento > div > div:first-child {
            background: linear-gradient(to right, #f8fafc, #f1f5f9) !important;
            border-bottom: 1px solid #e5e7eb !important;
            padding: 12px 14px !important;
        }

        /* Tipo de imóvel e localização */
        .p-evento .flex.align-items-center.justify-content-between.px-3.pt-1 {
            padding: 10px 14px 6px 14px !important;
            background: #fafafa !important;
            border-radius: 6px !important;
            margin: 8px 12px 0 12px !important;
        }

        /* Descrição do imóvel */
        .p-evento .flex.align-items-start.px-3.pt-1 {
            padding: 10px 14px !important;
            margin: 0 12px !important;
        }

        .p-evento .flex.align-items-start.px-3.pt-1 .text-sm {
            line-height: 1.6 !important;
            color: #374151 !important;
        }

        /* Container da imagem */
        .p-evento .flex.px-3.pt-2 {
            padding: 12px 14px !important;
        }

        /* Melhorias visuais globais */
        .p-evento .text-sm {
            line-height: 1.5 !important;
        }

        .p-evento .p-tag {
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
        }

        .p-evento .pi-building,
        .p-evento .pi-map-marker {
            color: #6b7280 !important;
        }

        /* Botões de ação */
        .eleiloes-clear-cache-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            border: none;
            border-radius: 50%;
            width: 56px;
            height: 56px;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
            transition: all 0.3s ease;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .eleiloes-clear-cache-btn:hover {
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.6);
        }

        .eleiloes-clear-cache-btn:active {
            transform: translateY(0) scale(0.98);
        }

        .eleiloes-clear-cache-btn::after {
            content: 'Limpar Cache';
            position: absolute;
            right: calc(100% + 10px);
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s ease;
        }

        .eleiloes-clear-cache-btn:hover::after {
            opacity: 1;
        }

        /* Botão Ver Dados */
        .eleiloes-view-data-btn {
            position: fixed;
            bottom: 20px;
            right: 86px;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            border: none;
            border-radius: 50%;
            width: 56px;
            height: 56px;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
            transition: all 0.3s ease;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .eleiloes-view-data-btn:hover {
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);
        }

        .eleiloes-view-data-btn:active {
            transform: translateY(0) scale(0.98);
        }

        .eleiloes-view-data-btn::after {
            content: 'Ver Dados';
            position: absolute;
            right: calc(100% + 10px);
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s ease;
        }

        .eleiloes-view-data-btn:hover::after {
            opacity: 1;
        }

        /* Botão Recolher Tudo */
        .eleiloes-collect-all-btn {
            position: fixed;
            bottom: 20px;
            right: 152px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            border: none;
            border-radius: 50%;
            width: 56px;
            height: 56px;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
            transition: all 0.3s ease;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .eleiloes-collect-all-btn:hover {
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.6);
        }

        .eleiloes-collect-all-btn:active {
            transform: translateY(0) scale(0.98);
        }

        .eleiloes-collect-all-btn.loading {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            animation: pulse 1.5s infinite;
        }

        .eleiloes-collect-all-btn::after {
            content: 'Recolher Tudo';
            position: absolute;
            right: calc(100% + 10px);
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s ease;
        }

        .eleiloes-collect-all-btn:hover::after {
            opacity: 1;
        }

        .eleiloes-collect-all-btn.loading::after {
            content: 'A recolher...';
        }

        /* Modal */
        .eleiloes-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .eleiloes-modal {
            background: white;
            border-radius: 12px;
            width: 95%;
            max-width: 1400px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: slideUp 0.3s ease;
        }

        @keyframes slideUp {
            from { transform: translateY(50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .eleiloes-modal-header {
            padding: 24px 28px;
            border-bottom: 2px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(to right, #f8fafc, #f1f5f9);
            border-radius: 12px 12px 0 0;
        }

        .eleiloes-modal-title {
            font-size: 24px;
            font-weight: 800;
            color: #1f2937;
            margin: 0;
        }

        .eleiloes-modal-subtitle {
            font-size: 14px;
            color: #6b7280;
            margin: 4px 0 0 0;
        }

        .eleiloes-modal-close {
            background: #ef4444;
            color: white;
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .eleiloes-modal-close:hover {
            background: #dc2626;
            transform: scale(1.1);
        }

        .eleiloes-modal-body {
            padding: 20px 28px;
            overflow-y: auto;
            flex: 1;
        }

        .eleiloes-data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        .eleiloes-data-table thead {
            position: sticky;
            top: 0;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            z-index: 10;
        }

        .eleiloes-data-table th {
            padding: 12px 10px;
            text-align: left;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #1e40af;
        }

        .eleiloes-data-table td {
            padding: 12px 10px;
            border-bottom: 1px solid #e5e7eb;
        }

        .eleiloes-data-table tbody tr {
            transition: background 0.2s ease;
        }

        .eleiloes-data-table tbody tr:hover {
            background: #f0f9ff;
        }

        .eleiloes-data-table tbody tr:nth-child(even) {
            background: #fafafa;
        }

        .eleiloes-data-table tbody tr:nth-child(even):hover {
            background: #f0f9ff;
        }

        .eleiloes-table-ref {
            font-weight: 700;
            color: #2563eb;
        }

        .eleiloes-table-gps {
            font-family: 'Courier New', monospace;
            font-size: 11px;
            color: #059669;
        }

        .eleiloes-table-area {
            text-align: right;
            font-weight: 600;
        }

        .eleiloes-empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #9ca3af;
        }

        .eleiloes-empty-state-icon {
            font-size: 64px;
            margin-bottom: 16px;
        }

        .eleiloes-empty-state-text {
            font-size: 18px;
            font-weight: 600;
        }

        /* Overlay de progresso */
        .eleiloes-progress-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(8px);
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease;
        }

        .eleiloes-progress-modal {
            background: white;
            border-radius: 16px;
            padding: 32px;
            width: 90%;
            max-width: 600px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            animation: slideUp 0.3s ease;
        }

        .eleiloes-progress-header {
            text-align: center;
            margin-bottom: 24px;
        }

        .eleiloes-progress-title {
            font-size: 28px;a
            font-weight: 800;
            color: #1f2937;
            margin: 0 0 8px 0;
        }

        .eleiloes-progress-subtitle {
            font-size: 14px;
            color: #6b7280;
            margin: 0;
        }

        .eleiloes-progress-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .eleiloes-stat-card {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            border: 2px solid #bae6fd;
        }

        .eleiloes-stat-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #0369a1;
            margin-bottom: 8px;
        }

        .eleiloes-stat-value {
            font-size: 32px;
            font-weight: 900;
            color: #0c4a6e;
            line-height: 1;
        }

        .eleiloes-stat-value.highlight {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .eleiloes-progress-bar-container {
            background: #e5e7eb;
            border-radius: 12px;
            height: 32px;
            overflow: hidden;
            margin-bottom: 16px;
            position: relative;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .eleiloes-progress-bar {
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            height: 100%;
            transition: width 0.5s ease;
            position: relative;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
        }

        .eleiloes-progress-bar::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            animation: shimmer 2s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        .eleiloes-progress-text {
            text-align: center;
            font-size: 18px;
            font-weight: 700;
            color: #374151;
            margin-bottom: 16px;
        }

        .eleiloes-progress-status {
            text-align: center;
            font-size: 14px;
            color: #6b7280;
            min-height: 20px;
            font-style: italic;
        }

        .eleiloes-progress-time {
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
        }

        .eleiloes-time-item {
            text-align: center;
        }

        .eleiloes-time-label {
            font-size: 11px;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        .eleiloes-time-value {
            font-size: 20px;
            font-weight: 700;
            color: #1f2937;
            font-family: 'Courier New', monospace;
        }

        .eleiloes-progress-spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 3px solid #e5e7eb;
            border-top-color: #10b981;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-left: 8px;
            vertical-align: middle;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    `);

    // Função para extrair dados reais dos cards ANTES de qualquer modificação
    function extractCardData(card) {
        try {
            // IMPORTANTE: Extrai TUDO antes de modificar o DOM
            const footer = card.querySelector('.p-evento-footer');
            if (!footer) {
                console.warn('⚠️ Footer não encontrado no card');
                return null;
            }

            // Clona o footer original para garantir que temos os dados originais
            const footerClone = footer.cloneNode(true);
            const footerText = footerClone.innerText || footerClone.textContent || '';

            // Extrai referência
            const refElement = card.querySelector('.pi-tag + span');
            const reference = refElement ? refElement.textContent.trim() : '';

            // A estrutura tem 2 colunas: labels na esquerda, valores na direita
            // Procura pelos containers flex que têm as labels e valores
            const flexContainers = footerClone.querySelectorAll('.flex.gap-1');
            
            let vb = '0,00', vm = '0,00', pma = '0,00', labelLance = 'PMA', endDate = '';
            
            // Primeiro container tem VB, VM, PMA/LA
            if (flexContainers[0]) {
                const leftColumn = flexContainers[0].querySelector('.flex-column.align-items-end');
                const rightColumn = flexContainers[0].querySelectorAll('.flex-column')[1];
                
                if (leftColumn && rightColumn) {
                    const labels = Array.from(leftColumn.querySelectorAll('.text-xs'));
                    const values = Array.from(rightColumn.querySelectorAll('.text-xs'));
                    
                    // Mapeia labels aos valores (mesma posição no array)
                    labels.forEach((label, index) => {
                        const labelText = label.textContent.trim();
                        const value = values[index] ? values[index].textContent.replace('€', '').trim() : '0,00';
                        
                        if (labelText === 'VB:') {
                            vb = value;
                        } else if (labelText === 'VM:') {
                            vm = value;
                        } else if (labelText === 'PMA:' || labelText === 'LA:') {
                            labelLance = labelText.replace(':', '');
                            pma = value;
                        }
                    });
                }
            }
            
            // Segundo container tem datas (de: / a:)
            if (flexContainers[1]) {
                const rightColumn = flexContainers[1].querySelectorAll('.flex-column')[1];
                if (rightColumn) {
                    const dateSpans = Array.from(rightColumn.querySelectorAll('.text-xs'));
                    // A segunda data (índice 1) é a data de fim
                    if (dateSpans[1]) {
                        const dateText = dateSpans[1].textContent.trim();
                        const dateMatch = dateText.match(/(\d{2}\/\d{2}\/\d{4})/);
                        if (dateMatch) {
                            endDate = dateMatch[1];
                        }
                    }
                }
            }
            
            const pmaNumeric = parseFloat(pma.replace(/\s/g, '').replace(/\./g, '').replace(',', '.'));
            const hasLance = pmaNumeric > 0;

            // Extrai localização
            const locationElement = card.querySelector('.pi-map-marker + span');
            const location = locationElement ? locationElement.textContent.trim() : '';

            const extractedData = {
                reference,
                vb,
                vm,
                pma,
                labelLance,
                hasLance,
                endDate,
                location,
                footerOriginalText: footerText
            };

            return extractedData;
        } catch (e) {
            console.error('❌ Erro ao extrair dados do card:', e);
            return null;
        }
    }

    function getRelativeTime(endDateStr) {
        try {
            const parts = endDateStr.match(/(\d{2})\/(\d{2})\/(\d{4})/);
            if (!parts) return null;

            const endDate = new Date(parts[3], parts[2] - 1, parts[1]);
            const now = new Date();
            const diff = endDate - now;

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const months = Math.floor(days / 30);
            const remainingDays = days % 30;

            let text = '';
            if (months > 0) {
                text = `Daqui a ${months}m e ${remainingDays}d`;
            } else if (days > 0) {
                text = `Daqui a ${days} dia${days !== 1 ? 's' : ''}`;
            } else {
                text = 'Termina hoje';
            }

            return {
                text,
                urgent: days <= 2,
                exactDate: endDateStr
            };
        } catch (e) {
            return null;
        }
    }

    function addBadges(card, extractedData) {
        const headerDiv = card.querySelector('.flex.w-full.flex-wrap.align-items-center.justify-content-between');
        if (!headerDiv || headerDiv.querySelector('.eleiloes-badge')) return;

        const { hasLance, pma, vm } = extractedData;
        
        // Badge 1: Verde se tem lance, vermelho se não tem
        const badge1 = document.createElement('span');
        badge1.className = `eleiloes-badge ${hasLance ? 'success' : 'danger'}`;
        badge1.innerHTML = hasLance ? '✓' : '✗';
        badge1.setAttribute('data-tooltip', hasLance ? 'Tem lances ativos' : 'Sem lances');
        
        // Badge 2: Info (ponto de interrogação)
        const badge2 = document.createElement('span');
        badge2.className = 'eleiloes-badge info';
        badge2.innerHTML = '?';
        
        // Calcula desconto ou diferença entre PMA e VM
        const pmaValue = parseFloat(pma.replace(/\s/g, '').replace(/\./g, '').replace(',', '.'));
        const vmValue = parseFloat(vm.replace(/\s/g, '').replace(/\./g, '').replace(',', '.'));
        const discount = vmValue > 0 ? ((vmValue - pmaValue) / vmValue * 100).toFixed(1) : 0;
        
        badge2.setAttribute('data-tooltip', `Desconto: ${discount}% face ao VM`);
        
        // Container para as badges
        const badgesContainer = document.createElement('div');
        badgesContainer.style.display = 'flex';
        badgesContainer.style.gap = '4px';
        badgesContainer.style.marginLeft = 'auto';
        badgesContainer.appendChild(badge1);
        badgesContainer.appendChild(badge2);
        
        headerDiv.appendChild(badgesContainer);
    }

    function simplifyFooter(card, extractedData) {
        const footer = card.querySelector('.p-evento-footer');
        if (!footer || footer.getAttribute('data-simplified')) return;
        
        // Se não foram passados dados extraídos, retorna
        if (!extractedData) {
            console.warn('⚠️ Dados não fornecidos para simplifyFooter');
            return;
        }

        footer.setAttribute('data-simplified', 'true');
        
        const { vb, vm, pma, labelLance, hasLance, endDate } = extractedData;
        
        const relativeTime = endDate ? getRelativeTime(endDate) : null;

        footer.innerHTML = '';

        // Valores inline no formato: VB: 124 181,62 € | VM: 105 554,38 € | PMA: 65 500,00 €
        const valuesDiv = document.createElement('div');
        valuesDiv.className = 'eleiloes-values-inline';
        valuesDiv.innerHTML = `
            <span class="value-inline-item">
                <span class="value-inline-label">VB:</span>
                <span class="value-inline-amount">${vb} €</span>
            </span>
            <span class="value-separator">|</span>
            <span class="value-inline-item">
                <span class="value-inline-label">VM:</span>
                <span class="value-inline-amount">${vm} €</span>
            </span>
            <span class="value-separator">|</span>
            <span class="value-inline-item">
                <span class="value-inline-label">${labelLance}:</span>
                <span class="value-inline-amount ${hasLance ? 'highlight' : ''}">${pma} €</span>
            </span>
        `;

        if (relativeTime) {
            const dateDiv = document.createElement('div');
            dateDiv.className = `eleiloes-date-relative ${relativeTime.urgent ? 'urgent' : ''}`;
            dateDiv.textContent = relativeTime.text;
            dateDiv.setAttribute('data-exact-date', relativeTime.exactDate);
            
            footer.appendChild(valuesDiv);
            footer.appendChild(dateDiv);
        } else {
            footer.appendChild(valuesDiv);
        }
    }

    async function addMapsLink(card) {
        const locationSpan = card.querySelector('.pi-map-marker + span');
        if (!locationSpan || locationSpan.querySelector('.eleiloes-map-icon')) return;

        const location = locationSpan.textContent.trim();
        const refElement = card.querySelector('.pi-tag + span');
        const reference = refElement ? refElement.textContent.trim() : '';
        
        const icon = document.createElement('i');
        icon.className = 'pi pi-map eleiloes-map-icon';
        icon.title = 'Ver no Google Maps';
        
        icon.addEventListener('click', async (e) => {
            e.stopPropagation();
            
            const forceUpdate = e.ctrlKey || e.metaKey; // Ctrl+Click força atualização
            
            // 🔍 Verifica cache primeiro
            const cached = getCachedData(reference);
            if (cached && cached.gps && cached.gps.latitude && !forceUpdate) {
                console.log(`📦 GPS do cache: ${cached.gps.latitude}, ${cached.gps.longitude}`);
                window.open(`https://www.google.com/maps?q=${cached.gps.latitude},${cached.gps.longitude}`, '_blank');
                return;
            }
            
            // Muda o ícone para loading
            const originalClass = icon.className;
            icon.className = 'pi pi-spin pi-spinner eleiloes-map-icon';
            icon.style.color = '#f59e0b';
            
            try {
                // Busca dados completos e atualiza cache
                const details = await extractEventDetails(reference);
                
                // Atualiza ou adiciona ao cache
                const existingIndex = window.eleiloesDetalhes.findIndex(d => d.reference === reference);
                if (existingIndex >= 0) {
                    window.eleiloesDetalhes[existingIndex] = details;
                } else {
                    window.eleiloesDetalhes.push(details);
                }
                saveCache();
                
                // Restaura o ícone
                icon.className = originalClass;
                icon.style.color = '';
                
                if (details.gps && details.gps.latitude) {
                    console.log(`✅ GPS: ${details.gps.latitude}, ${details.gps.longitude}`);
                    window.open(`https://www.google.com/maps?q=${details.gps.latitude},${details.gps.longitude}`, '_blank');
                } else {
                    window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(location)}`, '_blank');
                }
                
            } catch (error) {
                console.error('❌ Erro:', error);
                icon.className = originalClass;
                icon.style.color = '';
                window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(location)}`, '_blank');
            }
        });
        
        icon.addEventListener('mousedown', (e) => e.stopPropagation());
        
        locationSpan.parentNode.appendChild(icon);
    }

    function makeCardClickable(card) {
        const refSpan = card.querySelector('.pi-tag + span');
        if (!refSpan) return;
        
        // Mantém a referência completa (NP ou LO são parte do ID)
        const reference = refSpan.textContent.trim();

        const openLink = (e, forceNewTab = false) => {
            if (e.target.classList.contains('eleiloes-map-icon') || 
                e.target.closest('.eleiloes-map-icon') ||
                e.target.classList.contains('p-tag') ||
                e.target.closest('.p-tag')) {
                return;
            }
            
            e.preventDefault();
            const url = `https://www.e-leiloes.pt/evento/${reference}`;
            
            if (e.button === 1 || e.ctrlKey || e.metaKey || forceNewTab) {
                window.open(url, '_blank');
            } else {
                window.location.href = url;
            }
        };

        card.addEventListener('click', (e) => openLink(e, false));
        card.addEventListener('mousedown', (e) => {
            if (e.button === 1) {
                e.preventDefault();
                openLink(e, true);
            }
        });
        card.addEventListener('auxclick', (e) => {
            if (e.button === 1) {
                e.preventDefault();
                openLink(e, true);
            }
        });
    }

    function enhanceCard(card) {
        if (card.getAttribute('data-enhanced')) return;
        
        try {
            const extractedData = extractCardData(card);
            
            if (!extractedData) {
                console.error('❌ Falha ao extrair dados do card');
                return;
            }

            // Marca o card como "em processamento" para evitar reprocessamento
            card.setAttribute('data-enhanced', 'true');

            // Adiciona funcionalidades
            addMapsLink(card);
            addBadges(card, extractedData);
            makeCardClickable(card);
            simplifyFooter(card, extractedData);
        } catch (e) {
            console.error('❌ Erro ao melhorar card:', e);
            // Remove a marca de "enhanced" para tentar novamente
            card.removeAttribute('data-enhanced');
        }
    }

    function enhanceAllCards() {
        const cards = document.querySelectorAll('.p-evento:not([data-enhanced])');
        if (cards.length > 0) {
            cards.forEach(enhanceCard);
        }
    }

    // Array global para armazenar detalhes (GPS + Info)
    window.eleiloesDetalhes = [];

    // 💾 Sistema de cache com localStorage
    const STORAGE_KEY = 'eleiloes_detalhes_cache';
    
    function loadCache() {
        try {
            const cached = localStorage.getItem(STORAGE_KEY);
            if (cached) {
                const data = JSON.parse(cached);
                window.eleiloesDetalhes = data;
                console.log(`📦 Cache carregado: ${data.length} eventos`);
                return data;
            }
        } catch (e) {
            console.warn('⚠️ Erro ao carregar cache:', e);
        }
        return [];
    }
    
    function saveCache() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(window.eleiloesDetalhes));
            console.log(`💾 Cache guardado: ${window.eleiloesDetalhes.length} eventos`);
        } catch (e) {
            console.warn('⚠️ Erro ao guardar cache:', e);
        }
    }
    
    function isInCache(reference) {
        return window.eleiloesDetalhes.some(d => d.reference === reference);
    }
    
    function getCachedData(reference) {
        return window.eleiloesDetalhes.find(d => d.reference === reference);
    }

    // 🗑️ REMOVIDO: fetchEventDetails, collectAllEventData, showGPSCoordinates
    // Agora usamos apenas extractEventDetails + collectAllDetails

    // Função optimizada para extrair GPS + Detalhes via iframe
    async function extractEventDetails(reference) {
        return new Promise((resolve, reject) => {
            const url = `https://www.e-leiloes.pt/evento/${reference}`;
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            document.body.appendChild(iframe);
            
            let cleaned = false;
            const cleanup = () => {
                if (!cleaned && document.body.contains(iframe)) {
                    cleaned = true;
                    document.body.removeChild(iframe);
                }
            };
            
            const timeout = setTimeout(() => {
                cleanup();
                reject(new Error('Timeout'));
            }, 3000);
            
            iframe.onload = () => {
                setTimeout(() => {
                    try {
                        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                        
                        // 🔍 Extrai GPS (texto simples funciona)
                        const bodyText = iframeDoc.body.innerText || iframeDoc.body.textContent;
                        const latMatch = bodyText.match(/GPS\s*Latitude[:\s]*(-?\d+\.?\d+)/i);
                        const lonMatch = bodyText.match(/GPS\s*Longitude[:\s]*(-?\d+\.?\d+)/i);
                        
                        // 🎯 Extrai Detalhes via DOM (estrutura HTML específica)
                        const extractDetail = (label) => {
                            // Procura por <span class="font-semibold">Label:</span>
                            const allSpans = Array.from(iframeDoc.querySelectorAll('.flex.w-full .font-semibold'));
                            for (const span of allSpans) {
                                if (span.textContent.trim() === label) {
                                    // O valor está na próxima <span> no MESMO nível (nextElementSibling)
                                    let valueSpan = span.nextElementSibling;
                                    
                                    // Se não encontrou, tenta no parent.nextElementSibling
                                    if (!valueSpan || valueSpan.classList.contains('font-semibold')) {
                                        const parentWrapper = span.parentElement;
                                        if (parentWrapper && parentWrapper.nextElementSibling) {
                                            valueSpan = parentWrapper.nextElementSibling.querySelector('span:not(.font-semibold)');
                                        }
                                    }
                                    
                                    if (valueSpan && !valueSpan.classList.contains('font-semibold')) {
                                        // Pega APENAS o texto direto, não de sub-elementos
                                        const text = valueSpan.childNodes[0]?.textContent?.trim() || valueSpan.textContent.trim();
                                        return text;
                                    }
                                }
                            }
                            return 'N/A';
                        };
                        
                        const extractArea = (label) => {
                            const allSpans = Array.from(iframeDoc.querySelectorAll('.flex.w-full .font-semibold'));
                            for (const span of allSpans) {
                                if (span.textContent.trim() === label) {
                                    // Procura pelo <span class="mr-1">NÚMERO</span>
                                    const wrapper = span.closest('.flex.w-full');
                                    if (wrapper) {
                                        const numberSpan = wrapper.querySelector('span.mr-1');
                                        if (numberSpan) {
                                            // Retorna apenas o número (sem "m²")
                                            return numberSpan.textContent.trim();
                                        }
                                    }
                                }
                            }
                            return null;
                        };
                        
                        clearTimeout(timeout);
                        cleanup();
                        
                        resolve({
                            reference,
                            gps: {
                                latitude: latMatch ? latMatch[1] : null,
                                longitude: lonMatch ? lonMatch[1] : null
                            },
                            detalhes: {
                                tipo: extractDetail('Tipo:'),
                                subtipo: extractDetail('Subtipo:'),
                                tipologia: extractDetail('Tipologia:'),
                                areaPrivativa: extractArea('Área Privativa:'),
                                areaDependente: extractArea('Área Dependente:'),
                                areaTotal: extractArea('Área Total:')
                            }
                        });
                    } catch (err) {
                        clearTimeout(timeout);
                        cleanup();
                        reject(err);
                    }
                }, 800);
            };
            
            iframe.onerror = () => {
                clearTimeout(timeout);
                cleanup();
                reject(new Error('Erro ao carregar'));
            };
            
            iframe.src = url;
        });
    }

    // 🔥 Função ÚNICA para recolher GPS + Detalhes automaticamente (OPTIMIZADA)
    async function collectAllDetails(forceAll = false, progressCallback = null) {
        // Evita recolha duplicada se já estiver a correr
        if (window.eleiloesCollecting) {
            console.log('⚠️ Recolha já em progresso, aguarde...');
            return window.eleiloesDetalhes;
        }
        
        window.eleiloesCollecting = true;
        
        const cards = document.querySelectorAll('.p-evento');
        if (cards.length === 0) {
            console.log('⚠️ Nenhum card encontrado');
            window.eleiloesCollecting = false;
            return [];
        }
        
        // Filtra apenas cards sem cache (exceto se forceAll = true)
        const cardsToProcess = [];
        cards.forEach(card => {
            const refElement = card.querySelector('.pi-tag + span');
            if (refElement) {
                const reference = refElement.textContent.trim();
                if (forceAll || !isInCache(reference)) {
                    cardsToProcess.push({ card, reference });
                }
            }
        });
        
        if (cardsToProcess.length === 0) {
            console.log('✅ Todos os cards já estão em cache');
            window.eleiloesCollecting = false;
            return window.eleiloesDetalhes;
        }
        
        console.log(`🤖 Recolha automática: ${cardsToProcess.length}/${cards.length} novos`);
        let processed = 0;
        
        // � OPTIMIZAÇÃO: Processa 4 de cada vez (era 2, agora mais rápido)
        const batchSize = 4;
        for (let i = 0; i < cardsToProcess.length; i += batchSize) {
            const batch = cardsToProcess.slice(i, i + batchSize);
            
            const promises = batch.map(async ({ card, reference }) => {
                try {
                    const details = await extractEventDetails(reference);
                    
                    // Atualiza ou adiciona ao cache
                    const existingIndex = window.eleiloesDetalhes.findIndex(d => d.reference === reference);
                    if (existingIndex >= 0) {
                        window.eleiloesDetalhes[existingIndex] = details;
                    } else {
                        window.eleiloesDetalhes.push(details);
                    }
                    
                    processed++;
                    
                    // 🚀 NOVO: Callback para atualizar progresso em tempo real
                    if (progressCallback) {
                        progressCallback(processed, cardsToProcess.length);
                    }
                    
                    // Log progress apenas a cada 25%
                    if (processed % Math.ceil(cardsToProcess.length / 4) === 0 || processed === cardsToProcess.length) {
                        console.log(`📊 ${processed}/${cardsToProcess.length} (${Math.round(processed/cardsToProcess.length*100)}%)`);
                    }
                    return details;
                } catch (error) {
                    console.warn(`⚠️ ${reference}: ${error.message}`);
                    processed++;
                    if (progressCallback) {
                        progressCallback(processed, cardsToProcess.length);
                    }
                    return null;
                }
            });
            
            await Promise.all(promises);
            
            // � OPTIMIZAÇÃO: Delay reduzido para 200ms (era 500ms)
            if (i + batchSize < cardsToProcess.length) {
                await new Promise(resolve => setTimeout(resolve, 200));
            }
        }
        
        // Salva no localStorage
        saveCache();
        
        window.eleiloesCollecting = false;
        
        console.log(`✅ Total em cache: ${window.eleiloesDetalhes.length} eventos`);
        console.log('💾 Acede aos dados: window.eleiloesDetalhes');
        
        // Mostra tabela resumida (só primeiros 5)
        const sample = window.eleiloesDetalhes.slice(0, 5);
        console.table(sample.map(d => ({
            Ref: d.reference,
            Tipo: d.detalhes.tipo.substring(0, 15),
            Tipologia: d.detalhes.tipologia,
            'Área Priv.': d.detalhes.areaPrivativa ? `${d.detalhes.areaPrivativa} m²` : 'N/A',
            'Área Dep.': d.detalhes.areaDependente ? `${d.detalhes.areaDependente} m²` : 'N/A',
            'Área Total': d.detalhes.areaTotal ? `${d.detalhes.areaTotal} m²` : 'N/A',
            Latitude: d.gps.latitude || 'N/A',
            Longitude: d.gps.longitude || 'N/A'
        })));
        
        if (window.eleiloesDetalhes.length > 5) {
            console.log(`... e mais ${window.eleiloesDetalhes.length - 5} eventos`);
        }
        
        return window.eleiloesDetalhes;
    }

    // Expõe função global
    window.collectAllDetails = collectAllDetails;

    // 🗑️ Cria botão para limpar cache
    function createClearCacheButton() {
        const btn = document.createElement('button');
        btn.className = 'eleiloes-clear-cache-btn';
        btn.innerHTML = '🗑️';
        btn.title = 'Limpar Cache';
        
        btn.addEventListener('click', () => {
            if (confirm('🗑️ Limpar cache?\n\nIsto vai apagar todos os dados guardados (GPS + Detalhes) e forçar nova recolha.')) {
                localStorage.removeItem(STORAGE_KEY);
                window.eleiloesDetalhes = [];
                console.log('🗑️ Cache limpo! Recarrega a página para recolher dados novamente.');
                alert('✅ Cache limpo com sucesso!\n\nRecarrega a página para recolher os dados novamente.');
            }
        });
        
        document.body.appendChild(btn);
    }

    // 📊 Cria botão para ver dados
    function createViewDataButton() {
        const btn = document.createElement('button');
        btn.className = 'eleiloes-view-data-btn';
        btn.innerHTML = '📊';
        btn.title = 'Ver Dados';
        
        btn.addEventListener('click', () => {
            openDataModal();
        });
        
        document.body.appendChild(btn);
    }

    // 🎨 Cria modal de progresso visual
    function createProgressModal(totalPages, totalEvents) {
        const overlay = document.createElement('div');
        overlay.className = 'eleiloes-progress-overlay';
        overlay.id = 'eleiloes-progress';
        
        const modal = document.createElement('div');
        modal.className = 'eleiloes-progress-modal';
        
        modal.innerHTML = `
            <div class="eleiloes-progress-header">
                <h2 class="eleiloes-progress-title">🔄 Recolha em Progresso</h2>
                <p class="eleiloes-progress-subtitle">Não feches esta janela durante o processo</p>
            </div>
            
            <div class="eleiloes-progress-stats">
                <div class="eleiloes-stat-card">
                    <div class="eleiloes-stat-label">Páginas</div>
                    <div class="eleiloes-stat-value"><span id="progress-pages">0</span>/${totalPages}</div>
                </div>
                <div class="eleiloes-stat-card">
                    <div class="eleiloes-stat-label">Eventos</div>
                    <div class="eleiloes-stat-value highlight" id="progress-events">0</div>
                </div>
                <div class="eleiloes-stat-card">
                    <div class="eleiloes-stat-label">Erros</div>
                    <div class="eleiloes-stat-value" id="progress-errors">0</div>
                </div>
            </div>
            
            <div class="eleiloes-progress-bar-container">
                <div class="eleiloes-progress-bar" id="progress-bar" style="width: 0%"></div>
            </div>
            
            <div class="eleiloes-progress-text">
                <span id="progress-percentage">0%</span>
                <span class="eleiloes-progress-spinner"></span>
            </div>
            
            <div class="eleiloes-progress-status" id="progress-status">A iniciar...</div>
            
            <div class="eleiloes-progress-time">
                <div class="eleiloes-time-item">
                    <div class="eleiloes-time-label">⏱️ Decorrido</div>
                    <div class="eleiloes-time-value" id="progress-elapsed">00:00</div>
                </div>
                <div class="eleiloes-time-item">
                    <div class="eleiloes-time-label">📊 Estimativa Total</div>
                    <div class="eleiloes-time-value" id="progress-estimate" style="font-size: 18px; color: #059669;">--</div>
                </div>
                <div class="eleiloes-time-item">
                    <div class="eleiloes-time-label">⏳ Falta</div>
                    <div class="eleiloes-time-value" id="progress-remaining">--:--</div>
                </div>
            </div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        return {
            updateProgress: (pages, events, errors, percentage, status) => {
                document.getElementById('progress-pages').textContent = pages;
                document.getElementById('progress-events').textContent = events;
                document.getElementById('progress-errors').textContent = errors;
                document.getElementById('progress-bar').style.width = percentage + '%';
                document.getElementById('progress-percentage').textContent = Math.round(percentage) + '%';
                document.getElementById('progress-status').textContent = status;
            },
            updateTime: (elapsed, estimate, remaining) => {
                document.getElementById('progress-elapsed').textContent = elapsed;
                document.getElementById('progress-estimate').textContent = estimate;
                document.getElementById('progress-remaining').textContent = remaining;
            },
            remove: () => overlay.remove()
        };
    }

    // ⏱️ Formata tempo em mm:ss ou formato amigável
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    // 🕐 Formata tempo como intervalo (ex: "10-15 min")
    function formatTimeRange(avgSeconds, totalEvents, processedEvents) {
        if (processedEvents === 0) return '--';
        
        const remainingEvents = totalEvents - processedEvents;
        const estimatedSeconds = (avgSeconds * remainingEvents);
        const totalEstimated = estimatedSeconds + (Date.now() - window.eleiloesStartTime) / 1000;
        
        const minEstimate = Math.floor(totalEstimated * 0.9 / 60); // -10%
        const maxEstimate = Math.ceil(totalEstimated * 1.1 / 60); // +10%
        
        if (minEstimate === maxEstimate) {
            return `${minEstimate} min`;
        } else if (maxEstimate < 2) {
            return `${Math.floor(totalEstimated / 60)}m ${Math.floor(totalEstimated % 60)}s`;
        } else {
            return `${minEstimate}-${maxEstimate} min`;
        }
    }

    // 🔄 Cria botão para recolher tudo (TODAS as páginas)
    function createCollectAllButton() {
        const btn = document.createElement('button');
        btn.className = 'eleiloes-collect-all-btn';
        btn.innerHTML = '🔄';
        btn.title = 'Recolher Tudo';
        
        btn.addEventListener('click', async () => {
            if (window.eleiloesCollecting) {
                alert('⚠️ Recolha já em progresso!\n\nAguarde a conclusão da recolha atual.');
                return;
            }
            
            // Extrai informação de paginação
            const paginatorText = document.querySelector('.p-paginator-current');
            if (!paginatorText) {
                alert('⚠️ Não foi possível detectar a paginação!');
                return;
            }
            
            // Extrai total de eventos (ex: "A mostrar 61 a 72 de um total de 1207")
            const match = paginatorText.textContent.match(/total de (\d+)/);
            const totalEvents = match ? parseInt(match[1]) : 0;
            
            if (totalEvents === 0) {
                alert('⚠️ Não foi possível detectar o total de eventos!');
                return;
            }
            
            const eventsPerPage = 12; // E-leiloes mostra 12 por página
            const totalPages = Math.ceil(totalEvents / eventsPerPage);
            
            if (!confirm(`🔄 Recolher dados de TODAS as páginas?\n\n📊 ${totalEvents} eventos em ${totalPages} páginas\n⏱️ Isto pode demorar vários minutos!\n\n⚠️ NÃO FECHES ESTA JANELA durante o processo.`)) {
                return;
            }
            
            // Cria modal de progresso
            const progressModal = createProgressModal(totalPages, totalEvents);
            
            // Visual feedback no botão
            btn.classList.add('loading');
            btn.innerHTML = '⏳';
            btn.title = 'A recolher... NÃO FECHAR!';
            
            console.log(`🔄 Iniciando recolha TOTAL: ${totalEvents} eventos em ${totalPages} páginas`);
            
            let processedPages = 0;
            let processedEvents = 0; // 🚀 NOVO: Contador de eventos processados
            let errors = 0;
            const startTime = Date.now();
            window.eleiloesStartTime = startTime; // Global para cálculos
            
            // 🚀 OPTIMIZAÇÃO: Atualiza temporizador baseado em EVENTOS, não páginas
            const timerInterval = setInterval(() => {
                const elapsed = (Date.now() - startTime) / 1000;
                
                if (processedEvents > 5) { // Só mostra estimativa após 5 eventos
                    const avgTimePerEvent = elapsed / processedEvents;
                    const remainingEvents = totalEvents - processedEvents;
                    const remaining = avgTimePerEvent * remainingEvents;
                    
                    progressModal.updateTime(
                        formatTime(elapsed),
                        formatTimeRange(avgTimePerEvent, totalEvents, processedEvents),
                        remaining > 0 ? formatTime(remaining) : '00:00'
                    );
                } else if (processedEvents > 0) {
                    progressModal.updateTime(
                        formatTime(elapsed),
                        '⏳ A calcular...',
                        '⏳ A calcular...'
                    );
                } else {
                    const initialEstimate = Math.ceil(totalEvents * 1.2 / 60);
                    progressModal.updateTime(
                        formatTime(elapsed),
                        `~${initialEstimate} min`,
                        `~${initialEstimate} min`
                    );
                }
            }, 500); // 🚀 Atualiza 2x por segundo para ser mais responsivo
            
            try {
                // Recolhe página atual primeiro
                progressModal.updateProgress(processedPages, processedEvents, errors, 0, '📄 A processar página 1...');
                
                // 🚀 NOVO: Callback para atualizar progresso em tempo real
                await collectAllDetails(true, (processed, total) => {
                    processedEvents = window.eleiloesDetalhes.length; // Conta eventos TOTAIS
                    const eventPercentage = (processedEvents / totalEvents) * 100;
                    progressModal.updateProgress(
                        processedPages + 1, 
                        processedEvents, 
                        errors, 
                        eventPercentage, 
                        `📊 ${processed}/${total} eventos desta página...`
                    );
                });
                
                processedPages++;
                processedEvents = window.eleiloesDetalhes.length;
                const percentage = (processedEvents / totalEvents) * 100;
                progressModal.updateProgress(processedPages, processedEvents, errors, percentage, `✅ Página ${processedPages} concluída`);
                
                // Percorre todas as outras páginas
                for (let page = 2; page <= totalPages; page++) {
                    // Procura botão "Próxima página"
                    const nextBtn = document.querySelector('.p-paginator-next');
                    
                    if (!nextBtn || nextBtn.disabled) {
                        console.log('⚠️ Botão "Próxima" não disponível');
                        const finalPercentage = (processedEvents / totalEvents) * 100;
                        progressModal.updateProgress(processedPages, processedEvents, errors, finalPercentage, '⚠️ Não há mais páginas disponíveis');
                        break;
                    }
                    
                    // Atualiza status
                    const currentPercentage = (processedEvents / totalEvents) * 100;
                    progressModal.updateProgress(processedPages, processedEvents, errors, currentPercentage, `🔄 A mudar para página ${page}...`);
                    
                    // Clica na próxima página
                    nextBtn.click();
                    
                    // 🚀 OPTIMIZAÇÃO: Reduzido de 3s para 2s
                    await new Promise(resolve => setTimeout(resolve, 2000));
                    
                    // Aguarda cards carregarem com timeout inteligente
                    let attempts = 0;
                    while (document.querySelectorAll('.p-evento').length === 0 && attempts < 5) {
                        await new Promise(resolve => setTimeout(resolve, 200));
                        attempts++;
                    }
                    
                    // Atualiza status
                    progressModal.updateProgress(processedPages, processedEvents, errors, currentPercentage, `📄 A processar página ${page}...`);
                    
                    // Recolhe dados desta página com callback em tempo real
                    try {
                        await collectAllDetails(true, (processed, total) => {
                            processedEvents = window.eleiloesDetalhes.length;
                            const eventPercentage = (processedEvents / totalEvents) * 100;
                            progressModal.updateProgress(
                                page, 
                                processedEvents, 
                                errors, 
                                eventPercentage, 
                                `📊 ${processed}/${total} eventos desta página...`
                            );
                        });
                        
                        processedPages++;
                        processedEvents = window.eleiloesDetalhes.length;
                        
                        const finalPercentage = (processedEvents / totalEvents) * 100;
                        progressModal.updateProgress(processedPages, processedEvents, errors, finalPercentage, `✅ Página ${page} concluída`);
                        
                        // 🐛 DEBUG: Log para investigar paragem
                        console.log(`✅ Página ${page} OK - Total: ${processedEvents}/${totalEvents} eventos`);
                        
                    } catch (error) {
                        console.error(`❌ Erro na página ${page}:`, error);
                        errors++;
                        const errorPercentage = (processedEvents / totalEvents) * 100;
                        progressModal.updateProgress(processedPages, processedEvents, errors, errorPercentage, `⚠️ Erro na página ${page}`);
                        
                        // 🐛 DEBUG: Não para em caso de erro, continua
                        console.warn(`⚠️ Continuando apesar do erro na página ${page}...`);
                    }
                    
                    // � OPTIMIZAÇÃO: Delay reduzido de 1s para 300ms
                    await new Promise(resolve => setTimeout(resolve, 300));
                }
                
                clearInterval(timerInterval);
                
                // Atualiza visual final
                const finalCount = window.eleiloesDetalhes.length;
                progressModal.updateProgress(processedPages, finalCount, errors, 100, '🎉 Recolha concluída com sucesso!');
                
                // 🐛 DEBUG: Log final
                console.log(`🎉 CONCLUÍDO: ${finalCount}/${totalEvents} eventos em ${processedPages}/${totalPages} páginas`);
                
                // Aguarda 2s antes de fechar
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                progressModal.remove();
                
                btn.classList.remove('loading');
                btn.innerHTML = '✅';
                btn.title = 'Recolher Tudo';
                
                setTimeout(() => {
                    btn.innerHTML = '🔄';
                }, 3000);
                
                const message = errors > 0 
                    ? `✅ Recolha completa com avisos!\n\n📊 ${window.eleiloesDetalhes.length} eventos processados\n📄 ${processedPages}/${totalPages} páginas\n⚠️ ${errors} erros encontrados`
                    : `✅ Recolha completa!\n\n📊 ${window.eleiloesDetalhes.length} eventos processados\n📄 ${processedPages}/${totalPages} páginas`;
                
                alert(message);
                console.log('🎉 Recolha total concluída!');
                
            } catch (error) {
                clearInterval(timerInterval);
                console.error('❌ Erro crítico na recolha:', error);
                
                progressModal.updateProgress(processedPages, window.eleiloesDetalhes.length, errors, (processedPages / totalPages) * 100, '❌ Erro crítico na recolha');
                
                await new Promise(resolve => setTimeout(resolve, 2000));
                progressModal.remove();
                
                btn.classList.remove('loading');
                btn.innerHTML = '❌';
                btn.title = 'Recolher Tudo';
                
                setTimeout(() => {
                    btn.innerHTML = '🔄';
                }, 3000);
                
                alert(`❌ Erro na recolha!\n\n📄 ${processedPages}/${totalPages} páginas processadas\n📊 ${window.eleiloesDetalhes.length} eventos guardados\n\nVerifica a consola para mais detalhes.`);
            }
        });
        
        document.body.appendChild(btn);
    }

    // 📋 Abre modal com dados tabelados
    function openDataModal() {
        // Remove modal existente se houver
        const existingModal = document.querySelector('.eleiloes-modal-overlay');
        if (existingModal) {
            existingModal.remove();
        }

        // Cria overlay
        const overlay = document.createElement('div');
        overlay.className = 'eleiloes-modal-overlay';
        
        // Cria modal
        const modal = document.createElement('div');
        modal.className = 'eleiloes-modal';
        
        // Header
        const header = document.createElement('div');
        header.className = 'eleiloes-modal-header';
        
        const titleContainer = document.createElement('div');
        const title = document.createElement('h2');
        title.className = 'eleiloes-modal-title';
        title.textContent = '📊 Dados Recolhidos';
        const subtitle = document.createElement('p');
        subtitle.className = 'eleiloes-modal-subtitle';
        subtitle.textContent = `${window.eleiloesDetalhes.length} eventos em cache`;
        titleContainer.appendChild(title);
        titleContainer.appendChild(subtitle);
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'eleiloes-modal-close';
        closeBtn.innerHTML = '✕';
        closeBtn.onclick = () => overlay.remove();
        
        header.appendChild(titleContainer);
        header.appendChild(closeBtn);
        
        // Body
        const body = document.createElement('div');
        body.className = 'eleiloes-modal-body';
        
        if (window.eleiloesDetalhes.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'eleiloes-empty-state';
            emptyState.innerHTML = `
                <div class="eleiloes-empty-state-icon">📭</div>
                <div class="eleiloes-empty-state-text">Nenhum dado recolhido ainda</div>
                <p style="margin-top: 8px; font-size: 14px;">Aguarde a recolha automática ou recarregue a página</p>
            `;
            body.appendChild(emptyState);
        } else {
            const table = document.createElement('table');
            table.className = 'eleiloes-data-table';
            
            // Thead
            const thead = document.createElement('thead');
            thead.innerHTML = `
                <tr>
                    <th>Ref</th>
                    <th>Tipo</th>
                    <th>Subtipo</th>
                    <th>Tipologia</th>
                    <th>Área Priv.</th>
                    <th>Área Dep.</th>
                    <th>Área Total</th>
                    <th>Latitude</th>
                    <th>Longitude</th>
                </tr>
            `;
            
            // Tbody
            const tbody = document.createElement('tbody');
            window.eleiloesDetalhes.forEach(d => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="eleiloes-table-ref">${d.reference}</td>
                    <td>${d.detalhes.tipo}</td>
                    <td>${d.detalhes.subtipo}</td>
                    <td>${d.detalhes.tipologia}</td>
                    <td class="eleiloes-table-area">${d.detalhes.areaPrivativa ? d.detalhes.areaPrivativa + ' m²' : 'N/A'}</td>
                    <td class="eleiloes-table-area">${d.detalhes.areaDependente ? d.detalhes.areaDependente + ' m²' : 'N/A'}</td>
                    <td class="eleiloes-table-area">${d.detalhes.areaTotal ? d.detalhes.areaTotal + ' m²' : 'N/A'}</td>
                    <td class="eleiloes-table-gps">${d.gps.latitude || 'N/A'}</td>
                    <td class="eleiloes-table-gps">${d.gps.longitude || 'N/A'}</td>
                `;
                tbody.appendChild(row);
            });
            
            table.appendChild(thead);
            table.appendChild(tbody);
            body.appendChild(table);
        }
        
        modal.appendChild(header);
        modal.appendChild(body);
        overlay.appendChild(modal);
        
        // Fecha ao clicar fora
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
            }
        });
        
        // Fecha com ESC
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                overlay.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
        
        document.body.appendChild(overlay);
    }

    // 📄 Detecta mudança de página e reinicia recolha
    function setupPaginationListeners() {
        // Observer para detectar quando novos botões de paginação aparecem
        const paginationObserver = new MutationObserver(() => {
            // Procura por botões de paginação (próximo, anterior, números)
            const paginationButtons = document.querySelectorAll('.p-paginator-next, .p-paginator-prev, .p-paginator-page');
            
            paginationButtons.forEach(btn => {
                if (!btn.hasAttribute('data-eleiloes-listener')) {
                    btn.setAttribute('data-eleiloes-listener', 'true');
                    
                    btn.addEventListener('click', () => {
                        console.log('📄 Mudança de página detectada!');
                        
                        // Aguarda os novos cards carregarem (2s) e depois inicia recolha
                        setTimeout(() => {
                            console.log('🔄 A recarregar cards...');
                            enhanceAllCards();
                            
                            // Inicia recolha automática após mais 1s
                            setTimeout(() => {
                                collectAllDetails().catch(err => console.error('❌ Recolha falhou:', err));
                            }, 1000);
                        }, 2000);
                    });
                }
            });
        });
        
        paginationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Adiciona listeners aos botões que já existem
        const existingButtons = document.querySelectorAll('.p-paginator-next, .p-paginator-prev, .p-paginator-page');
        existingButtons.forEach(btn => {
            if (!btn.hasAttribute('data-eleiloes-listener')) {
                btn.setAttribute('data-eleiloes-listener', 'true');
                
                btn.addEventListener('click', () => {
                    console.log('📄 Mudança de página detectada!');
                    
                    setTimeout(() => {
                        console.log('🔄 A recarregar cards...');
                        enhanceAllCards();
                        
                        setTimeout(() => {
                            collectAllDetails().catch(err => console.error('❌ Recolha falhou:', err));
                        }, 1000);
                    }, 2000);
                });
            }
        });
    }

    function init() {
        // 📦 Carrega cache existente
        loadCache();
        console.log('💾 Dados: window.eleiloesDetalhes');
        
        // 🗑️ Cria botão de limpar cache
        setTimeout(createClearCacheButton, 1000);
        
        // 📊 Cria botão de ver dados
        setTimeout(createViewDataButton, 1000);
        
        // 🔄 Cria botão de recolher tudo
        setTimeout(createCollectAllButton, 1000);
        
        // 📄 Configura listeners para paginação
        setupPaginationListeners();
        
        // Melhora cards após 2s
        setTimeout(enhanceAllCards, 2000);

        // 🔥 Recolha automática após 3s (só novos cards)
        setTimeout(() => {
            collectAllDetails().catch(err => console.error('❌ Recolha falhou:', err));
        }, 3000);

        // Observer para novos cards
        const observer = new MutationObserver(() => {
            setTimeout(enhanceAllCards, 500);
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Verifica novos cards a cada 5s
        setInterval(enhanceAllCards, 5000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
