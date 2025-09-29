-- Create database_status enum type
DO $$ BEGIN
    CREATE TYPE database_status AS ENUM ('active', 'inactive');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create databases table
CREATE TABLE IF NOT EXISTS databases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    connection_string TEXT NOT NULL,
    description TEXT,
    status database_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create index on id
CREATE INDEX IF NOT EXISTS ix_databases_id ON databases(id);

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_databases_updated_at
    BEFORE UPDATE ON databases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();