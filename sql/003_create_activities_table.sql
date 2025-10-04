-- ===================================================================
-- Activities/Audit Log Table
-- Stores user activities and system events for audit trail
-- ===================================================================

-- Create activity_icon enum type
DO $$ BEGIN
    CREATE TYPE activity_icon AS ENUM (
        'database', 'edit', 'delete', 'add', 'plus', 'minus',
        'user', 'settings', 'upload', 'download', 'sync', 'refresh',
        'search', 'filter', 'save', 'copy', 'paste', 'cut',
        'file', 'folder', 'lock', 'unlock', 'key', 'shield',
        'bell', 'mail', 'phone', 'calendar', 'clock',
        'chart', 'graph', 'warning', 'error', 'success', 'info',
        'question', 'check', 'close', 'menu', 'more',
        'link', 'external', 'home', 'star', 'heart',
        'eye', 'eye_off', 'trash', 'archive', 'pin',
        'flag', 'tag', 'bookmark', 'wifi', 'wifi_off',
        'network', 'server', 'cloud', 'cloud_upload', 'cloud_download'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create activity_color enum type
DO $$ BEGIN
    CREATE TYPE activity_color AS ENUM (
        'blue',
        'green',
        'red',
        'yellow',
        'purple',
        'orange',
        'gray',
        'indigo',
        'pink'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create activities table
CREATE TABLE IF NOT EXISTS activities (
    id BIGSERIAL PRIMARY KEY,
    action VARCHAR(255) NOT NULL,
    item VARCHAR(500) NOT NULL,
    icon activity_icon NOT NULL DEFAULT 'info',
    color activity_color NOT NULL DEFAULT 'blue',
    user_email VARCHAR(255),
    user_id UUID,
    extra_data JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_activities_timestamp ON activities(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_activities_user_email ON activities(user_email);
CREATE INDEX IF NOT EXISTS idx_activities_user_id ON activities(user_id);
CREATE INDEX IF NOT EXISTS idx_activities_action ON activities(action);
CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at DESC);

-- Create GIN index for JSONB extra_data search
CREATE INDEX IF NOT EXISTS idx_activities_extra_data ON activities USING GIN (extra_data);

-- Add comments for documentation
COMMENT ON TABLE activities IS 'Audit log table storing all user activities and system events';
COMMENT ON COLUMN activities.id IS 'Auto-incrementing primary key';
COMMENT ON COLUMN activities.action IS 'Description of the action performed (e.g., "Created database", "Updated connection")';
COMMENT ON COLUMN activities.item IS 'Item affected by the action (e.g., database name, user name)';
COMMENT ON COLUMN activities.icon IS 'Icon identifier for UI display';
COMMENT ON COLUMN activities.color IS 'Color theme for the activity in UI';
COMMENT ON COLUMN activities.user_email IS 'Email of the user who performed the action';
COMMENT ON COLUMN activities.user_id IS 'UUID of the user (if authenticated)';
COMMENT ON COLUMN activities.extra_data IS 'Additional JSON data about the activity';
COMMENT ON COLUMN activities.ip_address IS 'IP address of the request';
COMMENT ON COLUMN activities.user_agent IS 'Browser/client user agent string';
COMMENT ON COLUMN activities.timestamp IS 'When the activity occurred';
COMMENT ON COLUMN activities.created_at IS 'When the record was created in the database';

-- Example insert
INSERT INTO activities (action, item, icon, color, user_email, extra_data)
VALUES
    ('Created database connection', 'Production DB', 'database', 'blue', 'user@example.com', '{"database_type": "sqlserver", "status": "active"}'),
    ('Updated connection settings', 'Production DB', 'edit', 'green', 'user@example.com', '{"fields_changed": ["connection_string", "description"]}'),
    ('Deleted database connection', 'Test DB', 'delete', 'red', 'admin@example.com', '{"reason": "no longer needed"}')
ON CONFLICT DO NOTHING;

-- ===================================================================
-- Table created successfully
-- ===================================================================
