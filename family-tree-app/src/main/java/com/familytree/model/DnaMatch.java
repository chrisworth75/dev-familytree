package com.familytree.model;

import java.math.BigDecimal;

public record DnaMatch(
    String ancestryId,
    String name,
    BigDecimal sharedCm,
    Integer sharedSegments,
    String predictedRelationship,
    String source,
    Integer adminLevel,
    Boolean hasTree,
    Integer treeSize,
    String notes,
    Long matchedToPersonId,
    Long personId
) {}