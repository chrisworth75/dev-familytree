package com.familytree.model;

public record TreeRelationship(
    Long id,
    Long treeId,
    Long personId,
    String ancestryId,
    String parent1AncestryId,
    String parent2AncestryId
) {}
