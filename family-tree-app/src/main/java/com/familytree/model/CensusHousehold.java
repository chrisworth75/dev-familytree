package com.familytree.model;

import java.util.List;

public record CensusHousehold(
    Long id,
    Integer year,
    String address,
    String occupation,
    String status,
    String relationshipToHead,
    Integer age,
    String birthPlace,
    String reference,
    String url,
    List<HouseholdMember> household
) {}
