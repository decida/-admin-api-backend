-- ============================================================================
-- MIGRATION: Add Execution Chain Support to API Resources
-- ============================================================================
-- Description: Adds execution_chain column to support sequential execution
--              of multiple business objects with parameter mapping
-- Date: 2025-10-22
-- Author: Claude Code
-- ============================================================================

-- Start transaction
BEGIN;

-- Add execution_chain column to api_resources table
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

        RAISE NOTICE '✓ Column execution_chain added to api_resources table';
    ELSE
        RAISE NOTICE '⚠ Column execution_chain already exists in api_resources table - skipping';
    END IF;
END $$;

-- Add comment to document the column purpose
COMMENT ON COLUMN api_resources.execution_chain IS
'JSON array containing the sequential chain of business objects to execute.
Each element contains:
- businessObjectId (UUID): ID of the business object to execute
- businessObjectName (string): Name of the business object
- businessObjectType (string): Type of command (select, insert, update, delete)
- businessObjectParams (array): Parameter definitions
- order (integer): Execution order (1-based, sequential)
- parameterMappings (array): Parameter mappings for this step
  - parameterName (string): Name of the parameter
  - sourceType (string): "static" or "variable"
  - staticValue (any): Static value if sourceType is "static"
  - variableSource (object): Variable source if sourceType is "variable"
    - stepIndex (integer): Index of the step to get value from (0-based)
    - fieldName (string): Name of the field in the step result

Example:
[
  {
    "businessObjectId": "uuid-1",
    "businessObjectName": "Query Cliente",
    "businessObjectType": "select",
    "businessObjectParams": [{"name": "id", "type": "number", "required": true}],
    "order": 1,
    "parameterMappings": []
  },
  {
    "businessObjectId": "uuid-2",
    "businessObjectName": "Insert Log",
    "businessObjectType": "insert",
    "businessObjectParams": [{"name": "clienteId", "type": "number", "required": true}],
    "order": 2,
    "parameterMappings": [
      {
        "parameterName": "clienteId",
        "sourceType": "variable",
        "staticValue": "",
        "variableSource": {"stepIndex": 0, "fieldName": "id"}
      }
    ]
  }
]';

-- Commit transaction
COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify column was created
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'api_resources'
AND column_name = 'execution_chain';

-- Count existing api_resources (should all have execution_chain = NULL initially)
SELECT
    COUNT(*) as total_resources,
    COUNT(execution_chain) as resources_with_chain,
    COUNT(*) - COUNT(execution_chain) as resources_without_chain
FROM api_resources;

-- Show sample of api_resources with new column
SELECT
    id,
    path,
    method,
    is_active,
    business_object_name,
    execution_chain IS NOT NULL as has_execution_chain,
    created_at
FROM api_resources
ORDER BY created_at DESC
LIMIT 5;

-- ============================================================================
-- ROLLBACK SCRIPT (Use only if you need to revert the migration)
-- ============================================================================
-- To rollback this migration, run:
-- BEGIN;
-- ALTER TABLE api_resources DROP COLUMN IF EXISTS execution_chain;
-- COMMIT;
--
-- WARNING: This will permanently delete all execution_chain data!
-- ============================================================================

-- Print success message
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '✓ MIGRATION COMPLETED SUCCESSFULLY';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'The execution_chain column has been added to the api_resources table.';
    RAISE NOTICE 'All existing resources have execution_chain = NULL (legacy mode).';
    RAISE NOTICE 'New resources can now use the execution chain feature.';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Restart your application';
    RAISE NOTICE '2. Test that existing resources still work';
    RAISE NOTICE '3. Create a new resource with execution chain';
    RAISE NOTICE '============================================================================';
END $$;
