package com.familytree.repository;

import com.familytree.model.Person;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Date;
import java.util.List;
import java.util.Optional;

@Repository
public class PersonRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<Person> PERSON_MAPPER = (rs, rowNum) -> {
        Date birthDate = rs.getDate("birth_date");
        Date deathDate = rs.getDate("death_date");
        return new Person(
            rs.getLong("id"),
            rs.getString("first_name"),
            rs.getString("middle_names"),
            rs.getString("surname"),
            rs.getString("birth_surname"),
            birthDate != null ? birthDate.toLocalDate() : null,
            (Integer) rs.getObject("birth_year_approx"),
            rs.getString("birth_place"),
            deathDate != null ? deathDate.toLocalDate() : null,
            (Integer) rs.getObject("death_year_approx"),
            rs.getString("death_place"),
            rs.getString("gender"),
            rs.getObject("father_id") != null ? rs.getLong("father_id") : null,
            rs.getObject("mother_id") != null ? rs.getLong("mother_id") : null,
            rs.getString("notes"),
            (Integer) rs.getObject("tree_id"),
            rs.getString("avatar_path")
        );
    };

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

    public List<Person> findAll() {
        return jdbc.query("SELECT * FROM person ORDER BY surname, first_name", PERSON_MAPPER);
    }

    public List<Person> findAncestors(Long personId, int maxGenerations) {
        String sql = """
            WITH RECURSIVE ancestors AS (
                SELECT id, first_name, middle_names, surname, birth_surname, birth_date, birth_year_approx,
                       birth_place, death_date, death_year_approx, death_place, gender,
                       father_id, mother_id, notes, tree_id, avatar_path, 1 as generation
                FROM person WHERE id = ?
                UNION ALL
                SELECT p.id, p.first_name, p.middle_names, p.surname, p.birth_surname, p.birth_date, p.birth_year_approx,
                       p.birth_place, p.death_date, p.death_year_approx, p.death_place, p.gender,
                       p.father_id, p.mother_id, p.notes, p.tree_id, p.avatar_path, a.generation + 1
                FROM person p
                JOIN ancestors a ON p.id = a.father_id OR p.id = a.mother_id
                WHERE a.generation < ?
            )
            SELECT id, first_name, middle_names, surname, birth_surname, birth_date, birth_year_approx,
                   birth_place, death_date, death_year_approx, death_place, gender,
                   father_id, mother_id, notes, tree_id, avatar_path
            FROM ancestors
            WHERE generation > 1
            ORDER BY generation, surname, first_name
            """;
        return jdbc.query(sql, PERSON_MAPPER, personId, maxGenerations);
    }

    public List<Person> findDescendants(Long personId, int maxGenerations) {
        String sql = """
            WITH RECURSIVE descendants AS (
                SELECT id, first_name, middle_names, surname, birth_surname, birth_date, birth_year_approx,
                       birth_place, death_date, death_year_approx, death_place, gender,
                       father_id, mother_id, notes, tree_id, avatar_path, 1 as generation
                FROM person WHERE id = ?
                UNION ALL
                SELECT p.id, p.first_name, p.middle_names, p.surname, p.birth_surname, p.birth_date, p.birth_year_approx,
                       p.birth_place, p.death_date, p.death_year_approx, p.death_place, p.gender,
                       p.father_id, p.mother_id, p.notes, p.tree_id, p.avatar_path, d.generation + 1
                FROM person p
                JOIN descendants d ON p.father_id = d.id OR p.mother_id = d.id
                WHERE d.generation < ?
            )
            SELECT id, first_name, middle_names, surname, birth_surname, birth_date, birth_year_approx,
                   birth_place, death_date, death_year_approx, death_place, gender,
                   father_id, mother_id, notes, tree_id, avatar_path
            FROM descendants
            WHERE generation > 1
            ORDER BY generation, surname, first_name
            """;
        return jdbc.query(sql, PERSON_MAPPER, personId, maxGenerations);
    }

    public List<Person> search(String name, String birthPlace, int limit) {
        StringBuilder sql = new StringBuilder("SELECT * FROM person WHERE 1=1");
        java.util.ArrayList<Object> params = new java.util.ArrayList<>();

        if (name != null && !name.isBlank()) {
            sql.append(" AND (first_name ILIKE ? OR surname ILIKE ? OR (first_name || ' ' || surname) ILIKE ?)");
            String pattern = "%" + name.trim() + "%";
            params.add(pattern);
            params.add(pattern);
            params.add(pattern);
        }

        if (birthPlace != null && !birthPlace.isBlank()) {
            sql.append(" AND birth_place ILIKE ?");
            params.add("%" + birthPlace.trim() + "%");
        }

        sql.append(" ORDER BY surname, first_name LIMIT ?");
        params.add(limit);

        return jdbc.query(sql.toString(), PERSON_MAPPER, params.toArray());
    }

    public List<Person> findChildren(Long personId) {
        return jdbc.query(
            "SELECT * FROM person WHERE father_id = ? OR mother_id = ? ORDER BY birth_date",
            PERSON_MAPPER,
            personId, personId
        );
    }

    public List<Person> findSpouses(Long personId) {
        String sql = """
            SELECT p.* FROM person p
            JOIN partnership m ON (m.person_1_id = p.id OR m.person_2_id = p.id)
            WHERE (m.person_1_id = ? OR m.person_2_id = ?) AND p.id != ?
            """;
        return jdbc.query(sql, PERSON_MAPPER, personId, personId, personId);
    }

    public List<Person> findSiblings(Long personId) {
        String sql = """
            SELECT DISTINCT p.* FROM person p
            JOIN person target ON target.id = ?
            WHERE p.id != ?
            AND (
                (p.father_id IS NOT NULL AND p.father_id = target.father_id)
                OR (p.mother_id IS NOT NULL AND p.mother_id = target.mother_id)
            )
            ORDER BY birth_date, first_name
            """;
        return jdbc.query(sql, PERSON_MAPPER, personId, personId);
    }

    public Long save(String firstName, String surname, Integer birthYear, Integer deathYear,
                     String birthPlace, Long fatherId, Long motherId, Integer treeId) {
        return save(firstName, null, surname, null, null, birthYear, birthPlace,
                    null, deathYear, null, null, null, fatherId, motherId, treeId);
    }

    public Long save(String firstName, String surname, java.time.LocalDate birthDate, Integer birthYearApprox,
                     java.time.LocalDate deathDate, Integer deathYearApprox, String birthPlace,
                     Long fatherId, Long motherId, Integer treeId) {
        return save(firstName, null, surname, null, birthDate, birthYearApprox, birthPlace,
                    deathDate, deathYearApprox, null, null, null, fatherId, motherId, treeId);
    }

    public Long save(String firstName, String middleNames, String surname, String birthSurname,
                     java.time.LocalDate birthDate, Integer birthYearApprox, String birthPlace,
                     java.time.LocalDate deathDate, Integer deathYearApprox, String deathPlace,
                     String gender, String notes, Long fatherId, Long motherId, Integer treeId) {
        return save(null, firstName, middleNames, surname, birthSurname, birthDate, birthYearApprox,
                    birthPlace, deathDate, deathYearApprox, deathPlace, gender, notes, fatherId, motherId, treeId);
    }

    public Long save(Long id, String firstName, String middleNames, String surname, String birthSurname,
                     java.time.LocalDate birthDate, Integer birthYearApprox, String birthPlace,
                     java.time.LocalDate deathDate, Integer deathYearApprox, String deathPlace,
                     String gender, String notes, Long fatherId, Long motherId, Integer treeId) {
        if (id != null) {
            String sql = """
                INSERT INTO person (id, first_name, middle_names, surname, birth_surname,
                                   birth_date, birth_year_approx, birth_place,
                                   death_date, death_year_approx, death_place,
                                   gender, notes, father_id, mother_id, tree_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """;
            return jdbc.queryForObject(sql, Long.class, id, firstName, middleNames, surname, birthSurname,
                                       birthDate != null ? java.sql.Date.valueOf(birthDate) : null, birthYearApprox, birthPlace,
                                       deathDate != null ? java.sql.Date.valueOf(deathDate) : null, deathYearApprox, deathPlace,
                                       gender, notes, fatherId, motherId, treeId);
        } else {
            String sql = """
                INSERT INTO person (first_name, middle_names, surname, birth_surname,
                                   birth_date, birth_year_approx, birth_place,
                                   death_date, death_year_approx, death_place,
                                   gender, notes, father_id, mother_id, tree_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """;
            return jdbc.queryForObject(sql, Long.class, firstName, middleNames, surname, birthSurname,
                                       birthDate != null ? java.sql.Date.valueOf(birthDate) : null, birthYearApprox, birthPlace,
                                       deathDate != null ? java.sql.Date.valueOf(deathDate) : null, deathYearApprox, deathPlace,
                                       gender, notes, fatherId, motherId, treeId);
        }
    }

    public void update(Long id, String firstName, String middleNames, String surname, String birthSurname,
                       java.time.LocalDate birthDate, Integer birthYearApprox, String birthPlace,
                       java.time.LocalDate deathDate, Integer deathYearApprox, String deathPlace,
                       String gender, String notes) {
        String sql = """
            UPDATE person SET first_name = ?, middle_names = ?, surname = ?, birth_surname = ?,
                             birth_date = ?, birth_year_approx = ?, birth_place = ?,
                             death_date = ?, death_year_approx = ?, death_place = ?,
                             gender = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """;
        jdbc.update(sql, firstName, middleNames, surname, birthSurname,
                    birthDate != null ? java.sql.Date.valueOf(birthDate) : null, birthYearApprox, birthPlace,
                    deathDate != null ? java.sql.Date.valueOf(deathDate) : null, deathYearApprox, deathPlace,
                    gender, notes, id);
    }

    public void updateParents(Long id, Long parent1Id, Long parent2Id) {
        jdbc.update("UPDATE person SET father_id = ?, mother_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    parent1Id, parent2Id, id);
    }

    public void delete(Long id) {
        // First remove any partnership records
        jdbc.update("DELETE FROM partnership WHERE person_1_id = ? OR person_2_id = ?", id, id);
        // Then delete the person
        jdbc.update("DELETE FROM person WHERE id = ?", id);
    }

    public void addMarriage(Long person1Id, Long person2Id) {
        // Check if partnership already exists
        String checkSql = """
            SELECT COUNT(*) FROM partnership
            WHERE (person_1_id = ? AND person_2_id = ?) OR (person_1_id = ? AND person_2_id = ?)
            """;
        Integer count = jdbc.queryForObject(checkSql, Integer.class, person1Id, person2Id, person2Id, person1Id);
        if (count == null || count == 0) {
            jdbc.update("INSERT INTO partnership (person_1_id, person_2_id) VALUES (?, ?)",
                       person1Id, person2Id);
        }
    }

    public void removeMarriage(Long person1Id, Long person2Id) {
        String sql = """
            DELETE FROM partnership
            WHERE (person_1_id = ? AND person_2_id = ?) OR (person_1_id = ? AND person_2_id = ?)
            """;
        jdbc.update(sql, person1Id, person2Id, person2Id, person1Id);
    }

    public int countAncestors(Long personId) {
        String sql = """
            WITH RECURSIVE ancestors AS (
                SELECT id, father_id, mother_id, 1 as generation
                FROM person WHERE id = ?
                UNION ALL
                SELECT p.id, p.father_id, p.mother_id, a.generation + 1
                FROM person p
                JOIN ancestors a ON p.id = a.father_id OR p.id = a.mother_id
                WHERE a.generation < 20
            )
            SELECT COUNT(*) FROM ancestors WHERE generation > 1
            """;
        return jdbc.queryForObject(sql, Integer.class, personId);
    }

    public int countDescendants(Long personId) {
        String sql = """
            WITH RECURSIVE descendants AS (
                SELECT id, 1 as generation
                FROM person WHERE id = ?
                UNION ALL
                SELECT p.id, d.generation + 1
                FROM person p
                JOIN descendants d ON p.father_id = d.id OR p.mother_id = d.id
                WHERE d.generation < 20
            )
            SELECT COUNT(*) FROM descendants WHERE generation > 1
            """;
        return jdbc.queryForObject(sql, Integer.class, personId);
    }

    /**
     * Find DNA match info by person ID.
     * Returns shared_cm if found, null otherwise.
     */
    public Double findDnaMatchCm(Long personId) {
        String sql = """
            SELECT shared_cm FROM my_dna_matches
            WHERE person_id = ?
            LIMIT 1
            """;
        List<Double> results = jdbc.query(sql, (rs, rowNum) -> rs.getDouble("shared_cm"), personId);
        return results.isEmpty() ? null : results.get(0);
    }
}
