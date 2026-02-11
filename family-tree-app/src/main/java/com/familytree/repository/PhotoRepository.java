package com.familytree.repository;

import com.familytree.model.Photo;
import com.familytree.model.PhotoTag;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public class PhotoRepository {

    private final JdbcTemplate jdbc;

    private static final RowMapper<Photo> PHOTO_MAPPER = (rs, rowNum) -> new Photo(
        rs.getLong("id"),
        rs.getString("original_filename"),
        rs.getString("description"),
        rs.getObject("year_taken", Integer.class),
        rs.getTimestamp("uploaded_at").toLocalDateTime(),
        rs.getInt("tag_count")
    );

    private static final RowMapper<PhotoTag> TAG_MAPPER = (rs, rowNum) -> new PhotoTag(
        rs.getLong("photo_id"),
        rs.getLong("person_id"),
        rs.getString("person_name"),
        rs.getObject("x_position", Double.class),
        rs.getObject("y_position", Double.class)
    );

    public PhotoRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<Photo> findById(Long id) {
        var results = jdbc.query(
            "SELECT p.*, COALESCE(t.cnt, 0) AS tag_count FROM photo p " +
            "LEFT JOIN (SELECT photo_id, COUNT(*) AS cnt FROM photo_tag GROUP BY photo_id) t " +
            "ON p.id = t.photo_id WHERE p.id = ?",
            PHOTO_MAPPER, id
        );
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }

    public List<Photo> findAllWithTagCount() {
        return jdbc.query(
            "SELECT p.*, COALESCE(t.cnt, 0) AS tag_count FROM photo p " +
            "LEFT JOIN (SELECT photo_id, COUNT(*) AS cnt FROM photo_tag GROUP BY photo_id) t " +
            "ON p.id = t.photo_id ORDER BY p.uploaded_at DESC",
            PHOTO_MAPPER
        );
    }

    public List<PhotoTag> findTagsByPhotoId(Long photoId) {
        return jdbc.query(
            "SELECT pt.photo_id, pt.person_id, CONCAT_WS(' ', per.first_name, per.surname) AS person_name, pt.x_position, pt.y_position " +
            "FROM photo_tag pt JOIN person per ON pt.person_id = per.id " +
            "WHERE pt.photo_id = ? ORDER BY per.first_name, per.surname",
            TAG_MAPPER, photoId
        );
    }

    public List<Photo> findPhotosByPersonId(Long personId) {
        return jdbc.query(
            "SELECT p.*, COALESCE(t.cnt, 0) AS tag_count FROM photo p " +
            "JOIN photo_tag pt ON p.id = pt.photo_id " +
            "LEFT JOIN (SELECT photo_id, COUNT(*) AS cnt FROM photo_tag GROUP BY photo_id) t " +
            "ON p.id = t.photo_id WHERE pt.person_id = ? ORDER BY p.year_taken, p.uploaded_at DESC",
            PHOTO_MAPPER, personId
        );
    }

    public Long save(String originalFilename, String description, Integer yearTaken) {
        return jdbc.queryForObject(
            "INSERT INTO photo (original_filename, description, year_taken) VALUES (?, ?, ?) RETURNING id",
            Long.class,
            originalFilename, description, yearTaken
        );
    }

    public void delete(Long id) {
        jdbc.update("DELETE FROM photo WHERE id = ?", id);
    }

    public void addTag(Long photoId, Long personId, Double xPosition, Double yPosition) {
        jdbc.update(
            "INSERT INTO photo_tag (photo_id, person_id, x_position, y_position) VALUES (?, ?, ?, ?)",
            photoId, personId, xPosition, yPosition
        );
    }

    public boolean tagExists(Long photoId, Long personId) {
        Integer count = jdbc.queryForObject(
            "SELECT COUNT(*) FROM photo_tag WHERE photo_id = ? AND person_id = ?",
            Integer.class, photoId, personId
        );
        return count != null && count > 0;
    }

    public void removeTag(Long photoId, Long personId) {
        jdbc.update("DELETE FROM photo_tag WHERE photo_id = ? AND person_id = ?", photoId, personId);
    }
}
