package com.familytree.model;

public record TreeRelationship(
    Long id,
    Long treeId,
    String ancestryPersonId,
    String fatherId,
    String motherId,
    String spouseIds  // JSON array stored as string
) {}
