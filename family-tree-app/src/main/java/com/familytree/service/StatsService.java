package com.familytree.service;

import com.familytree.model.DashboardStats;
import com.familytree.model.TopAncestor;
import com.familytree.model.TopCensusAncestor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

/**
 * Read-side queries backing the dashboard / stats REST API.
 * All SQL lives here; {@code StatsApiController} only delegates.
 */
@Service
public class StatsService {

    private final JdbcTemplate jdbc;

    public StatsService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Aggregate counts for the dashboard cards. */
    public DashboardStats getDashboardStats() {
        return jdbc.queryForObject("""
            SELECT
                (SELECT COUNT(*) FROM person) AS tree_size,
                (SELECT COUNT(*) FROM ancestry_tester) AS dna_match_count,
                (SELECT COUNT(*) FROM ancestry_tester WHERE person_id IS NOT NULL) AS linked_matches,
                (SELECT COUNT(*) FROM ancestry_tester WHERE person_id IS NULL) AS unlinked_matches,
                (SELECT COUNT(DISTINCT person_id) FROM ancestry_tester WHERE person_id IS NOT NULL) AS linked_people_count
            """,
            (rs, rowNum) -> new DashboardStats(
                rs.getLong("tree_size"),
                rs.getLong("dna_match_count"),
                rs.getLong("linked_matches"),
                rs.getLong("unlinked_matches"),
                rs.getLong("linked_people_count")
            )
        );
    }

    /** Top 10 people by total descendant count (children, grandchildren, ...). */
    public List<TopAncestor> getTopAncestorsByDescendants() {
        String sql = """
            WITH RECURSIVE descendants(ancestor_id, descendant_id) AS (
                -- Anchor: every direct parent -> child edge (father and mother)
                SELECT ancestor_id, descendant_id FROM (
                    SELECT father_id AS ancestor_id, id AS descendant_id
                    FROM person WHERE father_id IS NOT NULL
                    UNION
                    SELECT mother_id AS ancestor_id, id AS descendant_id
                    FROM person WHERE mother_id IS NOT NULL
                ) edges

                UNION

                -- Recursive: descendants of descendants
                SELECT d.ancestor_id, p.id AS descendant_id
                FROM descendants d
                JOIN person p ON p.father_id = d.descendant_id OR p.mother_id = d.descendant_id
            ),
            ancestor_counts(ancestor_id, descendant_count) AS (
                SELECT ancestor_id, COUNT(DISTINCT descendant_id) AS descendant_count
                FROM descendants
                WHERE ancestor_id IS NOT NULL
                GROUP BY ancestor_id
            )
            SELECT
                p.id,
                TRIM(COALESCE(p.first_name, '') || ' ' || COALESCE(p.surname, '')) AS name,
                COALESCE(CAST(EXTRACT(YEAR FROM p.birth_date) AS INTEGER), p.birth_year_approx) AS birth_year,
                p.avatar_path,
                ac.descendant_count
            FROM ancestor_counts ac
            JOIN person p ON p.id = ac.ancestor_id
            ORDER BY ac.descendant_count DESC, name
            LIMIT 10
            """;

        return jdbc.query(sql, (rs, rowNum) -> new TopAncestor(
            rs.getLong("id"),
            rs.getString("name"),
            birthYear(rs),
            rs.getString("avatar_path"),
            rs.getLong("descendant_count")
        ));
    }

    /** Top 10 people by number of linked census records. */
    public List<TopCensusAncestor> getTopAncestorsByCensus() {
        String sql = """
            SELECT
                p.id,
                TRIM(COALESCE(p.first_name, '') || ' ' || COALESCE(p.surname, '')) AS name,
                COALESCE(CAST(EXTRACT(YEAR FROM p.birth_date) AS INTEGER), p.birth_year_approx) AS birth_year,
                p.avatar_path,
                COUNT(*) AS census_count
            FROM person_source ps
            JOIN source_record sr ON sr.id = ps.source_record_id
            JOIN person p ON p.id = ps.person_id
            WHERE sr.record_type = 'census'
            GROUP BY p.id, p.first_name, p.surname, p.birth_date, p.birth_year_approx, p.avatar_path
            ORDER BY census_count DESC, name
            LIMIT 10
            """;

        return jdbc.query(sql, (rs, rowNum) -> new TopCensusAncestor(
            rs.getLong("id"),
            rs.getString("name"),
            birthYear(rs),
            rs.getString("avatar_path"),
            rs.getLong("census_count")
        ));
    }

    /** birth_year may be null; keep it nullable rather than coercing to 0. */
    private static Integer birthYear(ResultSet rs) throws SQLException {
        return rs.getObject("birth_year") != null ? rs.getInt("birth_year") : null;
    }
}
