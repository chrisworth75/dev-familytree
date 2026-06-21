package com.familytree.model;

/** A person ranked by total number of descendants. */
public record TopAncestor(
    long id,
    String name,
    Integer birthYear,
    String avatarPath,
    long descendantCount
) {}
