-- Runs only on first DB init. Harmless on plain postgres (extension missing).
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS postgis;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'PostGIS not available — using GeoJSON text for plot.geom';
END $$;
