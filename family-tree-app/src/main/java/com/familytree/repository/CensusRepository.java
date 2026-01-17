package com.familytree.repository;

import com.familytree.model.CensusRecord;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public class CensusRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<CensusRecord> CENSUS_MAPPER = (rs, rowNum) -> new CensusRecord(
        rs.getLong("id"),
        rs.getObject("year") != null ? rs.getInt("year") : null,
        rs.getString("piece_folio"),
        rs.getString("registration_district"),
        rs.getString("sub_district"),
        rs.getString("parish"),
        rs.getString("address"),
        rs.getString("name_as_recorded"),
        rs.getString("relationship_to_head"),
        rs.getString("marital_status"),
        rs.getObject("age_as_recorded") != null ? rs.getInt("age_as_recorded") : null,
        rs.getString("sex"),
        rs.getString("occupation"),
        rs.getString("birth_place_as_recorded"),
        rs.getString("household_id"),
        rs.getObject("schedule_number") != null ? rs.getInt("schedule_number") : null,
        rs.getString("source_url"),
        rs.getObject("confidence") != null ? rs.getDouble("confidence") : null,
        rs.getString("reasoning")
    );

    public CensusRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<CensusRecord> searchBySurname(String surname, Integer year, int limit) {
        StringBuilder sql = new StringBuilder("""
            SELECT cr.*, NULL as confidence, NULL as reasoning
            FROM census_record cr
            WHERE cr.name_as_recorded LIKE ?
            """);

        if (year != null) {
            sql.append(" AND cr.year = ").append(year);
        }

        sql.append(" ORDER BY cr.year, cr.name_as_recorded LIMIT ").append(Math.min(limit, 500));

        String pattern = "%" + surname + "%";
        return jdbc.query(sql.toString(), CENSUS_MAPPER, pattern);
    }

    public List<CensusRecord> findByPersonId(Long personId) {
        // Query both link tables: person_census_link (with confidence) and person_census (from import)
        String sql = """
            SELECT cr.*, pcl.confidence, pcl.reasoning
            FROM census_record cr
            JOIN person_census_link pcl ON cr.id = pcl.census_record_id
            WHERE pcl.person_id = ?
            UNION
            SELECT cr.*, 1.0 as confidence, 'Imported from Ancestry' as reasoning
            FROM census_record cr
            JOIN person_census pc ON cr.id = pc.census_record_id
            WHERE pc.person_id = ?
            ORDER BY year
            """;
        return jdbc.query(sql, CENSUS_MAPPER, personId, personId);
    }
}
