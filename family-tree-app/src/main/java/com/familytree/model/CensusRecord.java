package com.familytree.model;

public record CensusRecord(
    Long id,
    Integer year,
    String pieceFolio,
    String registrationDistrict,
    String subDistrict,
    String parish,
    String address,
    String nameAsRecorded,
    String relationshipToHead,
    String maritalStatus,
    Integer ageAsRecorded,
    String sex,
    String occupation,
    String birthPlaceAsRecorded,
    String householdId,
    Integer scheduleNumber,
    String sourceUrl,
    Double confidence,
    String reasoning
) {}
