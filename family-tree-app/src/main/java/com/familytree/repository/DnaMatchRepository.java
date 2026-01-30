package com.familytree.repository;

import com.familytree.model.DnaMatch;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class DnaMatchRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<DnaMatch> MATCH_MAPPER = (rs, rowNum) -> new DnaMatch(
        rs.getString("dna_test_id"),
        rs.getString("name"),
        rs.getBigDecimal("shared_cm"),
        rs.getObject("shared_segments") != null ? rs.getInt("shared_segments") : null,
        rs.getString("predicted_relationship"),
        rs.getString("match_side"),
        rs.getObject("has_tree") != null ? rs.getBoolean("has_tree") : null,
        rs.getObject("tree_size") != null ? rs.getInt("tree_size") : null,
        rs.getObject("person_id") != null ? rs.getLong("person_id") : null
    );

    public DnaMatchRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<DnaMatch> findAll(int limit) {
        return jdbc.query(
            "SELECT * FROM my_dna_matches LIMIT ?",
            MATCH_MAPPER,
            limit
        );
    }

    public List<DnaMatch> findByMinCm(double minCm, int limit) {
        return jdbc.query(
            "SELECT * FROM my_dna_matches WHERE shared_cm >= ? LIMIT ?",
            MATCH_MAPPER,
            minCm, limit
        );
    }

    public List<DnaMatch> findByMatchSide(String side, int limit) {
        return jdbc.query(
            "SELECT * FROM my_dna_matches WHERE match_side = ? LIMIT ?",
            MATCH_MAPPER,
            side, limit
        );
    }

    public List<DnaMatch> findLinked(int limit) {
        return jdbc.query(
            "SELECT * FROM my_dna_matches WHERE person_id IS NOT NULL LIMIT ?",
            MATCH_MAPPER,
            limit
        );
    }
}
