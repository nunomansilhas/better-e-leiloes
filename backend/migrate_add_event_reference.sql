-- Add event_reference column to notification_rules table
ALTER TABLE notification_rules 
ADD COLUMN event_reference VARCHAR(50) NULL AFTER minutos_restantes;
