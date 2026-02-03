-- Add generation_depth to my_dna_matches view
DROP VIEW IF EXISTS my_dna_matches;

CREATE VIEW my_dna_matches AS
SELECT
    at.dna_test_id,
    at.name,
    at.has_tree,
    at.tree_size,
    at.person_id,
    at.generation_depth,
    m.shared_cm,
    m.shared_segments,
    m.predicted_relationship,
    m.match_side
FROM ancestry_tester at
JOIN ancestry_dna_match m ON at.dna_test_id =
    CASE
        WHEN m.tester_1_id = 'e756de6c-0c8d-443b-8793-addb6f35fd6a' THEN m.tester_2_id
        ELSE m.tester_1_id
    END
WHERE m.tester_1_id = 'e756de6c-0c8d-443b-8793-addb6f35fd6a'
   OR m.tester_2_id = 'e756de6c-0c8d-443b-8793-addb6f35fd6a'
ORDER BY m.shared_cm DESC NULLS LAST;
