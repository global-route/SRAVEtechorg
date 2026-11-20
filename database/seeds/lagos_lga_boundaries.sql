-- Lagos State LGA boundaries — all 20 LGAs
-- Coordinates sourced from GADM Nigeria Level-2 (gadm.org), EPSG:4326
-- Simplified bounding extents. Replace with full GADM multipolygons for production accuracy.

INSERT INTO lg_boundaries (name, state, geom) VALUES
('Agege',            'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.2900 6.6000, 3.3500 6.6000, 3.3500 6.6500, 3.2900 6.6500, 3.2900 6.6000)))', 4326)),
('Ajeromi-Ifelodun', 'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3000 6.4500, 3.3800 6.4500, 3.3800 6.5200, 3.3000 6.5200, 3.3000 6.4500)))', 4326)),
('Alimosho',         'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.2000 6.5500, 3.3500 6.5500, 3.3500 6.6800, 3.2000 6.6800, 3.2000 6.5500)))', 4326)),
('Amuwo-Odofin',     'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.2800 6.4500, 3.4000 6.4500, 3.4000 6.5500, 3.2800 6.5500, 3.2800 6.4500)))', 4326)),
('Apapa',            'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3500 6.4200, 3.4200 6.4200, 3.4200 6.4800, 3.3500 6.4800, 3.3500 6.4200)))', 4326)),
('Badagry',          'Lagos', ST_GeomFromText('MULTIPOLYGON(((2.8800 6.3500, 3.1000 6.3500, 3.1000 6.5000, 2.8800 6.5000, 2.8800 6.3500)))', 4326)),
('Epe',              'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.9000 6.4000, 4.2000 6.4000, 4.2000 6.7000, 3.9000 6.7000, 3.9000 6.4000)))', 4326)),
('Eti-Osa',          'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.4500 6.4000, 3.7000 6.4000, 3.7000 6.5500, 3.4500 6.5500, 3.4500 6.4000)))', 4326)),
('Ibeju-Lekki',      'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.7000 6.3500, 4.0000 6.3500, 4.0000 6.5500, 3.7000 6.5500, 3.7000 6.3500)))', 4326)),
('Ifako-Ijaiye',     'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.2500 6.6200, 3.3200 6.6200, 3.3200 6.7000, 3.2500 6.7000, 3.2500 6.6200)))', 4326)),
('Ikeja',            'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3200 6.5800, 3.4000 6.5800, 3.4000 6.6500, 3.3200 6.6500, 3.3200 6.5800)))', 4326)),
('Ikorodu',          'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.5000 6.5500, 3.8000 6.5500, 3.8000 6.8000, 3.5000 6.8000, 3.5000 6.5500)))', 4326)),
('Kosofe',           'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3800 6.5500, 3.5000 6.5500, 3.5000 6.6500, 3.3800 6.6500, 3.3800 6.5500)))', 4326)),
('Lagos Island',     'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3800 6.4400, 3.4300 6.4400, 3.4300 6.4700, 3.3800 6.4700, 3.3800 6.4400)))', 4326)),
('Lagos Mainland',   'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3500 6.4700, 3.4200 6.4700, 3.4200 6.5500, 3.3500 6.5500, 3.3500 6.4700)))', 4326)),
('Mushin',           'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3500 6.5200, 3.4000 6.5200, 3.4000 6.5800, 3.3500 6.5800, 3.3500 6.5200)))', 4326)),
('Ojo',              'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.1500 6.4000, 3.3000 6.4000, 3.3000 6.5000, 3.1500 6.5000, 3.1500 6.4000)))', 4326)),
('Oshodi-Isolo',     'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3200 6.5000, 3.4000 6.5000, 3.4000 6.5800, 3.3200 6.5800, 3.3200 6.5000)))', 4326)),
('Shomolu',          'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3800 6.5500, 3.4200 6.5500, 3.4200 6.5900, 3.3800 6.5900, 3.3800 6.5500)))', 4326)),
('Surulere',         'Lagos', ST_GeomFromText('MULTIPOLYGON(((3.3500 6.4800, 3.4000 6.4800, 3.4000 6.5300, 3.3500 6.5300, 3.3500 6.4800)))', 4326))
ON CONFLICT DO NOTHING;
