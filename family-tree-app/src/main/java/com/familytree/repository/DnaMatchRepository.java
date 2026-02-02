package com.familytree.repository;

import com.familytree.model.DnaMatch;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

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
            rs.getObject("person_id") != null ? rs.getLong("person_id") : null,
            rs.getObject("generation_depth") != null ? rs.getInt("generation_depth") : null,
            rs.getString("avatar_path")
    );

    public DnaMatchRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ========== READ OPERATIONS ==========

    public List<DnaMatch> findAll(int limit, int offset) {
        return jdbc.query(
                "SELECT * FROM my_dna_matches ORDER BY shared_cm DESC LIMIT ? OFFSET ?",
                MATCH_MAPPER,
                limit, offset
        );
    }

    public List<DnaMatch> findByMinCm(double minCm, int limit, int offset) {
        return jdbc.query(
                "SELECT * FROM my_dna_matches WHERE shared_cm >= ? ORDER BY shared_cm DESC LIMIT ? OFFSET ?",
                MATCH_MAPPER,
                minCm, limit, offset
        );
    }

    public List<DnaMatch> findByMatchSide(String side, int limit, int offset) {
        return jdbc.query(
                "SELECT * FROM my_dna_matches WHERE match_side = ? ORDER BY shared_cm DESC LIMIT ? OFFSET ?",
                MATCH_MAPPER,
                side, limit, offset
        );
    }

    public List<DnaMatch> findLinked(int limit, int offset) {
        return jdbc.query(
                "SELECT * FROM my_dna_matches WHERE person_id IS NOT NULL ORDER BY shared_cm DESC LIMIT ? OFFSET ?",
                MATCH_MAPPER,
                limit, offset
        );
    }

    public DnaMatch findByDnaTestId(String dnaTestId) {
        List<DnaMatch> results = jdbc.query(
                "SELECT * FROM my_dna_matches WHERE dna_test_id = ?",
                MATCH_MAPPER,
                dnaTestId
        );
        return results.isEmpty() ? null : results.get(0);
    }

    // ========== TESTER OPERATIONS ==========

    public void saveTester(String dnaTestId, String name, Boolean hasTree, Integer treeSize,
                           Integer adminLevel, String notes, Long personId) {
        saveTester(dnaTestId, name, hasTree, treeSize, adminLevel, notes, personId, null);
    }

    public void saveTester(String dnaTestId, String name, Boolean hasTree, Integer treeSize,
                           Integer adminLevel, String notes, Long personId, Integer generationDepth) {
        jdbc.update("""
            INSERT INTO ancestry_tester (dna_test_id, name, has_tree, tree_size, admin_level, notes, person_id, generation_depth)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (dna_test_id) DO UPDATE SET
                name = EXCLUDED.name,
                has_tree = EXCLUDED.has_tree,
                tree_size = EXCLUDED.tree_size,
                admin_level = EXCLUDED.admin_level,
                notes = EXCLUDED.notes,
                person_id = EXCLUDED.person_id,
                generation_depth = EXCLUDED.generation_depth,
                updated_at = CURRENT_TIMESTAMP
            """,
                dnaTestId, name, hasTree, treeSize, adminLevel, notes, personId, generationDepth
        );
    }

    public Map<String, Object> findTesterById(String dnaTestId) {
        List<Map<String, Object>> results = jdbc.queryForList(
                "SELECT * FROM ancestry_tester WHERE dna_test_id = ?",
                dnaTestId
        );
        return results.isEmpty() ? null : results.get(0);
    }

    public void deleteTester(String dnaTestId) {
        // Delete related matches first
        jdbc.update("DELETE FROM ancestry_dna_match WHERE tester_1_id = ? OR tester_2_id = ?",
                dnaTestId, dnaTestId);
        jdbc.update("DELETE FROM ancestry_tester WHERE dna_test_id = ?", dnaTestId);
    }

    public void updateAvatarPath(String dnaTestId, String avatarPath) {
        jdbc.update("UPDATE ancestry_tester SET avatar_path = ?, updated_at = CURRENT_TIMESTAMP WHERE dna_test_id = ?",
                avatarPath, dnaTestId);
    }

    // ========== DNA MATCH OPERATIONS ==========

    public void saveMatch(String tester1Id, String tester2Id, BigDecimal sharedCm,
                          Integer sharedSegments, String predictedRelationship, String matchSide) {
        // Ensure tester_1_id < tester_2_id (database constraint)
        String id1 = tester1Id.compareTo(tester2Id) < 0 ? tester1Id : tester2Id;
        String id2 = tester1Id.compareTo(tester2Id) < 0 ? tester2Id : tester1Id;

        jdbc.update("""
            INSERT INTO ancestry_dna_match (tester_1_id, tester_2_id, shared_cm, shared_segments,
                                           predicted_relationship, match_side)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (tester_1_id, tester_2_id) DO UPDATE SET
                shared_cm = EXCLUDED.shared_cm,
                shared_segments = EXCLUDED.shared_segments,
                predicted_relationship = EXCLUDED.predicted_relationship,
                match_side = EXCLUDED.match_side
            """,
                id1, id2, sharedCm, sharedSegments, predictedRelationship, matchSide
        );
    }

    public Map<String, Object> findMatch(String tester1Id, String tester2Id) {
        String id1 = tester1Id.compareTo(tester2Id) < 0 ? tester1Id : tester2Id;
        String id2 = tester1Id.compareTo(tester2Id) < 0 ? tester2Id : tester1Id;

        List<Map<String, Object>> results = jdbc.queryForList(
                "SELECT * FROM ancestry_dna_match WHERE tester_1_id = ? AND tester_2_id = ?",
                id1, id2
        );
        return results.isEmpty() ? null : results.get(0);
    }

    public void deleteMatch(String tester1Id, String tester2Id) {
        String id1 = tester1Id.compareTo(tester2Id) < 0 ? tester1Id : tester2Id;
        String id2 = tester1Id.compareTo(tester2Id) < 0 ? tester2Id : tester1Id;

        jdbc.update("DELETE FROM ancestry_dna_match WHERE tester_1_id = ? AND tester_2_id = ?",
                id1, id2);
    }
}