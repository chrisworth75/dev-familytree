-- Test data for TreeDataServiceTest
-- Real Worthington family data
--
-- Structure:
--     Constance Mary Wrathall (4005) ─┬─ Arthur Goodall (4004)
--                                     │
--         ┌───────────────────────────┴───────────────────────────┐
--         │                                                       │
--     Arthur Gordon (3002) ─┬─ Marjorie (3003)               Bryan (31)
--                           │
--     ┌───────────┬─────────┴─────────┬───────────┐
--     │           │                   │           │
-- Jonathan (2001) Rosalind (2002) David (2003) Tony (2004)
--     │
-- ┌───┴───┬───────────┬───────────┐
-- │       │           │           │
-- Tim  Chris(1000)  Rebecca   Jennifer
--      ─┬─ Sarah              ─┬─
--       │                      │
--   ┌───┴───┐             ┌────┴────┐
-- Hugo   Zachary        Joe     Grace

-- Tree
INSERT INTO tree (id, name, slug) VALUES (1, 'Worthington Family', 'worthington-family');
INSERT INTO tree (id, name, slug) VALUES (2, 'Unrelated Family', 'unrelated-family');

-- Generation 1: Constance's parents (stubs for FK integrity)
INSERT INTO person (id, first_name, surname, gender, tree_id)
VALUES (575341, 'Henry', 'Wrathall', 'M', 1);

INSERT INTO person (id, first_name, surname, gender, tree_id)
VALUES (511037, 'Mary Alice', 'Wrathall', 'F', 1);

-- Generation 2: Constance and Arthur Goodall
INSERT INTO person (id, first_name, middle_names, surname, birth_surname, gender, father_id, mother_id, tree_id, notes)
VALUES (4005, 'Constance', 'Mary', 'Worthington', 'Wrathall', 'F', 575341, 511037, 1, NULL);

INSERT INTO person (id, first_name, middle_names, surname, gender, tree_id)
VALUES (4004, 'Arthur', 'Goodall', 'Worthington', 'M', 1);

-- Generation 3: Arthur Gordon and Bryan
INSERT INTO person (id, first_name, middle_names, surname, gender, father_id, mother_id, tree_id)
VALUES (3002, 'Arthur', 'Gordon Lonsdale', 'Worthington', 'M', 4004, 4005, 1);

INSERT INTO person (id, first_name, surname, gender, father_id, mother_id, tree_id, notes)
VALUES (31, 'Bryan', 'Worthington', 'M', 4004, 4005, 1, 'Younger son of Arthur Goodall Worthington and Constance.');

-- Spouse for Arthur Gordon
INSERT INTO person (id, first_name, surname, gender, tree_id)
VALUES (3003, 'Marjorie', 'Worthington', 'F', 1);

-- Generation 4: Jonathan, Rosalind, David, Tony
INSERT INTO person (id, first_name, middle_names, surname, gender, father_id, mother_id, tree_id)
VALUES (2001, 'Jonathan', 'P', 'Worthington', 'M', 3002, 3003, 1);

INSERT INTO person (id, first_name, surname, gender, father_id, mother_id, tree_id)
VALUES (2002, 'Rosalind', 'Worthington', 'F', 3002, 3003, 1);

INSERT INTO person (id, first_name, surname, gender, father_id, mother_id, tree_id)
VALUES (2003, 'David', 'Worthington', 'M', 3002, 3003, 1);

INSERT INTO person (id, first_name, surname, gender, father_id, mother_id, tree_id)
VALUES (2004, 'Tony', 'Worthington', 'M', 3002, 3003, 1);

-- Spouse for Jonathan
INSERT INTO person (id, first_name, surname, gender, tree_id)
VALUES (2000, 'Patricia', 'Worthington', 'F', 1);

