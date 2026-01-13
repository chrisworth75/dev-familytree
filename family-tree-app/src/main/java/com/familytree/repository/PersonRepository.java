package com.familytree.repository;

import com.familytree.model.Person;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class PersonRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<Person> PERSON_MAPPER = (rs, rowNum) -> new Person(
        rs.getLong("id"),
        rs.getString("forename"),
        rs.getString("surname"),
        rs.getObject("birth_year_estimate") != null ? rs.getInt("birth_year_estimate") : null,
        rs.getObject("death_year_estimate") != null ? rs.getInt("death_year_estimate") : null,
        rs.getString("birth_place"),
        rs.getLong("tree_id"),
        rs.getString("ancestry_person_id")
    );

    public PersonRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Person> findByTreeId(Long treeId) {
        return jdbc.query(
            "SELECT * FROM person WHERE tree_id = ? ORDER BY surname, forename",
            PERSON_MAPPER,
            treeId
        );
    }
}
