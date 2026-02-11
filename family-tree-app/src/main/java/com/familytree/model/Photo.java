package com.familytree.model;

import java.time.LocalDateTime;

public record Photo(
    Long id,
    String originalFilename,
    String description,
    Integer yearTaken,
    LocalDateTime uploadedAt,
    int tagCount
) {}
