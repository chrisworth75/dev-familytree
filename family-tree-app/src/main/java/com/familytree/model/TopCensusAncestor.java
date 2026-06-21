package com.familytree.model;

/** A person ranked by number of linked census records. */
public record TopCensusAncestor(
    long id,
    String name,
    Integer birthYear,
    String avatarPath,
    long censusCount
) {}
