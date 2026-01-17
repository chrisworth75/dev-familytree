package com.familytree.model;

public record PersonUrl(
    Long id,
    Long personId,
    String url,
    String description,
    String source
) {}
