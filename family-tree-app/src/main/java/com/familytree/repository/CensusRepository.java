package com.familytree.repository;

import com.familytree.model.CensusRecord;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class CensusRepository {

    private final JdbcTemplate jdbc;

    // Maps source_record table (with JSONB data) to CensusRecord model
    private static final RowMapper<CensusRecord> CENSUS_MAPPER = (rs, rowNum) -> new CensusRecord(
        rs.getLong("id"),
        rs.getObject("record_year") != null ? rs.getInt("record_year") : null,
        rs.getString("reference"),
        null, // registration_district - not stored separately
        null, // sub_district - not stored separately
        null, // parish - not stored separately
        rs.getString("location"),
        rs.getString("name_as_recorded"),
        rs.getString("relationship_to_head"),
        rs.getString("marital_status"),
        rs.getObject("age_as_recorded") != null ? rs.getInt("age_as_recorded") : null,
        rs.getString("sex"),
        rs.getString("occupation"),
        rs.getString("birth_place_as_recorded"),
        rs.getString("household_id"),
        rs.getObject("schedule_number") != null ? rs.getInt("schedule_number") : null,
        rs.getString("url"),
        rs.getObject("confidence_score") != null ? rs.getDouble("confidence_score") : null,
        rs.getString("reasoning")
    );

    public CensusRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<CensusRecord> searchBySurname(String surname, Integer year, int limit) {
        StringBuilder sql = new StringBuilder("""
            SELECT sr.id,
                   EXTRACT(YEAR FROM sr.record_date)::int as record_year,
                   sr.reference,
                   sr.location,
                   sr.url,
                   sr.data->>'name_as_recorded' as name_as_recorded,
                   sr.data->>'relationship_to_head' as relationship_to_head,
                   sr.data->>'marital_status' as marital_status,
                   (sr.data->>'age_as_recorded')::int as age_as_recorded,
                   sr.data->>'sex' as sex,
                   sr.data->>'occupation' as occupation,
                   sr.data->>'birth_place_as_recorded' as birth_place_as_recorded,
                   sr.data->>'household_id' as household_id,
                   (sr.data->>'schedule_number')::int as schedule_number,
                   NULL::double precision as confidence_score,
                   NULL as reasoning
            FROM source_record sr
            WHERE sr.record_type = 'census'
            AND sr.data->>'name_as_recorded' ILIKE ?
            """);

        if (year != null) {
            sql.append(" AND EXTRACT(YEAR FROM sr.record_date) = ").append(year);
        }

        sql.append(" ORDER BY sr.record_date, sr.data->>'name_as_recorded' LIMIT ").append(Math.min(limit, 500));

        String pattern = "%" + surname + "%";
        return jdbc.query(sql.toString(), CENSUS_MAPPER, pattern);
    }

    public List<CensusRecord> findByPersonId(Long personId) {
        String sql = """
            SELECT sr.id,
                   EXTRACT(YEAR FROM sr.record_date)::int as record_year,
                   sr.reference,
                   sr.location,
                   sr.url,
                   sr.data->>'name_as_recorded' as name_as_recorded,
                   sr.data->>'relationship_to_head' as relationship_to_head,
                   sr.data->>'marital_status' as marital_status,
                   (sr.data->>'age_as_recorded')::int as age_as_recorded,
                   sr.data->>'sex' as sex,
                   sr.data->>'occupation' as occupation,
                   sr.data->>'birth_place_as_recorded' as birth_place_as_recorded,
                   sr.data->>'household_id' as household_id,
                   (sr.data->>'schedule_number')::int as schedule_number,
                   CASE ps.confidence
                       WHEN 'certain' THEN 1.0
                       WHEN 'probable' THEN 0.8
                       WHEN 'possible' THEN 0.6
                       WHEN 'speculative' THEN 0.4
                       ELSE NULL
                   END as confidence_score,
                   ps.notes as reasoning
            FROM source_record sr
            JOIN person_source ps ON sr.id = ps.source_record_id
            WHERE ps.person_id = ?
            AND sr.record_type = 'census'
            ORDER BY sr.record_date
            """;
        return jdbc.query(sql, CENSUS_MAPPER, personId);
    }
}
