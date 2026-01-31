package com.familytree.repository;

import com.familytree.model.Tree;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public class TreeRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<Tree> TREE_MAPPER = (rs, rowNum) -> new Tree(
        rs.getLong("id"),
        rs.getString("name"),
        rs.getString("source"),
        rs.getString("owner_name"),
        rs.getObject("match_person_id") != null ? rs.getLong("match_person_id") : null,
        rs.getString("notes"),
        rs.getString("dna_test_id"),
        rs.getObject("ancestry_tree_id") != null ? rs.getLong("ancestry_tree_id") : null,
        rs.getObject("size") != null ? rs.getInt("size") : null
    );

    public TreeRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Tree> findAll() {
        return jdbc.query("SELECT * FROM tree ORDER BY name", TREE_MAPPER);
    }

    public List<Tree> findAllWithMembers() {
        // Trees with at least one person linked
        return jdbc.query("""
            SELECT DISTINCT t.* FROM tree t
            WHERE EXISTS (SELECT 1 FROM person p WHERE p.tree_id = t.id)
            ORDER BY t.name
            """,
            TREE_MAPPER
        );
    }

    public Optional<Tree> findById(Long id) {
        List<Tree> results = jdbc.query(
            "SELECT * FROM tree WHERE id = ?",
            TREE_MAPPER,
            id
        );
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }

    public Long save(String name, String source, String ownerName, String notes,
                     String dnaTestId, Long ancestryTreeId, Integer size) {
        return jdbc.queryForObject("""
            INSERT INTO tree (name, source, owner_name, notes, dna_test_id, ancestry_tree_id, size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            Long.class,
            name, source, ownerName, notes, dnaTestId, ancestryTreeId, size
        );
    }

    public void delete(Long id) {
        jdbc.update("DELETE FROM tree WHERE id = ?", id);
    }
}
