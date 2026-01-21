package com.familytree.repository;

import com.familytree.model.PersonUrl;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class PersonUrlRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<PersonUrl> URL_MAPPER = (rs, rowNum) -> new PersonUrl(
        rs.getLong("id"),
        rs.getLong("person_id"),
        rs.getString("url"),
        rs.getString("description")
    );

    public PersonUrlRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<PersonUrl> findByPersonId(Long personId) {
        return jdbc.query(
            "SELECT * FROM person_url WHERE person_id = ? ORDER BY id",
            URL_MAPPER,
            personId
        );
    }

    public Long save(Long personId, String url, String description) {
        return jdbc.queryForObject(
            "INSERT INTO person_url (person_id, url, description) VALUES (?, ?, ?) RETURNING id",
            Long.class,
            personId, url, description
        );
    }

    public void delete(Long id) {
        jdbc.update("DELETE FROM person_url WHERE id = ?", id);
    }
}
