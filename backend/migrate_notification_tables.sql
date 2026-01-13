-- Migration script to update notification_rules table to match backend model
-- Run this on your MySQL database

-- ============================================
-- NOTIFICATION_RULES TABLE
-- ============================================

-- Check if table exists, if not create it
CREATE TABLE IF NOT EXISTS notification_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    tipos TEXT NULL,
    subtipos TEXT NULL,
    distritos TEXT NULL,
    concelhos TEXT NULL,
    preco_min FLOAT NULL,
    preco_max FLOAT NULL,
    variacao_min FLOAT NULL,
    minutos_restantes INT NULL,
    event_reference VARCHAR(50) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,
    triggers_count INT DEFAULT 0,
    INDEX idx_rule_type (rule_type),
    INDEX idx_event_reference (event_reference),
    INDEX idx_active (active)
);

-- If table already exists, add missing columns
-- (MySQL doesn't support IF NOT EXISTS for ADD COLUMN, so we use ALTER IGNORE or separate statements)

-- Add subtipos if not exists
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notification_rules' AND COLUMN_NAME = 'subtipos');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE notification_rules ADD COLUMN subtipos TEXT NULL AFTER tipos', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add concelhos if not exists
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notification_rules' AND COLUMN_NAME = 'concelhos');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE notification_rules ADD COLUMN concelhos TEXT NULL AFTER distritos', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add variacao_min if not exists
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notification_rules' AND COLUMN_NAME = 'variacao_min');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE notification_rules ADD COLUMN variacao_min FLOAT NULL AFTER preco_max', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add minutos_restantes if not exists
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notification_rules' AND COLUMN_NAME = 'minutos_restantes');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE notification_rules ADD COLUMN minutos_restantes INT NULL AFTER variacao_min', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add event_reference if not exists
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notification_rules' AND COLUMN_NAME = 'event_reference');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE notification_rules ADD COLUMN event_reference VARCHAR(50) NULL AFTER minutos_restantes', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add triggers_count if not exists
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notification_rules' AND COLUMN_NAME = 'triggers_count');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE notification_rules ADD COLUMN triggers_count INT DEFAULT 0 AFTER updated_at', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add index on event_reference if not exists
SET @idx_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notification_rules' AND INDEX_NAME = 'idx_event_reference');
SET @sql = IF(@idx_exists = 0, 'CREATE INDEX idx_event_reference ON notification_rules(event_reference)', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================
-- NOTIFICATIONS TABLE
-- ============================================

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
    preco_variacao FLOAT NULL,
    `read` BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_event_reference (event_reference),
    INDEX idx_notification_type (notification_type),
    INDEX idx_created_at (created_at),
    INDEX idx_read (`read`)
);

-- Add preco_variacao if not exists (some older versions might not have it)
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'notifications' AND COLUMN_NAME = 'preco_variacao');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE notifications ADD COLUMN preco_variacao FLOAT NULL AFTER preco_atual', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ============================================
-- VERIFY STRUCTURE
-- ============================================

SELECT 'notification_rules columns:' as info;
SHOW COLUMNS FROM notification_rules;

SELECT 'notifications columns:' as info;
SHOW COLUMNS FROM notifications;
