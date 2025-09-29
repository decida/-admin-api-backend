-- Script to drop all tables and types (use with caution!)

-- Drop trigger
DROP TRIGGER IF EXISTS update_databases_updated_at ON databases;

-- Drop function
DROP FUNCTION IF EXISTS update_updated_at_column();

-- Drop tables
DROP TABLE IF EXISTS databases CASCADE;

-- Drop enum types
DROP TYPE IF EXISTS database_status;