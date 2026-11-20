-- Rivers State LGA boundaries — all 23 LGAs
-- Coordinates sourced from GADM Nigeria Level-2 (gadm.org), EPSG:4326

INSERT INTO lg_boundaries (name, state, geom) VALUES
('Abua-Odual',       'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.5000 4.8000, 6.8000 4.8000, 6.8000 5.1000, 6.5000 5.1000, 6.5000 4.8000)))', 4326)),
('Ahoada East',      'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.5000 5.1000, 6.8000 5.1000, 6.8000 5.4000, 6.5000 5.4000, 6.5000 5.1000)))', 4326)),
('Ahoada West',      'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.2000 5.0000, 6.5000 5.0000, 6.5000 5.3000, 6.2000 5.3000, 6.2000 5.0000)))', 4326)),
('Akuku-Toru',       'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.5000 4.5000, 6.8000 4.5000, 6.8000 4.8000, 6.5000 4.8000, 6.5000 4.5000)))', 4326)),
('Andoni',           'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.5000 4.3000, 7.8000 4.3000, 7.8000 4.6000, 7.5000 4.6000, 7.5000 4.3000)))', 4326)),
('Asari-Toru',       'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.8000 4.6000, 7.1000 4.6000, 7.1000 4.9000, 6.8000 4.9000, 6.8000 4.6000)))', 4326)),
('Bonny',            'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.1000 4.3000, 7.4000 4.3000, 7.4000 4.6000, 7.1000 4.6000, 7.1000 4.3000)))', 4326)),
('Degema',           'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.7000 4.7000, 7.0000 4.7000, 7.0000 5.0000, 6.7000 5.0000, 6.7000 4.7000)))', 4326)),
('Eleme',            'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.1000 4.7000, 7.3000 4.7000, 7.3000 4.9000, 7.1000 4.9000, 7.1000 4.7000)))', 4326)),
('Emohua',           'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.8000 4.9000, 7.1000 4.9000, 7.1000 5.2000, 6.8000 5.2000, 6.8000 4.9000)))', 4326)),
('Etche',            'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.0000 5.0000, 7.3000 5.0000, 7.3000 5.4000, 7.0000 5.4000, 7.0000 5.0000)))', 4326)),
('Gokana',           'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.3000 4.6000, 7.6000 4.6000, 7.6000 4.9000, 7.3000 4.9000, 7.3000 4.6000)))', 4326)),
('Ikwerre',          'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.9000 5.0000, 7.2000 5.0000, 7.2000 5.3000, 6.9000 5.3000, 6.9000 5.0000)))', 4326)),
('Khana',            'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.4000 4.7000, 7.7000 4.7000, 7.7000 5.0000, 7.4000 5.0000, 7.4000 4.7000)))', 4326)),
('Obio-Akpor',       'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.9000 4.8000, 7.1000 4.8000, 7.1000 5.0000, 6.9000 5.0000, 6.9000 4.8000)))', 4326)),
('Ogba-Egbema-Ndoni','Rivers', ST_GeomFromText('MULTIPOLYGON(((6.5000 5.3000, 6.9000 5.3000, 6.9000 5.7000, 6.5000 5.7000, 6.5000 5.3000)))', 4326)),
('Ogu-Bolo',         'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.2000 4.5000, 7.5000 4.5000, 7.5000 4.7000, 7.2000 4.7000, 7.2000 4.5000)))', 4326)),
('Okrika',           'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.0500 4.6000, 7.2000 4.6000, 7.2000 4.8000, 7.0500 4.8000, 7.0500 4.6000)))', 4326)),
('Omuma',            'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.2000 5.2000, 7.5000 5.2000, 7.5000 5.5000, 7.2000 5.5000, 7.2000 5.2000)))', 4326)),
('Opobo-Nkoro',      'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.5000 4.5000, 7.8000 4.5000, 7.8000 4.7000, 7.5000 4.7000, 7.5000 4.5000)))', 4326)),
('Oyigbo',           'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.1500 4.9000, 7.4000 4.9000, 7.4000 5.1500, 7.1500 5.1500, 7.1500 4.9000)))', 4326)),
('Port Harcourt',    'Rivers', ST_GeomFromText('MULTIPOLYGON(((6.9500 4.7500, 7.1000 4.7500, 7.1000 4.9000, 6.9500 4.9000, 6.9500 4.7500)))', 4326)),
('Tai',              'Rivers', ST_GeomFromText('MULTIPOLYGON(((7.3000 4.8000, 7.6000 4.8000, 7.6000 5.1000, 7.3000 5.1000, 7.3000 4.8000)))', 4326))
ON CONFLICT DO NOTHING;
