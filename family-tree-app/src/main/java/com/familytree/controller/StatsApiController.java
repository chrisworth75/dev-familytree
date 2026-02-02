package com.familytree.controller;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/stats")
public class StatsApiController {

    private final JdbcTemplate jdbc;

    public StatsApiController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping
    public Map<String, Object> getStats() {
        return jdbc.queryForObject("""
            SELECT
                (SELECT COUNT(*) FROM person) AS tree_size,
                (SELECT COUNT(*) FROM ancestry_tester) AS dna_match_count,
                (SELECT COUNT(*) FROM ancestry_tester WHERE person_id IS NOT NULL) AS linked_matches,
                (SELECT COUNT(*) FROM ancestry_tester WHERE person_id IS NULL) AS unlinked_matches,
                (SELECT COUNT(DISTINCT person_id) FROM ancestry_tester WHERE person_id IS NOT NULL) AS linked_people_count
            """,
            (rs, rowNum) -> Map.of(
                "treeSize", rs.getLong("tree_size"),
                "dnaMatchCount", rs.getLong("dna_match_count"),
                "linkedMatches", rs.getLong("linked_matches"),
                "unlinkedMatches", rs.getLong("unlinked_matches"),
                "linkedPeopleCount", rs.getLong("linked_people_count")
            )
        );
    }

    @GetMapping("/top-ancestors")
    public List<Map<String, Object>> getTopAncestors() {
        String sql = """
            WITH RECURSIVE descendants AS (
                -- Base case: direct children of each person
                SELECT
                    COALESCE(father_id, mother_id) AS ancestor_id,
                    id AS descendant_id
                FROM person
                WHERE father_id IS NOT NULL OR mother_id IS NOT NULL

                UNION

                SELECT
                    mother_id AS ancestor_id,
                    id AS descendant_id
                FROM person
                WHERE father_id IS NOT NULL AND mother_id IS NOT NULL

                UNION

                -- Recursive case: descendants of descendants
                SELECT
                    d.ancestor_id,
                    p.id AS descendant_id
                FROM descendants d
                JOIN person p ON p.father_id = d.descendant_id OR p.mother_id = d.descendant_id
            ),
            ancestor_counts AS (
                SELECT
                    ancestor_id,
                    COUNT(DISTINCT descendant_id) AS descendant_count
                FROM descendants
                WHERE ancestor_id IS NOT NULL
                GROUP BY ancestor_id
            )
            SELECT
                p.id,
                TRIM(COALESCE(p.first_name, '') || ' ' || COALESCE(p.surname, '')) AS name,
                COALESCE(EXTRACT(YEAR FROM p.birth_date)::INTEGER, p.birth_year_approx) AS birth_year,
                ac.descendant_count
            FROM ancestor_counts ac
            JOIN person p ON p.id = ac.ancestor_id
            ORDER BY ac.descendant_count DESC
            LIMIT 10
            """;

        return jdbc.query(sql, (rs, rowNum) -> {
            Map<String, Object> row = new HashMap<>();
            row.put("id", rs.getLong("id"));
            row.put("name", rs.getString("name"));
            row.put("birthYear", rs.getObject("birth_year"));
            row.put("descendantCount", rs.getLong("descendant_count"));
            return row;
        });
    }
}
