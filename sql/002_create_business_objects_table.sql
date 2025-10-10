-- Create command_type enum type
DO $$ BEGIN
    CREATE TYPE command_type AS ENUM ('select', 'insert', 'update', 'delete');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create business_objects table
CREATE TABLE IF NOT EXISTS business_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    command_type command_type NOT NULL,
    sql_command TEXT NOT NULL,
    tags JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create index on id
CREATE INDEX IF NOT EXISTS ix_business_objects_id ON business_objects(id);

-- Create index on name for faster search
CREATE INDEX IF NOT EXISTS ix_business_objects_name ON business_objects(name);

-- Create GIN index on tags for JSON queries
CREATE INDEX IF NOT EXISTS ix_business_objects_tags ON business_objects USING GIN (tags);

-- Create trigger to auto-update updated_at (reuse existing function)
CREATE TRIGGER update_business_objects_updated_at
    BEFORE UPDATE ON business_objects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
