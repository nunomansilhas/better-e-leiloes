-- Migration: Convert FLOAT to DECIMAL for monetary precision
-- FLOAT causes rounding errors (e.g., 10457.77 becomes 10457.80)
-- DECIMAL(12,2) stores exact values with 2 decimal places

-- Events table
ALTER TABLE events
    MODIFY COLUMN lance_atual DECIMAL(12,2) DEFAULT 0,
    MODIFY COLUMN valor_base DECIMAL(12,2) NULL,
    MODIFY COLUMN valor_abertura DECIMAL(12,2) NULL,
    MODIFY COLUMN valor_minimo DECIMAL(12,2) NULL;

-- Price history table
ALTER TABLE price_history
    MODIFY COLUMN old_price DECIMAL(12,2) NULL,
    MODIFY COLUMN new_price DECIMAL(12,2) NOT NULL,
    MODIFY COLUMN change_amount DECIMAL(12,2) NULL;

-- Refresh logs table
ALTER TABLE refresh_logs
    MODIFY COLUMN result_lance DECIMAL(12,2) NULL;
