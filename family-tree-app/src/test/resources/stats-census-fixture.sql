-- Census fixture for StatsServiceTest. Loaded AFTER worthington-family.sql,
-- so the referenced people (3002, 4005, 1000) already exist.
--
--   Arthur Gordon Worthington (3002): 3 census records  -> rank #1
--   Constance Worthington     (4005): 2 census records  -> rank #2
--   Chris Worthington         (1000): 1 census record   -> rank #3
--
-- Chris also gets a non-census (probate) record to prove the query counts
-- only record_type = 'census'. Timothy (1001) gets none -> must not appear.

INSERT INTO source_record (id, record_type, title) VALUES (9001, 'census', '1881 Census');
INSERT INTO source_record (id, record_type, title) VALUES (9002, 'census', '1891 Census');
INSERT INTO source_record (id, record_type, title) VALUES (9003, 'census', '1901 Census');
INSERT INTO source_record (id, record_type, title) VALUES (9004, 'census', '1911 Census');
INSERT INTO source_record (id, record_type, title) VALUES (9005, 'census', '1921 Census');
INSERT INTO source_record (id, record_type, title) VALUES (9006, 'census', '1939 Register');
INSERT INTO source_record (id, record_type, title) VALUES (9100, 'probate', '1950 Probate');

INSERT INTO person_source (person_id, source_record_id, role) VALUES (3002, 9001, 'subject');
INSERT INTO person_source (person_id, source_record_id, role) VALUES (3002, 9002, 'subject');
INSERT INTO person_source (person_id, source_record_id, role) VALUES (3002, 9003, 'subject');
INSERT INTO person_source (person_id, source_record_id, role) VALUES (4005, 9004, 'subject');
INSERT INTO person_source (person_id, source_record_id, role) VALUES (4005, 9005, 'subject');
INSERT INTO person_source (person_id, source_record_id, role) VALUES (1000, 9006, 'subject');
INSERT INTO person_source (person_id, source_record_id, role) VALUES (1000, 9100, 'subject');
