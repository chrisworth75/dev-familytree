package com.familytree.repository;

import com.familytree.model.TreeRelationship;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class TreeRelationshipRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<TreeRelationship> RELATIONSHIP_MAPPER = (rs, rowNum) -> new TreeRelationship(
        rs.getLong("id"),
        rs.getLong("tree_id"),
        rs.getLong("person_id"),
        rs.getString("ancestry_id"),
        rs.getString("parent_1_ancestry_id"),
        rs.getString("parent_2_ancestry_id")
    );

    public TreeRelationshipRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<TreeRelationship> findByTreeId(Long treeId) {
        return jdbc.query(
            "SELECT * FROM tree_relationship WHERE tree_id = ?",
            RELATIONSHIP_MAPPER,
            treeId
        );
    }
}
