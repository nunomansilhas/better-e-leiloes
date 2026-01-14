-- Migration: Create refresh_logs table for queue-based refresh system
-- Run this on the production database

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
