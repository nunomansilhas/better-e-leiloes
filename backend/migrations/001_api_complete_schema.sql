-- ============================================================
-- MIGRAÇÃO: Schema completo para API oficial e-leiloes.pt
-- Criado: 2025-12-22
-- ============================================================

-- Backup da tabela antiga (opcional - fazer antes de dropar)
-- CREATE TABLE events_backup AS SELECT * FROM events;

-- Drop tabela antiga (CUIDADO!)
DROP TABLE IF EXISTS events;

-- Nova tabela com TODOS os campos da API oficial
CREATE TABLE events (
    -- ========== IDENTIFICAÇÃO ==========
    reference VARCHAR(50) PRIMARY KEY,                    -- LO1427992025, NP1133632025
    id_api INT DEFAULT NULL,                              -- ID interno da API (183193)
    origem INT DEFAULT NULL,                              -- ID origem (258095)
    verba_id INT DEFAULT NULL,                            -- ID da verba (122416)

    -- ========== TÍTULO E CAPA ==========
    titulo VARCHAR(500) DEFAULT NULL,                     -- "Apartamento sito em Caparica"
    capa VARCHAR(500) DEFAULT NULL,                       -- URL da imagem de capa

    -- ========== TIPO/CATEGORIA ==========
    tipo_id INT DEFAULT NULL,                             -- 1=Imóvel, 2=Veículo, etc.
    subtipo_id INT DEFAULT NULL,                          -- ID do subtipo
    tipologia_id INT DEFAULT NULL,                        -- ID da tipologia
    tipo VARCHAR(100) DEFAULT NULL,                       -- "Imóvel"
    subtipo VARCHAR(100) DEFAULT NULL,                    -- "Apartamento"
    tipologia VARCHAR(50) DEFAULT NULL,                   -- "T2"
    modalidade_id INT DEFAULT NULL,                       -- 1=Leilão Online, etc.

    -- ========== VALORES (€) ==========
    valor_base DECIMAL(12,2) DEFAULT NULL,                -- 180000.00
    valor_abertura DECIMAL(12,2) DEFAULT NULL,            -- 90000.00
    valor_minimo DECIMAL(12,2) DEFAULT NULL,              -- 153000.00
    lance_atual DECIMAL(12,2) DEFAULT 0,                  -- 126121.20
    lance_atual_id INT DEFAULT NULL,                      -- ID do lance atual

    -- ========== IVA ==========
    iva_cobrar BOOLEAN DEFAULT FALSE,                     -- Se cobra IVA
    iva_percentagem INT DEFAULT 23,                       -- Percentagem IVA

    -- ========== DATAS ==========
    data_inicio DATETIME DEFAULT NULL,                    -- 2025-12-05 00:00:02
    data_fim_inicial DATETIME DEFAULT NULL,               -- Data fim original
    data_fim DATETIME DEFAULT NULL,                       -- 2026-01-28 10:00:00 (pode mudar)

    -- ========== STATUS ==========
    cancelado BOOLEAN DEFAULT FALSE,                      -- Evento cancelado?
    iniciado BOOLEAN DEFAULT FALSE,                       -- Já começou?
    terminado BOOLEAN DEFAULT FALSE,                      -- Já terminou?
    ultimos_5m BOOLEAN DEFAULT FALSE,                     -- Nos últimos 5 minutos?

    -- ========== ÁREAS (m²) ==========
    area_privativa DECIMAL(10,2) DEFAULT NULL,            -- 71.96
    area_dependente DECIMAL(10,2) DEFAULT NULL,           -- 5.60
    area_total DECIMAL(10,2) DEFAULT NULL,                -- 77.56

    -- ========== MORADA COMPLETA ==========
    morada TEXT DEFAULT NULL,                             -- "Rua 3 Vales, Alcaniça"
    morada_numero VARCHAR(50) DEFAULT NULL,               -- "32"
    morada_andar VARCHAR(50) DEFAULT NULL,                -- "3º A"
    morada_cp VARCHAR(20) DEFAULT NULL,                   -- "2825-024"
    distrito VARCHAR(100) DEFAULT NULL,                   -- "Setúbal"
    concelho VARCHAR(100) DEFAULT NULL,                   -- "Almada"
    freguesia VARCHAR(200) DEFAULT NULL,                  -- "União das freguesias..."

    -- ========== GPS ==========
    latitude DECIMAL(10,7) DEFAULT NULL,                  -- 38.6678921
    longitude DECIMAL(10,7) DEFAULT NULL,                 -- -9.1874379

    -- ========== VEÍCULOS ==========
    matricula VARCHAR(50) DEFAULT NULL,                   -- Matrícula do veículo
    osae360 VARCHAR(100) DEFAULT NULL,                    -- Link OSAE 360

    -- ========== DESCRIÇÕES (texto) ==========
    descricao MEDIUMTEXT DEFAULT NULL,                    -- Descrição completa
    observacoes MEDIUMTEXT DEFAULT NULL,                  -- Observações

    -- ========== PROCESSO JUDICIAL ==========
    processo_id INT DEFAULT NULL,                         -- 83408
    processo_numero VARCHAR(100) DEFAULT NULL,            -- "6715/24.0T8LSB"
    processo_comarca VARCHAR(200) DEFAULT NULL,           -- "Comarca de Lisboa"
    processo_comarca_codigo VARCHAR(20) DEFAULT NULL,     -- "1044"
    processo_tribunal VARCHAR(200) DEFAULT NULL,          -- "Lisboa - Juízo Execução - Juiz 2"

    -- ========== EXECUTADOS (JSON) ==========
    executados JSON DEFAULT NULL,                         -- [{nif, nome, requerido}, ...]

    -- ========== CERIMÓNIA ==========
    cerimonia_id INT DEFAULT NULL,                        -- 1083
    cerimonia_data DATETIME DEFAULT NULL,                 -- 2026-01-28 14:30:00
    cerimonia_local VARCHAR(200) DEFAULT NULL,            -- "Lisboa - Palácio da Justiça"
    cerimonia_morada TEXT DEFAULT NULL,                   -- Morada completa

    -- ========== AGENTE/GESTOR ==========
    gestor_id INT DEFAULT NULL,                           -- 78
    gestor_tipo VARCHAR(100) DEFAULT NULL,                -- "Agente de Execução"
    gestor_tipo_id INT DEFAULT NULL,                      -- 1
    gestor_cedula VARCHAR(50) DEFAULT NULL,               -- "5224"
    gestor_nome VARCHAR(200) DEFAULT NULL,                -- "SUSANA COSTA"
    gestor_email VARCHAR(200) DEFAULT NULL,               -- "5224@solicitador.net"
    gestor_comarca VARCHAR(200) DEFAULT NULL,
    gestor_tribunal VARCHAR(200) DEFAULT NULL,
    gestor_telefone VARCHAR(50) DEFAULT NULL,
    gestor_fax VARCHAR(50) DEFAULT NULL,
    gestor_morada TEXT DEFAULT NULL,
    gestor_horario TEXT DEFAULT NULL,

    -- ========== ARRAYS JSON ==========
    fotos JSON DEFAULT NULL,                              -- [{legenda, image, thumbnail}, ...]
    onus JSON DEFAULT NULL,                               -- [{tipo, descricao, tipoDesc}, ...]
    desc_predial JSON DEFAULT NULL,                       -- [{numero, fracao, artigos}, ...]
    visitas JSON DEFAULT NULL,                            -- Visitas agendadas
    anexos JSON DEFAULT NULL,                             -- Documentos anexos

    -- ========== METADADOS ==========
    data_servidor DATETIME DEFAULT NULL,                  -- Timestamp do servidor API
    data_atualizacao DATETIME DEFAULT NULL,               -- Última atualização na API
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,        -- Quando fizemos scrape
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,                           -- Registo ativo?

    -- ========== ÍNDICES ==========
    INDEX idx_tipo_id (tipo_id),
    INDEX idx_distrito (distrito),
    INDEX idx_concelho (concelho),
    INDEX idx_data_fim (data_fim),
    INDEX idx_cancelado (cancelado),
    INDEX idx_lance_atual (lance_atual),
    INDEX idx_valor_base (valor_base)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Notas:
-- - JSON fields: fotos, onus, desc_predial, visitas, anexos, executados
-- - Todos os campos nullable para flexibilidade
-- - Índices nos campos mais usados para filtros
-- ============================================================
