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
        rs.getString("notes")
    );

    public TreeRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Tree> findAllWithMembers() {
        // Trees with at least one relationship entry
        return jdbc.query("""
            SELECT DISTINCT t.* FROM tree t
            JOIN tree_relationship tr ON t.id = tr.tree_id
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
}
