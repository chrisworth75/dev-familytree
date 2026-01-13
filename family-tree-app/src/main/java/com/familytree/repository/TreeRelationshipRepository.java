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
        rs.getString("ancestry_person_id"),
        rs.getString("father_id"),
        rs.getString("mother_id"),
        rs.getString("spouse_ids")
    );

    public TreeRelationshipRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * Find relationships by ancestry_tree_id (which is what tree_relationship.tree_id stores)
     */
    public List<TreeRelationship> findByAncestryTreeId(String ancestryTreeId) {
        return jdbc.query(
            "SELECT * FROM tree_relationship WHERE tree_id = ?",
            RELATIONSHIP_MAPPER,
            ancestryTreeId
        );
    }
}
