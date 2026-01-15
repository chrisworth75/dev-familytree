-- Tree Query Helpers for Genealogy Database
-- Uses mother_id/father_id columns on person table
-- Max 7 levels deep, so multiple queries are fine

-- ============================================
-- DESCENDANTS (children, grandchildren, etc.)
-- ============================================

-- Get immediate children of a person
-- Usage: Replace :person_id with the parent's ID
SELECT id, forename, surname, birth_year_estimate, death_year_estimate
FROM person
WHERE mother_id = :person_id OR father_id = :person_id
ORDER BY birth_year_estimate;

-- Get all descendants up to 7 generations (iterative approach)
-- Level 1: Children
WITH RECURSIVE descendants AS (
    -- Base case: direct children
    SELECT id, forename, surname, birth_year_estimate, 1 as level
    FROM person
    WHERE mother_id = :root_id OR father_id = :root_id

    UNION ALL

    -- Recursive case: children of descendants
    SELECT p.id, p.forename, p.surname, p.birth_year_estimate, d.level + 1
    FROM person p
    JOIN descendants d ON p.mother_id = d.id OR p.father_id = d.id
    WHERE d.level < 7
)
SELECT * FROM descendants ORDER BY level, birth_year_estimate;


-- ============================================
-- ANCESTORS (parents, grandparents, etc.)
-- ============================================

-- Get parents of a person
SELECT id, forename, surname, birth_year_estimate,
       CASE WHEN id = (SELECT mother_id FROM person WHERE id = :person_id) THEN 'mother'
            WHEN id = (SELECT father_id FROM person WHERE id = :person_id) THEN 'father'
       END as relationship
FROM person
WHERE id IN (
    SELECT mother_id FROM person WHERE id = :person_id
    UNION
    SELECT father_id FROM person WHERE id = :person_id
);

-- Get all ancestors up to 7 generations
WITH RECURSIVE ancestors AS (
    -- Base case: parents
    SELECT p.id, p.forename, p.surname, p.birth_year_estimate, 1 as level
    FROM person p
    WHERE p.id IN (
        SELECT mother_id FROM person WHERE id = :person_id
        UNION
        SELECT father_id FROM person WHERE id = :person_id
    )

    UNION ALL

    -- Recursive case: parents of ancestors
    SELECT p.id, p.forename, p.surname, p.birth_year_estimate, a.level + 1
    FROM person p
    JOIN ancestors a ON p.id IN (
        SELECT mother_id FROM person WHERE id = a.id
        UNION
        SELECT father_id FROM person WHERE id = a.id
    )
    WHERE a.level < 7
)
SELECT * FROM ancestors ORDER BY level, birth_year_estimate;


-- ============================================
-- SPECIFIC TREE QUERIES
-- ============================================

-- HLW's direct children (for tree root)
SELECT id, forename, surname, birth_year_estimate
FROM person
WHERE forename LIKE '%Henry Lonsdale%' AND surname LIKE '%Wrathall%'
   OR (mother_id IS NOT NULL OR father_id IS NOT NULL)
      AND id IN (
        SELECT id FROM person
        WHERE (mother_id IN (SELECT id FROM person WHERE forename LIKE '%Henry Lonsdale%' AND surname LIKE '%Wrathall%')
           OR father_id IN (SELECT id FROM person WHERE forename LIKE '%Henry Lonsdale%' AND surname LIKE '%Wrathall%'))
      );

-- Find person by name
SELECT id, forename, surname, birth_year_estimate, death_year_estimate,
       mother_id, father_id
FROM person
WHERE forename LIKE '%' || :search_name || '%'
   OR surname LIKE '%' || :search_name || '%'
ORDER BY birth_year_estimate
LIMIT 20;

-- Get a person with their parents
SELECT
    p.id, p.forename, p.surname, p.birth_year_estimate,
    m.forename || ' ' || m.surname as mother_name,
    f.forename || ' ' || f.surname as father_name
FROM person p
LEFT JOIN person m ON p.mother_id = m.id
LEFT JOIN person f ON p.father_id = f.id
WHERE p.id = :person_id;

-- Get a person with their children
SELECT
    p.id as parent_id, p.forename as parent_forename, p.surname as parent_surname,
    c.id as child_id, c.forename as child_forename, c.surname as child_surname,
    c.birth_year_estimate as child_birth_year
FROM person p
LEFT JOIN person c ON c.mother_id = p.id OR c.father_id = p.id
WHERE p.id = :person_id
ORDER BY c.birth_year_estimate;

-- Get spouse(s) from relationship table
SELECT
    p.id, p.forename, p.surname
FROM relationship r
JOIN person p ON (r.person_id_2 = p.id AND r.person_id_1 = :person_id)
              OR (r.person_id_1 = p.id AND r.person_id_2 = :person_id)
WHERE r.relationship_type = 'spouse';


-- ============================================
-- TREE STATS
-- ============================================

-- Count descendants at each level from a root
WITH RECURSIVE descendants AS (
    SELECT id, 1 as level
    FROM person
    WHERE mother_id = :root_id OR father_id = :root_id

    UNION ALL

    SELECT p.id, d.level + 1
    FROM person p
    JOIN descendants d ON p.mother_id = d.id OR p.father_id = d.id
    WHERE d.level < 7
)
SELECT level, COUNT(*) as count
FROM descendants
GROUP BY level
ORDER BY level;

-- People with most children
SELECT p.id, p.forename, p.surname, COUNT(c.id) as child_count
FROM person p
JOIN person c ON c.mother_id = p.id OR c.father_id = p.id
GROUP BY p.id
HAVING child_count > 2
ORDER BY child_count DESC
LIMIT 20;

-- People missing parent links (orphans in the tree)
SELECT id, forename, surname, birth_year_estimate
FROM person
WHERE mother_id IS NULL AND father_id IS NULL
  AND id IN (
    -- But who are children of someone
    SELECT person_id_2 FROM relationship WHERE relationship_type = 'parent-child'
  )
ORDER BY surname, forename;
