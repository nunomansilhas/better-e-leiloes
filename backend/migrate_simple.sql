-- Simple migration script - run each statement manually if needed
-- Ignores errors for columns that already exist

-- ============================================
-- NOTIFICATION_RULES - Add missing columns
-- ============================================

ALTER TABLE notification_rules ADD COLUMN subtipos TEXT NULL AFTER tipos;
ALTER TABLE notification_rules ADD COLUMN concelhos TEXT NULL AFTER distritos;
ALTER TABLE notification_rules ADD COLUMN variacao_min FLOAT NULL AFTER preco_max;
ALTER TABLE notification_rules ADD COLUMN minutos_restantes INT NULL AFTER variacao_min;
ALTER TABLE notification_rules ADD COLUMN event_reference VARCHAR(50) NULL AFTER minutos_restantes;
ALTER TABLE notification_rules ADD COLUMN triggers_count INT DEFAULT 0 AFTER updated_at;

-- Add index
CREATE INDEX idx_event_reference ON notification_rules(event_reference);

-- ============================================
-- NOTIFICATIONS TABLE - Create if not exists
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

-- Verify
DESCRIBE notification_rules;
DESCRIBE notifications;
