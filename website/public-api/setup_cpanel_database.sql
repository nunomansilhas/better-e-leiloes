-- ============================================================
-- SETUP COMPLETO PARA cPanel - E-Leiloes Public API
-- Corre isto no phpMyAdmin do cPanel
-- ============================================================

-- 1. TABELA PRINCIPAL: events
CREATE TABLE IF NOT EXISTS events (
    -- IDENTIFICACAO
    reference VARCHAR(50) PRIMARY KEY,
    id_api INT DEFAULT NULL,
    origem INT DEFAULT NULL,
    verba_id INT DEFAULT NULL,

    -- TITULO E CAPA
    titulo VARCHAR(500) DEFAULT NULL,
    capa VARCHAR(500) DEFAULT NULL,

    -- TIPO/CATEGORIA
    tipo_id INT DEFAULT NULL,
    subtipo_id INT DEFAULT NULL,
    tipologia_id INT DEFAULT NULL,
    tipo VARCHAR(100) DEFAULT NULL,
    subtipo VARCHAR(100) DEFAULT NULL,
    tipologia VARCHAR(50) DEFAULT NULL,
    modalidade_id INT DEFAULT NULL,

    -- VALORES (EUR)
    valor_base DECIMAL(12,2) DEFAULT NULL,
    valor_abertura DECIMAL(12,2) DEFAULT NULL,
    valor_minimo DECIMAL(12,2) DEFAULT NULL,
    lance_atual DECIMAL(12,2) DEFAULT 0,
    lance_atual_id INT DEFAULT NULL,

    -- IVA
    iva_cobrar BOOLEAN DEFAULT FALSE,
    iva_percentagem INT DEFAULT 23,

    -- DATAS
    data_inicio DATETIME DEFAULT NULL,
    data_fim_inicial DATETIME DEFAULT NULL,
    data_fim DATETIME DEFAULT NULL,

    -- STATUS
    cancelado BOOLEAN DEFAULT FALSE,
    iniciado BOOLEAN DEFAULT FALSE,
    terminado BOOLEAN DEFAULT FALSE,
    ultimos_5m BOOLEAN DEFAULT FALSE,

    -- AREAS (m2)
    area_privativa DECIMAL(10,2) DEFAULT NULL,
    area_dependente DECIMAL(10,2) DEFAULT NULL,
    area_total DECIMAL(10,2) DEFAULT NULL,

    -- MORADA COMPLETA
    morada TEXT DEFAULT NULL,
    morada_numero VARCHAR(50) DEFAULT NULL,
    morada_andar VARCHAR(50) DEFAULT NULL,
    morada_cp VARCHAR(20) DEFAULT NULL,
    distrito VARCHAR(100) DEFAULT NULL,
    concelho VARCHAR(100) DEFAULT NULL,
    freguesia VARCHAR(200) DEFAULT NULL,

    -- GPS
    latitude DECIMAL(10,7) DEFAULT NULL,
    longitude DECIMAL(10,7) DEFAULT NULL,

    -- VEICULOS
    matricula VARCHAR(50) DEFAULT NULL,
    osae360 VARCHAR(100) DEFAULT NULL,

    -- DESCRICOES
    descricao MEDIUMTEXT DEFAULT NULL,
    observacoes MEDIUMTEXT DEFAULT NULL,

    -- PROCESSO JUDICIAL
    processo_id INT DEFAULT NULL,
    processo_numero VARCHAR(100) DEFAULT NULL,
    processo_comarca VARCHAR(200) DEFAULT NULL,
    processo_comarca_codigo VARCHAR(20) DEFAULT NULL,
    processo_tribunal VARCHAR(200) DEFAULT NULL,

    -- EXECUTADOS (JSON)
    executados JSON DEFAULT NULL,

    -- CERIMONIA
    cerimonia_id INT DEFAULT NULL,
    cerimonia_data DATETIME DEFAULT NULL,
    cerimonia_local VARCHAR(200) DEFAULT NULL,
    cerimonia_morada TEXT DEFAULT NULL,

    -- AGENTE/GESTOR
    gestor_id INT DEFAULT NULL,
    gestor_tipo VARCHAR(100) DEFAULT NULL,
    gestor_tipo_id INT DEFAULT NULL,
    gestor_cedula VARCHAR(50) DEFAULT NULL,
    gestor_nome VARCHAR(200) DEFAULT NULL,
    gestor_email VARCHAR(200) DEFAULT NULL,
    gestor_comarca VARCHAR(200) DEFAULT NULL,
    gestor_tribunal VARCHAR(200) DEFAULT NULL,
    gestor_telefone VARCHAR(50) DEFAULT NULL,
    gestor_fax VARCHAR(50) DEFAULT NULL,
    gestor_morada TEXT DEFAULT NULL,
    gestor_horario TEXT DEFAULT NULL,

    -- ARRAYS JSON
    fotos JSON DEFAULT NULL,
    onus JSON DEFAULT NULL,
    desc_predial JSON DEFAULT NULL,
    visitas JSON DEFAULT NULL,
    anexos JSON DEFAULT NULL,

    -- METADADOS
    data_servidor DATETIME DEFAULT NULL,
    data_atualizacao DATETIME DEFAULT NULL,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,

    -- INDICES
    INDEX idx_tipo_id (tipo_id),
    INDEX idx_distrito (distrito),
    INDEX idx_concelho (concelho),
    INDEX idx_data_fim (data_fim),
    INDEX idx_cancelado (cancelado),
    INDEX idx_lance_atual (lance_atual),
    INDEX idx_valor_base (valor_base)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 2. TABELA: price_history (historico de lances)
CREATE TABLE IF NOT EXISTS price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reference VARCHAR(50) NOT NULL,
    old_price FLOAT NULL,
    new_price FLOAT NOT NULL,
    change_amount FLOAT NULL,
    change_percent FLOAT NULL,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(20) NULL,
    INDEX idx_reference (reference),
    INDEX idx_recorded_at (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 3. TABELA: refresh_logs (pedidos de refresh do frontend)
CREATE TABLE IF NOT EXISTS refresh_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reference VARCHAR(50) NOT NULL,
    refresh_type VARCHAR(20) DEFAULT 'price',
    state INT DEFAULT 0 COMMENT '0=pending, 1=processing, 2=completed, 3=error',
    result_lance FLOAT NULL,
    result_message VARCHAR(500) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME NULL,
    INDEX idx_reference (reference),
    INDEX idx_state (state),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 4. TABELA: notification_rules (regras de notificacao)
CREATE TABLE IF NOT EXISTS notification_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    event_reference VARCHAR(50) NULL,
    tipos VARCHAR(100) NULL,
    subtipos TEXT NULL,
    distritos VARCHAR(500) NULL,
    concelhos TEXT NULL,
    preco_min FLOAT NULL,
    preco_max FLOAT NULL,
    variacao_min FLOAT NULL,
    minutos_restantes INT NULL,
    last_price FLOAT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    triggers_count INT DEFAULT 0,
    last_triggered DATETIME NULL,
    INDEX idx_event_reference (event_reference)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 5. TABELA: notifications (notificacoes geradas)
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_id INT NULL,
    notification_type VARCHAR(50) NOT NULL,
    event_reference VARCHAR(50) NOT NULL,
    event_titulo VARCHAR(500) NULL,
    event_tipo VARCHAR(100) NULL,
    event_subtipo VARCHAR(100) NULL,
    event_distrito VARCHAR(100) NULL,
    preco_anterior FLOAT NULL,
    preco_atual FLOAT NULL,
    `read` BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_reference (event_reference),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 6. TABELA: favorites (favoritos do utilizador)
CREATE TABLE IF NOT EXISTS favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_reference VARCHAR(50) NOT NULL UNIQUE,
    event_titulo VARCHAR(500) NULL,
    event_tipo VARCHAR(100) NULL,
    event_subtipo VARCHAR(100) NULL,
    event_distrito VARCHAR(100) NULL,
    event_data_fim DATETIME NULL,
    price_when_added FLOAT NULL,
    last_known_price FLOAT NULL,
    price_min_seen FLOAT NULL,
    price_max_seen FLOAT NULL,
    notify_price_change BOOLEAN DEFAULT TRUE,
    notify_ending_soon BOOLEAN DEFAULT TRUE,
    notify_ending_minutes INT DEFAULT 30,
    notify_price_threshold FLOAT NULL,
    price_changes_count INT DEFAULT 0,
    notifications_sent INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    last_notified_at DATETIME NULL,
    notes TEXT NULL,
    INDEX idx_event_reference (event_reference),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 7. TABELA: event_ai_tips (tips de AI)
CREATE TABLE IF NOT EXISTS event_ai_tips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reference VARCHAR(50) NOT NULL UNIQUE,
    event_titulo VARCHAR(500) NULL,
    event_tipo VARCHAR(100) NULL,
    event_subtipo VARCHAR(100) NULL,
    event_distrito VARCHAR(100) NULL,
    event_valor_base DECIMAL(12,2) NULL,
    tip_summary TEXT NULL,
    tip_analysis TEXT NULL,
    tip_pros TEXT NULL,
    tip_cons TEXT NULL,
    tip_recommendation VARCHAR(50) NULL,
    tip_confidence FLOAT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT NULL,
    model_used VARCHAR(100) NULL,
    tokens_used INT NULL,
    processing_time_ms INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME NULL,
    updated_at DATETIME NULL,
    INDEX idx_reference (reference),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 8. TABELA: ai_pipeline_state (estado do pipeline de AI)
CREATE TABLE IF NOT EXISTS ai_pipeline_state (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pipeline_name VARCHAR(50) NOT NULL UNIQUE,
    is_running BOOLEAN DEFAULT FALSE,
    current_reference VARCHAR(50) NULL,
    current_event_titulo VARCHAR(500) NULL,
    total_processed INT DEFAULT 0,
    total_failed INT DEFAULT 0,
    total_pending INT DEFAULT 0,
    last_started_at DATETIME NULL,
    last_completed_at DATETIME NULL,
    last_error TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 9. TABELA: pipeline_state (estado geral dos pipelines - backend)
CREATE TABLE IF NOT EXISTS pipeline_state (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pipeline_name VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    is_running BOOLEAN DEFAULT FALSE,
    interval_hours FLOAT NULL,
    description VARCHAR(500) NULL,
    last_run DATETIME NULL,
    next_run DATETIME NULL,
    runs_count INT DEFAULT 0,
    last_result TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- VERIFICACAO - Corre isto para confirmar que as tabelas foram criadas
-- ============================================================
SELECT 'Tabelas criadas:' AS info;
SHOW TABLES;
