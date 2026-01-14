-- Migration 004: Add performance indexes
-- Run this on MySQL/MariaDB to improve query performance

-- Composite index for active events queries (most common)
CREATE INDEX idx_events_active ON events(terminado, cancelado, data_fim);

-- Index for filtering by type
CREATE INDEX idx_events_tipo ON events(tipo_id);

-- Index for filtering by location
CREATE INDEX idx_events_distrito ON events(distrito);

-- Index for price history lookups
CREATE INDEX idx_price_history_ref_time ON price_history(reference, recorded_at DESC);

-- Index for refresh logs by state (for queue processing)
CREATE INDEX idx_refresh_logs_state ON refresh_logs(state, created_at);

-- Index for notifications by user
CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC);

-- Verify indexes were created
SHOW INDEX FROM events;
SHOW INDEX FROM price_history;
SHOW INDEX FROM refresh_logs;
