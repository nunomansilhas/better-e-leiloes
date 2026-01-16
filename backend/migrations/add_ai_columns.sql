-- Migration: Add AI analysis columns to event_vehicle_data table
-- Run this SQL on your MySQL database to add the new AI analysis columns

ALTER TABLE event_vehicle_data
ADD COLUMN ai_score FLOAT NULL,
ADD COLUMN ai_recommendation VARCHAR(50) NULL,
ADD COLUMN ai_summary TEXT NULL,
ADD COLUMN ai_pros TEXT NULL,
ADD COLUMN ai_cons TEXT NULL,
ADD COLUMN ai_questions_results TEXT NULL,
ADD COLUMN ai_image_analyses TEXT NULL,
ADD COLUMN ai_model_used VARCHAR(100) NULL,
ADD COLUMN ai_tokens_used INT NULL,
ADD COLUMN ai_processing_time_ms INT NULL;

-- Verify the columns were added
DESCRIBE event_vehicle_data;
