-- Create notification_rules table
CREATE TABLE IF NOT EXISTS notification_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,  -- 'new_event', 'price_change', 'ending_soon', 'event_specific'
    active BOOLEAN DEFAULT TRUE,

    -- For event-specific rules
    event_reference VARCHAR(50) NULL,

    -- Filters (comma-separated)
    tipos VARCHAR(100) NULL,  -- e.g., "1,2,3"
    distritos VARCHAR(500) NULL,  -- e.g., "Lisboa,Porto"
    preco_min FLOAT NULL,
    preco_max FLOAT NULL,

    -- Tracking
    last_price FLOAT NULL,  -- For price change tracking
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NULL,

    INDEX idx_event_reference (event_reference)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rule_id INT NULL,  -- Link to rule that triggered it
    notification_type VARCHAR(50) NOT NULL,  -- 'new_event', 'price_change', 'ending_soon'

    -- Event info
    event_reference VARCHAR(50) NOT NULL,
    event_titulo VARCHAR(500) NULL,
    event_tipo VARCHAR(100) NULL,
    event_subtipo VARCHAR(100) NULL,
    event_distrito VARCHAR(100) NULL,

    -- Price info (for price_change notifications)
    preco_anterior FLOAT NULL,
    preco_atual FLOAT NULL,

    -- State
    `read` BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_event_reference (event_reference),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
