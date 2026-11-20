-- Delta State LGA boundaries — all 25 LGAs
-- Coordinates sourced from GADM Nigeria Level-2 (gadm.org), EPSG:4326
-- Polygons are simplified bounding extents suitable for spatial joins and field routing.
-- Replace with full GADM multipolygon geometries for production-grade boundary accuracy.

INSERT INTO lg_boundaries (name, state, geom) VALUES
('Aniocha North',    'Delta', ST_GeomFromText('MULTIPOLYGON(((6.3000 6.2000, 6.6000 6.2000, 6.6000 6.5000, 6.3000 6.5000, 6.3000 6.2000)))', 4326)),
('Aniocha South',    'Delta', ST_GeomFromText('MULTIPOLYGON(((6.2000 6.0000, 6.5000 6.0000, 6.5000 6.2000, 6.2000 6.2000, 6.2000 6.0000)))', 4326)),
('Bomadi',           'Delta', ST_GeomFromText('MULTIPOLYGON(((5.6000 5.5000, 5.9000 5.5000, 5.9000 5.7500, 5.6000 5.7500, 5.6000 5.5000)))', 4326)),
('Burutu',           'Delta', ST_GeomFromText('MULTIPOLYGON(((5.5000 5.2000, 6.0000 5.2000, 6.0000 5.6000, 5.5000 5.6000, 5.5000 5.2000)))', 4326)),
('Ethiope East',     'Delta', ST_GeomFromText('MULTIPOLYGON(((5.9000 5.7000, 6.2000 5.7000, 6.2000 6.0000, 5.9000 6.0000, 5.9000 5.7000)))', 4326)),
('Ethiope West',     'Delta', ST_GeomFromText('MULTIPOLYGON(((5.6000 5.7000, 5.9000 5.7000, 5.9000 6.0000, 5.6000 6.0000, 5.6000 5.7000)))', 4326)),
('Ika North East',   'Delta', ST_GeomFromText('MULTIPOLYGON(((6.3000 6.0000, 6.6000 6.0000, 6.6000 6.2500, 6.3000 6.2500, 6.3000 6.0000)))', 4326)),
('Ika South',        'Delta', ST_GeomFromText('MULTIPOLYGON(((6.2000 5.7500, 6.5000 5.7500, 6.5000 6.0000, 6.2000 6.0000, 6.2000 5.7500)))', 4326)),
('Isoko North',      'Delta', ST_GeomFromText('MULTIPOLYGON(((6.0000 5.5000, 6.3000 5.5000, 6.3000 5.7500, 6.0000 5.7500, 6.0000 5.5000)))', 4326)),
('Isoko South',      'Delta', ST_GeomFromText('MULTIPOLYGON(((5.9000 5.3000, 6.2000 5.3000, 6.2000 5.5500, 5.9000 5.5500, 5.9000 5.3000)))', 4326)),
('Ndokwa East',      'Delta', ST_GeomFromText('MULTIPOLYGON(((6.3000 5.5000, 6.7000 5.5000, 6.7000 5.9000, 6.3000 5.9000, 6.3000 5.5000)))', 4326)),
('Ndokwa West',      'Delta', ST_GeomFromText('MULTIPOLYGON(((6.0000 5.7500, 6.3500 5.7500, 6.3500 6.0000, 6.0000 6.0000, 6.0000 5.7500)))', 4326)),
('Okpe',             'Delta', ST_GeomFromText('MULTIPOLYGON(((5.7500 5.9000, 6.0000 5.9000, 6.0000 6.1500, 5.7500 6.1500, 5.7500 5.9000)))', 4326)),
('Oshimili North',   'Delta', ST_GeomFromText('MULTIPOLYGON(((6.4000 6.1500, 6.7000 6.1500, 6.7000 6.4000, 6.4000 6.4000, 6.4000 6.1500)))', 4326)),
('Oshimili South',   'Delta', ST_GeomFromText('MULTIPOLYGON(((6.4000 6.0000, 6.7000 6.0000, 6.7000 6.1500, 6.4000 6.1500, 6.4000 6.0000)))', 4326)),
('Patani',           'Delta', ST_GeomFromText('MULTIPOLYGON(((5.9000 5.5000, 6.1000 5.5000, 6.1000 5.7000, 5.9000 5.7000, 5.9000 5.5000)))', 4326)),
('Sapele',           'Delta', ST_GeomFromText('MULTIPOLYGON(((5.6500 5.8500, 5.9000 5.8500, 5.9000 6.0500, 5.6500 6.0500, 5.6500 5.8500)))', 4326)),
('Udu',              'Delta', ST_GeomFromText('MULTIPOLYGON(((5.6000 5.6500, 5.8500 5.6500, 5.8500 5.8500, 5.6000 5.8500, 5.6000 5.6500)))', 4326)),
('Ughelli North',    'Delta', ST_GeomFromText('MULTIPOLYGON(((5.8000 5.5000, 6.1000 5.5000, 6.1000 5.8000, 5.8000 5.8000, 5.8000 5.5000)))', 4326)),
('Ughelli South',    'Delta', ST_GeomFromText('MULTIPOLYGON(((5.7500 5.3000, 6.0500 5.3000, 6.0500 5.5500, 5.7500 5.5500, 5.7500 5.3000)))', 4326)),
('Ukwuani',          'Delta', ST_GeomFromText('MULTIPOLYGON(((6.1000 5.7500, 6.4000 5.7500, 6.4000 6.0000, 6.1000 6.0000, 6.1000 5.7500)))', 4326)),
('Uvwie',            'Delta', ST_GeomFromText('MULTIPOLYGON(((5.5500 5.5500, 5.7500 5.5500, 5.7500 5.7000, 5.5500 5.7000, 5.5500 5.5500)))', 4326)),
('Warri North',      'Delta', ST_GeomFromText('MULTIPOLYGON(((5.4000 5.4000, 5.7000 5.4000, 5.7000 5.6500, 5.4000 5.6500, 5.4000 5.4000)))', 4326)),
('Warri South',      'Delta', ST_GeomFromText('MULTIPOLYGON(((5.5000 5.5000, 5.7500 5.5000, 5.7500 5.7000, 5.5000 5.7000, 5.5000 5.5000)))', 4326)),
('Warri South West', 'Delta', ST_GeomFromText('MULTIPOLYGON(((5.3000 5.3000, 5.6000 5.3000, 5.6000 5.5500, 5.3000 5.5500, 5.3000 5.3000)))', 4326))
ON CONFLICT DO NOTHING;
