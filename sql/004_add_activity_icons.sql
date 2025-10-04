-- ===================================================================
-- Add new icons to activity_icon enum
-- ===================================================================

-- Add new icon values to the existing enum
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'plus';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'minus';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'refresh';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'search';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'filter';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'save';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'copy';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'paste';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'cut';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'file';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'folder';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'lock';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'unlock';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'key';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'shield';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'bell';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'mail';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'phone';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'calendar';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'clock';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'chart';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'graph';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'question';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'check';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'close';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'menu';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'more';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'link';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'external';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'home';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'star';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'heart';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'eye';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'eye_off';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'trash';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'archive';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'pin';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'flag';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'tag';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'bookmark';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'wifi';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'wifi_off';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'network';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'server';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'cloud';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'cloud_upload';
ALTER TYPE activity_icon ADD VALUE IF NOT EXISTS 'cloud_download';

-- ===================================================================
-- Icons added successfully
-- Total icons: 61
-- ===================================================================
