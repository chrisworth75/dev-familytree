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
        rs.getString("ancestry_id"),
        rs.getString("name"),
        rs.getBigDecimal("shared_cm"),
        rs.getObject("shared_segments") != null ? rs.getInt("shared_segments") : null,
        rs.getString("predicted_relationship"),
        rs.getString("source"),
        rs.getObject("admin_level") != null ? rs.getInt("admin_level") : null,
        rs.getObject("has_tree") != null ? rs.getBoolean("has_tree") : null,
        rs.getObject("tree_size") != null ? rs.getInt("tree_size") : null,
        rs.getString("notes"),
        rs.getObject("person_id") != null ? rs.getLong("person_id") : null
    );

    public DnaMatchRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<DnaMatch> findAll(int limit) {
        return jdbc.query(
            "SELECT * FROM dna_match ORDER BY shared_cm DESC LIMIT ?",
            MATCH_MAPPER,
            limit
        );
    }

    public List<DnaMatch> findByPersonId(Long personId) {
        return jdbc.query(
            "SELECT * FROM dna_match WHERE person_id = ? ORDER BY shared_cm DESC",
            MATCH_MAPPER,
            personId
        );
    }

    public List<DnaMatch> findByMinCm(double minCm, int limit) {
        return jdbc.query(
            "SELECT * FROM dna_match WHERE shared_cm >= ? ORDER BY shared_cm DESC LIMIT ?",
            MATCH_MAPPER,
            minCm, limit
        );
    }
}
