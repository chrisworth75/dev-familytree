package com.familytree.repository;

import com.familytree.model.Person;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

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
        rs.getString("ancestry_person_id"),
        rs.getObject("mother_id") != null ? rs.getLong("mother_id") : null,
        rs.getObject("father_id") != null ? rs.getLong("father_id") : null
    );

    public PersonRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<Person> findById(Long id) {
        List<Person> results = jdbc.query(
            "SELECT * FROM person WHERE id = ?",
            PERSON_MAPPER,
            id
        );
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }

    public List<Person> findByTreeId(Long treeId) {
        return jdbc.query(
            "SELECT * FROM person WHERE tree_id = ? ORDER BY surname, forename",
            PERSON_MAPPER,
            treeId
        );
    }

    public List<Person> findAncestors(Long personId, int maxGenerations) {
        String sql = """
            WITH RECURSIVE ancestors AS (
                SELECT id, forename, surname, birth_year_estimate, death_year_estimate,
                       birth_place, tree_id, ancestry_person_id, mother_id, father_id,
                       1 as generation
                FROM person WHERE id = ?
                UNION ALL
                SELECT p.id, p.forename, p.surname, p.birth_year_estimate, p.death_year_estimate,
                       p.birth_place, p.tree_id, p.ancestry_person_id, p.mother_id, p.father_id,
                       a.generation + 1
                FROM person p
                JOIN ancestors a ON p.id = a.mother_id OR p.id = a.father_id
                WHERE a.generation < ?
            )
            SELECT id, forename, surname, birth_year_estimate, death_year_estimate,
                   birth_place, tree_id, ancestry_person_id, mother_id, father_id
            FROM ancestors
            WHERE generation > 1
            ORDER BY generation, surname, forename
            """;
        return jdbc.query(sql, PERSON_MAPPER, personId, maxGenerations);
    }

    public List<Person> findDescendants(Long personId, int maxGenerations) {
        String sql = """
            WITH RECURSIVE descendants AS (
                SELECT id, forename, surname, birth_year_estimate, death_year_estimate,
                       birth_place, tree_id, ancestry_person_id, mother_id, father_id,
                       1 as generation
                FROM person WHERE id = ?
                UNION ALL
                SELECT p.id, p.forename, p.surname, p.birth_year_estimate, p.death_year_estimate,
                       p.birth_place, p.tree_id, p.ancestry_person_id, p.mother_id, p.father_id,
                       d.generation + 1
                FROM person p
                JOIN descendants d ON p.mother_id = d.id OR p.father_id = d.id
                WHERE d.generation < ?
            )
            SELECT id, forename, surname, birth_year_estimate, death_year_estimate,
                   birth_place, tree_id, ancestry_person_id, mother_id, father_id
            FROM descendants
            WHERE generation > 1
            ORDER BY generation, surname, forename
            """;
        return jdbc.query(sql, PERSON_MAPPER, personId, maxGenerations);
    }

    public List<Person> search(String name, String birthPlace, int limit) {
        StringBuilder sql = new StringBuilder("SELECT * FROM person WHERE 1=1");
        java.util.ArrayList<Object> params = new java.util.ArrayList<>();

        if (name != null && !name.isBlank()) {
            sql.append(" AND (forename LIKE ? OR surname LIKE ? OR (forename || ' ' || surname) LIKE ?)");
            String pattern = "%" + name.trim() + "%";
            params.add(pattern);
            params.add(pattern);
            params.add(pattern);
        }

        if (birthPlace != null && !birthPlace.isBlank()) {
            sql.append(" AND birth_place LIKE ?");
            params.add("%" + birthPlace.trim() + "%");
        }

        sql.append(" ORDER BY surname, forename LIMIT ?");
        params.add(limit);

        return jdbc.query(sql.toString(), PERSON_MAPPER, params.toArray());
    }

    public List<Person> findChildren(Long personId) {
        return jdbc.query(
            "SELECT * FROM person WHERE mother_id = ? OR father_id = ? ORDER BY birth_year_estimate",
            PERSON_MAPPER,
            personId, personId
        );
    }

    public List<Person> findSpouses(Long personId) {
        String sql = """
            SELECT p.* FROM person p
            JOIN marriage m ON (m.person_id_1 = p.id OR m.person_id_2 = p.id)
            WHERE (m.person_id_1 = ? OR m.person_id_2 = ?) AND p.id != ?
            """;
        return jdbc.query(sql, PERSON_MAPPER, personId, personId, personId);
    }

    public List<Person> findSiblings(Long personId) {
        // Find siblings: people who share at least one parent (mother or father)
        // Also include explicit sibling relationships from the relationship table
        String sql = """
            SELECT DISTINCT p.* FROM person p
            JOIN person target ON target.id = ?
            WHERE p.id != ?
            AND (
                (p.mother_id IS NOT NULL AND p.mother_id = target.mother_id)
                OR (p.father_id IS NOT NULL AND p.father_id = target.father_id)
            )
            UNION
            SELECT p.* FROM person p
            JOIN relationship r ON (r.person_id_1 = p.id OR r.person_id_2 = p.id)
            WHERE (r.person_id_1 = ? OR r.person_id_2 = ?)
            AND r.relationship_type IN ('sibling', 'half_sibling', 'twin')
            AND p.id != ?
            ORDER BY birth_year_estimate, forename
            """;
        return jdbc.query(sql, PERSON_MAPPER, personId, personId, personId, personId, personId);
    }
}
