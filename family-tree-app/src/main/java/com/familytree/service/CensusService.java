package com.familytree.service;

import com.familytree.model.CensusHousehold;
import com.familytree.model.HouseholdMember;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class CensusService {

    private static final Pattern YEAR_PATTERN = Pattern.compile("\\b(1[89]\\d{2})\\b");

    private final JdbcTemplate jdbc;

    public CensusService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<CensusHousehold> getCensusHouseholds(Long personId) {
        String sql = """
            SELECT sr.id, sr.title, sr.location, sr.url, sr.reference,
                   sr.data->>'occupation' AS occupation,
                   sr.data->>'marital_status' AS status,
                   sr.data->>'relationship_to_head' AS relationship_to_head,
                   (sr.data->>'age_as_recorded')::int AS age,
                   sr.data->>'birth_place_as_recorded' AS birth_place,
                   sr.data->>'household_id' AS household_id
            FROM source_record sr
            JOIN person_source ps ON sr.id = ps.source_record_id
            WHERE ps.person_id = ?
            AND sr.record_type = 'census'
            ORDER BY sr.title
            """;

        return jdbc.query(sql, (rs, rowNum) -> {
            String title = rs.getString("title");
            String location = rs.getString("location");
            String householdId = rs.getString("household_id");

            List<HouseholdMember> members = (title != null && location != null && householdId != null)
                ? findHouseholdMembers(title, location, householdId)
                : List.of();

            return new CensusHousehold(
                rs.getLong("id"),
                extractYear(title),
                location,
                rs.getString("occupation"),
                rs.getString("status"),
                rs.getString("relationship_to_head"),
                rs.getObject("age") != null ? rs.getInt("age") : null,
                rs.getString("birth_place"),
                rs.getString("reference"),
                rs.getString("url"),
                members
            );
        }, personId);
    }

    private List<HouseholdMember> findHouseholdMembers(String title, String location, String householdId) {
        String sql = """
            SELECT name, relationship, age, occupation, person_id
            FROM (
                SELECT DISTINCT ON (sr.id)
                       sr.data->>'name_as_recorded' AS name,
                       sr.data->>'relationship_to_head' AS relationship,
                       (sr.data->>'age_as_recorded')::int AS age,
                       sr.data->>'occupation' AS occupation,
                       ps.person_id
                FROM source_record sr
                LEFT JOIN person_source ps ON sr.id = ps.source_record_id
                WHERE sr.record_type = 'census'
                AND sr.title = ?
                AND sr.location = ?
                AND sr.data->>'household_id' = ?
                ORDER BY sr.id
            ) members
            ORDER BY CASE WHEN relationship ILIKE '%head%' THEN 0 ELSE 1 END,
                     age DESC NULLS LAST
            """;
        return jdbc.query(sql, (rs, rowNum) -> new HouseholdMember(
            rs.getString("name"),
            rs.getString("relationship"),
            rs.getObject("age") != null ? rs.getInt("age") : null,
            rs.getString("occupation"),
            rs.getObject("person_id") != null ? rs.getLong("person_id") : null
        ), title, location, householdId);
    }

    private static Integer extractYear(String title) {
        if (title == null) return null;
        Matcher m = YEAR_PATTERN.matcher(title);
        return m.find() ? Integer.parseInt(m.group(1)) : null;
    }
}
