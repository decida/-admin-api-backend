-- Add execution_chain column to api_resources table
-- This column stores the sequential chain of business objects to execute

DO $$
BEGIN
    -- Check if column exists before adding
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'api_resources'
        AND column_name = 'execution_chain'
    ) THEN
        ALTER TABLE api_resources
        ADD COLUMN execution_chain JSONB DEFAULT NULL;

        RAISE NOTICE 'Column execution_chain added to api_resources table';
    ELSE
        RAISE NOTICE 'Column execution_chain already exists in api_resources table';
    END IF;
END $$;

-- Add comment to document the column purpose
COMMENT ON COLUMN api_resources.execution_chain IS
'JSON array containing the sequential chain of business objects to execute. Each element contains businessObjectId, businessObjectName, businessObjectType, businessObjectParams, order, and parameterMappings.';
