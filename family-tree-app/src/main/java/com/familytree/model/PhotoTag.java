package com.familytree.model;

public record PhotoTag(
    Long photoId,
    Long personId,
    String personName,
    Double xPosition,
    Double yPosition
) {}
