-- Add params column to business_objects table
ALTER TABLE business_objects
ADD COLUMN IF NOT EXISTS params JSONB DEFAULT '[]'::jsonb NOT NULL;

-- Create GIN index on params for JSON queries
CREATE INDEX IF NOT EXISTS ix_business_objects_params ON business_objects USING GIN (params);

-- Add comment to explain params structure
COMMENT ON COLUMN business_objects.params IS 'Array of parameter definitions with structure: [{name: string, type: string|number|date, required: boolean, defaultValue: any}]';
