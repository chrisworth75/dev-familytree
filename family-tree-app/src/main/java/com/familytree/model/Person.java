package com.familytree.model;

public record Person(
    Long id,
    String forename,
    String surname,
    Integer birthYearEstimate,
    Integer deathYearEstimate,
    String birthPlace,
    Long treeId,
    String ancestryPersonId,
    Long motherId,
    Long fatherId,
    String gender,
    String photoUrl
) {
    public String fullName() {
        String first = forename != null ? forename : "";
        String last = surname != null ? surname : "";
        String full = (first + " " + last).trim();
        return full.isEmpty() ? "Unknown" : full;
    }

    public String lifespan() {
        if (birthYearEstimate == null && deathYearEstimate == null) {
            return "";
        }
        String birth = birthYearEstimate != null ? String.valueOf(birthYearEstimate) : "?";
        String death = deathYearEstimate != null ? String.valueOf(deathYearEstimate) : "";
        if (death.isEmpty() && birthYearEstimate != null) {
            return "b. " + birth;
        }
        return birth + " - " + death;
    }
}
