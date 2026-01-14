-- ============================================
-- Better E-Leilões - MySQL/MariaDB Schema
-- ============================================

DROP DATABASE IF EXISTS eleiloes;
CREATE DATABASE eleiloes
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE eleiloes;

-- ============================================
-- Tabela: events
-- ============================================

CREATE TABLE events (
    -- Identificação
    reference VARCHAR(50) PRIMARY KEY COMMENT 'Referência única do evento (ex: LO-2024-12345, NP-2024-67890)',
    tipo_evento ENUM('imovel', 'movel') NOT NULL COMMENT 'Tipo de evento: imóvel ou móvel',

    -- Valores do Leilão
    valor_base DECIMAL(12,2) NULL COMMENT 'Valor base em euros',
    valor_abertura DECIMAL(12,2) NULL COMMENT 'Valor de abertura em euros',
    valor_minimo DECIMAL(12,2) NULL COMMENT 'Valor mínimo em euros',
    lance_atual DECIMAL(12,2) NULL COMMENT 'Lance atual em euros',

    -- GPS (apenas para imóveis)
    gps_latitude DECIMAL(10,7) NULL COMMENT 'Latitude GPS',
    gps_longitude DECIMAL(10,7) NULL COMMENT 'Longitude GPS',

    -- Detalhes do Evento (campos comuns)
    det_tipo VARCHAR(100) NULL COMMENT 'Tipo de bem (ex: Apartamento, Veículo)',
    det_subtipo VARCHAR(100) NULL COMMENT 'Subtipo (ex: T2, Ligeiro Passageiros)',

    -- Detalhes - IMÓVEL específico
    det_tipologia VARCHAR(50) NULL COMMENT 'Tipologia do imóvel (ex: T2, T3)',
    det_area_privativa DECIMAL(10,2) NULL COMMENT 'Área privativa em m²',
    det_area_dependente DECIMAL(10,2) NULL COMMENT 'Área dependente em m²',
    det_area_total DECIMAL(10,2) NULL COMMENT 'Área total em m²',
    det_distrito VARCHAR(100) NULL COMMENT 'Distrito',
    det_concelho VARCHAR(100) NULL COMMENT 'Concelho',
    det_freguesia VARCHAR(100) NULL COMMENT 'Freguesia',

    -- Detalhes - MÓVEL específico
    det_matricula VARCHAR(50) NULL COMMENT 'Matrícula do veículo',

    -- Datas
    data_inicio DATETIME NULL COMMENT 'Data de início do leilão',
    data_fim DATETIME NULL COMMENT 'Data de fim do leilão',

    -- Galeria e Secções (HTML/Text)
    imagens JSON NULL COMMENT 'Array JSON de URLs das imagens',
    descricao MEDIUMTEXT NULL COMMENT 'HTML da secção Descrição',
    observacoes MEDIUMTEXT NULL COMMENT 'HTML da secção Observações',
    onuselimitacoes MEDIUMTEXT NULL COMMENT 'HTML da secção Ónus e Limitações',
    descricao_predial MEDIUMTEXT NULL COMMENT 'HTML da secção Descrição Predial',
    cerimonia_encerramento MEDIUMTEXT NULL COMMENT 'HTML da secção Cerimónia de Encerramento',
    agente_execucao MEDIUMTEXT NULL COMMENT 'HTML da secção Agente de Execução',
    dados_processo MEDIUMTEXT NULL COMMENT 'HTML da secção Dados do Processo',

    -- Metadados
    scraped_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Data/hora do primeiro scrape',
    updated_at DATETIME NULL ON UPDATE CURRENT_TIMESTAMP COMMENT 'Data/hora da última atualização',

    -- Índices
    INDEX idx_tipo_evento (tipo_evento),
    INDEX idx_data_fim (data_fim),
    INDEX idx_concelho (det_concelho),
    INDEX idx_distrito (det_distrito),
    INDEX idx_scraped_at (scraped_at)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tabela principal de eventos de leilão';

-- ============================================
-- Views úteis
-- ============================================

-- View: Eventos ativos (ainda não terminaram)
CREATE VIEW vw_eventos_ativos AS
SELECT
    reference,
    tipo_evento,
    valor_base,
    det_tipo,
    det_subtipo,
    det_concelho,
    data_inicio,
    data_fim,
    TIMESTAMPDIFF(HOUR, NOW(), data_fim) as horas_restantes
FROM events
WHERE data_fim > NOW()
ORDER BY data_fim ASC;

-- View: Imóveis com GPS
CREATE VIEW vw_imoveis_gps AS
SELECT
    reference,
    det_tipo,
    det_concelho,
    det_freguesia,
    gps_latitude,
    gps_longitude,
    valor_base,
    data_fim
FROM events
WHERE tipo_evento = 'imovel'
  AND gps_latitude IS NOT NULL
  AND gps_longitude IS NOT NULL;

-- View: Estatísticas por concelho
CREATE VIEW vw_stats_concelho AS
SELECT
    det_concelho,
    COUNT(*) as total_eventos,
    SUM(CASE WHEN tipo_evento = 'imovel' THEN 1 ELSE 0 END) as total_imoveis,
    SUM(CASE WHEN tipo_evento = 'movel' THEN 1 ELSE 0 END) as total_moveis,
    AVG(valor_base) as valor_medio,
    MIN(valor_base) as valor_minimo,
    MAX(valor_base) as valor_maximo
FROM events
WHERE det_concelho IS NOT NULL
GROUP BY det_concelho
ORDER BY total_eventos DESC;

-- ============================================
-- Procedures úteis
-- ============================================

DELIMITER //

-- Procedure: Limpar eventos antigos
CREATE PROCEDURE sp_limpar_eventos_antigos(IN dias_antiguidade INT)
BEGIN
    DELETE FROM events
    WHERE data_fim < DATE_SUB(NOW(), INTERVAL dias_antiguidade DAY);

    SELECT ROW_COUNT() as eventos_removidos;
END //

-- Procedure: Estatísticas gerais
CREATE PROCEDURE sp_estatisticas_gerais()
BEGIN
    SELECT
        COUNT(*) as total_eventos,
        SUM(CASE WHEN tipo_evento = 'imovel' THEN 1 ELSE 0 END) as total_imoveis,
        SUM(CASE WHEN tipo_evento = 'movel' THEN 1 ELSE 0 END) as total_moveis,
        COUNT(DISTINCT det_concelho) as concelhos_unicos,
        AVG(valor_base) as valor_medio,
        MIN(scraped_at) as primeiro_scrape,
        MAX(scraped_at) as ultimo_scrape
    FROM events;
END //

DELIMITER ;

-- ============================================
-- Dados de exemplo (opcional - comentado)
-- ============================================

/*
INSERT INTO events (
    reference, tipo_evento,
    valor_base, valor_abertura, valor_minimo,
    det_tipo, det_subtipo, det_tipologia,
    det_concelho, det_distrito,
    data_inicio, data_fim,
    scraped_at
) VALUES
(
    'LO-2024-00001', 'imovel',
    150000.00, 120000.00, 100000.00,
    'Apartamento', 'T2', 'T2',
    'Lisboa', 'Lisboa',
    '2024-01-01 10:00:00', '2024-01-15 18:00:00',
    NOW()
),
(
    'NP-2024-00001', 'movel',
    8000.00, 6400.00, 5000.00,
    'Veículo', 'Ligeiro Passageiros', NULL,
    NULL, NULL,
    '2024-01-01 10:00:00', '2024-01-10 18:00:00',
    NOW()
);
*/

-- ============================================
-- Grants (ajustar conforme necessário)
-- ============================================

-- Criar utilizador para a aplicação (ajustar password)
-- CREATE USER 'eleiloes_app'@'localhost' IDENTIFIED BY 'SUA_PASSWORD_AQUI';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON eleiloes.* TO 'eleiloes_app'@'localhost';
-- FLUSH PRIVILEGES;

-- ============================================
-- Informações
-- ============================================

SELECT
    'Base de dados criada com sucesso!' as status,
    VERSION() as mysql_version,
    DATABASE() as database_name;
