-- Create api_resources table
CREATE TABLE IF NOT EXISTS api_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    path VARCHAR(500) NOT NULL UNIQUE,
    method VARCHAR(10) NOT NULL DEFAULT 'POST',
    description VARCHAR(1000),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Foreign key to business_objects
    business_object_id UUID NOT NULL,
    CONSTRAINT fk_api_resources_business_object
        FOREIGN KEY (business_object_id)
        REFERENCES business_objects(id)
        ON DELETE RESTRICT,

    -- Metadata snapshot from business object
    business_object_name VARCHAR(255) NOT NULL,
    business_object_params JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_api_resources_id ON api_resources(id);
CREATE INDEX IF NOT EXISTS ix_api_resources_path ON api_resources(path);
CREATE INDEX IF NOT EXISTS ix_api_resources_business_object_id ON api_resources(business_object_id);
CREATE INDEX IF NOT EXISTS ix_api_resources_is_active ON api_resources(is_active);

-- Create trigger to auto-update updated_at (reuse existing function)
CREATE TRIGGER update_api_resources_updated_at
    BEFORE UPDATE ON api_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
