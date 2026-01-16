-- Migration 005: Market Prices Cache and Analysis Feedback
-- Date: 2026-01-15
-- Description: Adds tables for caching market prices and collecting user feedback

-- ============================================================
-- Table: market_prices
-- Cache of market prices scraped periodically from various sources
-- Used for instant price lookups without real-time scraping
-- ============================================================
CREATE TABLE IF NOT EXISTS market_prices (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Vehicle identification
    marca VARCHAR(100) NOT NULL,
    modelo VARCHAR(150) NOT NULL,
    variante VARCHAR(150) NULL,               -- e.g., "1.6 HDi", "2.0 TDI"

    -- Characteristics
    ano INT NOT NULL,
    combustivel VARCHAR(30) NULL,             -- Diesel, Gasolina, Elétrico, Híbrido
    quilometros_min INT NULL,
    quilometros_max INT NULL,

    -- Aggregated prices
    preco_min DECIMAL(12, 2) NULL,
    preco_max DECIMAL(12, 2) NULL,
    preco_medio DECIMAL(12, 2) NULL,
    preco_mediana DECIMAL(12, 2) NULL,
    num_anuncios INT DEFAULT 0,

    -- Sample listings (JSON array)
    sample_listings TEXT NULL,

    -- Source and freshness
    fonte VARCHAR(50) NOT NULL,               -- 'standvirtual', 'autosapo', 'olx', 'ai_estimate'
    confianca VARCHAR(20) DEFAULT 'media',    -- 'baixa', 'media', 'alta'
    data_recolha DATE NOT NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_market_marca_modelo (marca, modelo),
    INDEX idx_market_marca_modelo_ano (marca, modelo, ano),
    INDEX idx_market_data_recolha (data_recolha DESC),
    INDEX idx_market_fonte (fonte)
);


-- ============================================================
-- Table: auction_history
-- Historical record of past auctions for comparison
-- Tracks what similar vehicles sold for
-- ============================================================
CREATE TABLE IF NOT EXISTS auction_history (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Reference to original event
    reference VARCHAR(50) NOT NULL,

    -- Vehicle identification
    marca VARCHAR(100) NULL,
    modelo VARCHAR(150) NULL,
    variante VARCHAR(150) NULL,
    ano INT NULL,
    combustivel VARCHAR(30) NULL,

    -- Auction values
    valor_base DECIMAL(12, 2) NULL,
    valor_venda DECIMAL(12, 2) NULL,          -- NULL if not sold
    vendido BOOLEAN DEFAULT FALSE,

    -- Auction dates
    data_inicio DATE NULL,
    data_fim DATE NULL,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_history_marca_modelo (marca, modelo),
    INDEX idx_history_marca_modelo_ano (marca, modelo, ano),
    INDEX idx_history_data_fim (data_fim DESC),
    INDEX idx_history_vendido (vendido),
    UNIQUE INDEX idx_history_reference (reference)
);


-- ============================================================
-- Table: analysis_feedback
-- User feedback on analysis quality for continuous improvement
-- ============================================================
CREATE TABLE IF NOT EXISTS analysis_feedback (
    id INT PRIMARY KEY AUTO_INCREMENT,

    -- Reference to analysis
    reference VARCHAR(50) NOT NULL,

    -- User ratings (0-10)
    score_precisao INT NULL,                  -- How accurate was the analysis?
    score_utilidade INT NULL,                 -- How useful was the analysis?

    -- What was wrong (checkboxes)
    erro_preco BOOLEAN DEFAULT FALSE,         -- Price estimation was wrong
    erro_problemas_modelo BOOLEAN DEFAULT FALSE,  -- Model problems were incorrect
    erro_recomendacao BOOLEAN DEFAULT FALSE,  -- Recommendation didn't make sense
    falta_info BOOLEAN DEFAULT FALSE,         -- Missing important information
    outro_erro TEXT NULL,                     -- Other error description

    -- Actual outcome (if user bought)
    comprou BOOLEAN NULL,                     -- Did user buy this vehicle?
    preco_compra DECIMAL(12, 2) NULL,         -- Actual purchase price
    satisfacao_compra INT NULL,               -- Satisfaction with purchase (0-10)

    -- Additional feedback
    comentario TEXT NULL,                     -- Free text comments

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_feedback_reference (reference),
    INDEX idx_feedback_created (created_at DESC),
    INDEX idx_feedback_scores (score_precisao, score_utilidade)
);


-- ============================================================
-- Alter event_vehicle_data to add new fields
-- ============================================================

-- Add market price source tracking
ALTER TABLE event_vehicle_data
ADD COLUMN IF NOT EXISTS market_preco_fonte VARCHAR(50) NULL AFTER market_fonte,
ADD COLUMN IF NOT EXISTS market_preco_confianca VARCHAR(20) NULL AFTER market_preco_fonte,
ADD COLUMN IF NOT EXISTS market_data_recolha DATE NULL AFTER market_preco_confianca;

-- Add scores
ALTER TABLE event_vehicle_data
ADD COLUMN IF NOT EXISTS score_oportunidade FLOAT NULL AFTER desconto_percentagem,
ADD COLUMN IF NOT EXISTS score_risco FLOAT NULL AFTER score_oportunidade,
ADD COLUMN IF NOT EXISTS score_liquidez FLOAT NULL AFTER score_risco;

-- Add checklist and red flags
ALTER TABLE event_vehicle_data
ADD COLUMN IF NOT EXISTS ai_checklist TEXT NULL AFTER ai_cons,
ADD COLUMN IF NOT EXISTS ai_red_flags TEXT NULL AFTER ai_checklist,
ADD COLUMN IF NOT EXISTS ai_lance_maximo_sugerido DECIMAL(12, 2) NULL AFTER ai_red_flags;

-- Add estimated costs
ALTER TABLE event_vehicle_data
ADD COLUMN IF NOT EXISTS custo_total_estimado DECIMAL(12, 2) NULL AFTER ai_lance_maximo_sugerido,
ADD COLUMN IF NOT EXISTS preco_revenda_minimo DECIMAL(12, 2) NULL AFTER custo_total_estimado;

-- Add feedback reference
ALTER TABLE event_vehicle_data
ADD COLUMN IF NOT EXISTS feedback_score_medio FLOAT NULL AFTER preco_revenda_minimo,
ADD COLUMN IF NOT EXISTS feedback_count INT DEFAULT 0 AFTER feedback_score_medio;
