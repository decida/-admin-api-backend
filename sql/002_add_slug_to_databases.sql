-- Add slug column to databases table
ALTER TABLE databases
ADD COLUMN IF NOT EXISTS slug VARCHAR(255) UNIQUE;

-- Create unique index on slug
CREATE UNIQUE INDEX IF NOT EXISTS ix_databases_slug ON databases(slug);

-- Function to generate slug from name
CREATE OR REPLACE FUNCTION generate_slug(name TEXT)
RETURNS TEXT AS $$
DECLARE
    slug TEXT;
BEGIN
    -- Convert to lowercase, replace spaces and special chars with hyphens
    slug := lower(regexp_replace(name, '[^a-zA-Z0-9]+', '-', 'g'));
    -- Remove leading/trailing hyphens
    slug := trim(both '-' from slug);
    RETURN slug;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Populate slug for existing records (if any)
DO $$
DECLARE
    rec RECORD;
    base_slug TEXT;
    final_slug TEXT;
    counter INTEGER;
BEGIN
    FOR rec IN SELECT id, name FROM databases WHERE slug IS NULL LOOP
        base_slug := generate_slug(rec.name);
        final_slug := base_slug;
        counter := 1;

        -- Check if slug exists and add counter if needed
        WHILE EXISTS (SELECT 1 FROM databases WHERE slug = final_slug AND id != rec.id) LOOP
            final_slug := base_slug || '-' || counter;
            counter := counter + 1;
        END LOOP;

        UPDATE databases SET slug = final_slug WHERE id = rec.id;
    END LOOP;
END $$;

-- Make slug NOT NULL after populating existing records
ALTER TABLE databases
ALTER COLUMN slug SET NOT NULL;
