-- Sample LGA boundaries for development/testing
INSERT INTO lg_boundaries (name, state, geom) VALUES
(
  'Abeokuta South',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.3792 6.5244, 3.4000 6.5244, 3.4000 6.5500, 3.3792 6.5500, 3.3792 6.5244)))', 4326)
),
(
  'Warri South',
  'Delta',
  ST_GeomFromText('MULTIPOLYGON(((5.7200 5.5100, 5.7600 5.5100, 5.7600 5.5500, 5.7200 5.5500, 5.7200 5.5100)))', 4326)
);
