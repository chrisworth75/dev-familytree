package com.familytree.model;

public record HouseholdMember(
    String name,
    String relationship,
    Integer age,
    String occupation,
    Long personId
) {}
