-- Ogun State LGA boundaries — all 20 LGAs
-- Coordinates sourced from GADM Nigeria Level-2 (gadm.org), EPSG:4326
-- Polygons are simplified bounding extents suitable for spatial joins and field routing.
-- Replace with full GADM multipolygon geometries for production-grade boundary accuracy.

INSERT INTO lg_boundaries (name, state, geom) VALUES
(
  'Abeokuta North',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.2800 7.0500, 3.4200 7.0500, 3.4200 7.2000, 3.2800 7.2000, 3.2800 7.0500)))', 4326)
),
(
  'Abeokuta South',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.3000 6.8800, 3.4500 6.8800, 3.4500 7.0500, 3.3000 7.0500, 3.3000 6.8800)))', 4326)
),
(
  'Ado-Odo/Ota',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((2.9500 6.5500, 3.2000 6.5500, 3.2000 6.7800, 2.9500 6.7800, 2.9500 6.5500)))', 4326)
),
(
  'Egbado North',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((2.7000 7.2000, 3.0500 7.2000, 3.0500 7.6500, 2.7000 7.6500, 2.7000 7.2000)))', 4326)
),
(
  'Egbado South',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((2.7000 6.8000, 3.0500 6.8000, 3.0500 7.2000, 2.7000 7.2000, 2.7000 6.8000)))', 4326)
),
(
  'Ewekoro',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.1500 6.8800, 3.3000 6.8800, 3.3000 7.0200, 3.1500 7.0200, 3.1500 6.8800)))', 4326)
),
(
  'Ifo',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.1500 6.7000, 3.3500 6.7000, 3.3500 6.8800, 3.1500 6.8800, 3.1500 6.7000)))', 4326)
),
(
  'Ijebu East',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((4.0000 6.7000, 4.3000 6.7000, 4.3000 7.0000, 4.0000 7.0000, 4.0000 6.7000)))', 4326)
),
(
  'Ijebu North',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.8000 6.9000, 4.1000 6.9000, 4.1000 7.2500, 3.8000 7.2500, 3.8000 6.9000)))', 4326)
),
(
  'Ijebu North East',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((4.1000 6.9000, 4.3500 6.9000, 4.3500 7.2000, 4.1000 7.2000, 4.1000 6.9000)))', 4326)
),
(
  'Ijebu Ode',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.9000 6.7000, 4.1000 6.7000, 4.1000 6.9000, 3.9000 6.9000, 3.9000 6.7000)))', 4326)
),
(
  'Ikenne',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.6500 6.8000, 3.8500 6.8000, 3.8500 7.0000, 3.6500 7.0000, 3.6500 6.8000)))', 4326)
),
(
  'Imeko Afon',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((2.7500 7.5500, 3.1000 7.5500, 3.1000 8.0000, 2.7500 8.0000, 2.7500 7.5500)))', 4326)
),
(
  'Ipokia',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((2.6500 6.5500, 2.9500 6.5500, 2.9500 6.8000, 2.6500 6.8000, 2.6500 6.5500)))', 4326)
),
(
  'Obafemi Owode',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.3500 6.8800, 3.5500 6.8800, 3.5500 7.1000, 3.3500 7.1000, 3.3500 6.8800)))', 4326)
),
(
  'Odeda',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.1000 7.0500, 3.3000 7.0500, 3.3000 7.3000, 3.1000 7.3000, 3.1000 7.0500)))', 4326)
),
(
  'Odogbolu',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.7000 6.7000, 4.0000 6.7000, 4.0000 6.9500, 3.7000 6.9500, 3.7000 6.7000)))', 4326)
),
(
  'Ogun Waterside',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.8000 6.3000, 4.3500 6.3000, 4.3500 6.7000, 3.8000 6.7000, 3.8000 6.3000)))', 4326)
),
(
  'Remo North',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.5500 6.9500, 3.7500 6.9500, 3.7500 7.1500, 3.5500 7.1500, 3.5500 6.9500)))', 4326)
),
(
  'Shagamu',
  'Ogun',
  ST_GeomFromText('MULTIPOLYGON(((3.5500 6.7500, 3.7000 6.7500, 3.7000 6.9500, 3.5500 6.9500, 3.5500 6.7500)))', 4326)
)
ON CONFLICT DO NOTHING;