-- Generation 5: Tim, Chris, Rebecca, Jennifer (Jonathan's children)
INSERT INTO person (id, first_name, middle_names, surname, gender, birth_date, father_id, mother_id, tree_id)
VALUES (1001, 'Timothy', 'Jonathon Patrick', 'Worthington', 'M', '1974-02-12', 2001, 2000, 1);

INSERT INTO person (id, first_name, surname, gender, birth_date, father_id, mother_id, tree_id, avatar_path)
VALUES (1000, 'Chris', 'Worthington', 'M', '1975-09-30', 2001, 2000, 1, 'avatars/chris.jpg');

INSERT INTO person (id, first_name, surname, gender, birth_date, father_id, mother_id, tree_id)
VALUES (1002, 'Rebecca', 'Worthington', 'F', '1978-05-03', 2001, 2000, 1);

INSERT INTO person (id, first_name, middle_names, surname, gender, birth_date, father_id, mother_id, tree_id)
VALUES (1003, 'Jennifer', 'Clare', 'Worthington', 'F', '1982-02-02', 2001, 2000, 1);

-- Generation 5: Rosalind's children
INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (900200, 'Bruce', 'Worthington', 'M', 2002, 1);

INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (900201, 'Stuart', 'Worthington', 'M', 2002, 1);

-- Generation 5: David's children
INSERT INTO person (id, first_name, surname, gender, father_id, tree_id)
VALUES (900205, 'Nick', 'Worthington', 'M', 2003, 1);

INSERT INTO person (id, first_name, surname, gender, father_id, tree_id)
VALUES (900206, 'Natalie', 'Worthington', 'F', 2003, 1);

-- Generation 5: Tony's children
INSERT INTO person (id, first_name, surname, gender, father_id, tree_id)
VALUES (900211, 'Emma', 'Worthington', 'F', 2004, 1);

INSERT INTO person (id, first_name, surname, gender, father_id, tree_id)
VALUES (900212, 'Laura', 'Worthington', 'F', 2004, 1);

-- Spouse for Chris
INSERT INTO person (id, first_name, surname, gender, tree_id)
VALUES (1004, 'Sarah', 'Worthington', 'F', 1);

-- Generation 6: Chris's children
INSERT INTO person (id, first_name, surname, gender, birth_date, father_id, mother_id, tree_id)
VALUES (100, 'Hugo', 'Worthington', 'M', '2016-06-01', 1000, 1004, 1);

INSERT INTO person (id, first_name, surname, gender, birth_date, father_id, mother_id, tree_id)
VALUES (101, 'Zachary', 'Worthington', 'M', '2019-06-03', 1000, 1004, 1);

-- Generation 6: Jennifer's children
INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (400, 'Joe', 'Hyndman', 'M', 1003, 1);

INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (401, 'Grace', 'Hyndman', 'F', 1003, 1);

-- Generation 6: Bruce's children
INSERT INTO person (id, first_name, surname, gender, father_id, tree_id)
VALUES (900202, 'Caitlyn', 'Worthington', 'F', 900200, 1);

-- Generation 6: Stuart's children
INSERT INTO person (id, first_name, surname, gender, father_id, tree_id)
VALUES (900203, 'Jack', 'Worthington', 'M', 900201, 1);

INSERT INTO person (id, first_name, surname, gender, father_id, tree_id)
VALUES (900204, 'James', 'Worthington', 'M', 900201, 1);

-- Generation 6: Nick's children
INSERT INTO person (id, first_name, surname, gender, father_id, tree_id)
VALUES (900207, 'Josh', 'Worthington', 'M', 900205, 1);

-- Generation 6: Natalie's children
INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (900208, 'Toby', 'Yates', 'M', 900206, 1);

INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (900209, 'Libby', 'Yates', 'F', 900206, 1);

-- Generation 6: Emma's children
INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (900213, 'Ollie', 'Unknown', 'M', 900211, 1);

-- Generation 6: Laura's children
INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (900214, 'Millie', 'Unknown', 'F', 900212, 1);

-- Generation 7: Libby's children
INSERT INTO person (id, first_name, surname, gender, mother_id, tree_id)
VALUES (900210, 'Reggie', 'Unknown', 'M', 900209, 1);

-- Partnerships (marriages)
INSERT INTO partnership (id, person_1_id, person_2_id) VALUES (1, 4004, 4005);  -- Arthur Goodall & Constance
INSERT INTO partnership (id, person_1_id, person_2_id) VALUES (2, 3002, 3003);  -- Arthur Gordon & Marjorie
INSERT INTO partnership (id, person_1_id, person_2_id) VALUES (3, 2000, 2001);  -- Patricia & Jonathan
INSERT INTO partnership (id, person_1_id, person_2_id) VALUES (4, 1000, 1004);  -- Chris & Sarah

-- Unrelated family (for no-common-ancestor tests)
INSERT INTO person (id, first_name, surname, gender, tree_id)
VALUES (99001, 'Frank', 'Unrelated', 'M', 2);

INSERT INTO person (id, first_name, surname, gender, tree_id)
VALUES (99002, 'Grace', 'Unrelated', 'F', 2);

-- Special test case: null gender
INSERT INTO person (id, first_name, surname, gender, tree_id)
VALUES (99003, 'Pat', 'Unknown', NULL, 1);