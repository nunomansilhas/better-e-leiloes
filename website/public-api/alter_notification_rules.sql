-- Add missing columns to notification_rules table
-- Run this in your MySQL database

-- Add subtipos column
ALTER TABLE notification_rules
ADD COLUMN IF NOT EXISTS subtipos TEXT NULL AFTER tipos;

-- Add concelhos column
ALTER TABLE notification_rules
ADD COLUMN IF NOT EXISTS concelhos TEXT NULL AFTER distritos;

-- Add variacao_min column
ALTER TABLE notification_rules
ADD COLUMN IF NOT EXISTS variacao_min FLOAT NULL AFTER preco_max;

-- Add minutos_restantes column
ALTER TABLE notification_rules
ADD COLUMN IF NOT EXISTS minutos_restantes INT NULL AFTER variacao_min;

-- Add triggers_count column
ALTER TABLE notification_rules
ADD COLUMN IF NOT EXISTS triggers_count INT DEFAULT 0 AFTER updated_at;

-- Add last_triggered column
ALTER TABLE notification_rules
ADD COLUMN IF NOT EXISTS last_triggered DATETIME NULL AFTER triggers_count;

-- Verify the changes
DESCRIBE notification_rules;
