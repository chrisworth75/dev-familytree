package com.familytree.model;

import java.math.BigDecimal;

public record DnaMatch(
    String dnaTestId,
    String name,
    BigDecimal sharedCm,
    Integer sharedSegments,
    String predictedRelationship,
    String matchSide,
    Boolean hasTree,
    Integer treeSize,
    Long personId,
    Integer generationDepth,
    String avatarPath
) {}
