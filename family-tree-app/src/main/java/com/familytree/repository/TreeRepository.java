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
        rs.getString("owner_name"),
        rs.getObject("person_count") != null ? rs.getInt("person_count") : null,
        rs.getString("tree_type"),
        rs.getString("ancestry_tree_id")
    );

    public TreeRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Tree> findAllWithMembers() {
        return jdbc.query(
            "SELECT * FROM tree WHERE person_count > 0 ORDER BY name",
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
