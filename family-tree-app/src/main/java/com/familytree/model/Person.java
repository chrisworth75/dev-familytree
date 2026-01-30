package com.familytree.model;

import java.time.LocalDate;

public record Person(
    Long id,
    String firstName,
    String middleNames,
    String surname,
    LocalDate birthDate,
    Integer birthYearApprox,
    String birthPlace,
    LocalDate deathDate,
    Integer deathYearApprox,
    String deathPlace,
    String gender,
    Long parent1Id,
    Long parent2Id,
    String notes,
    Integer treeId
) {
    public String fullName() {
        StringBuilder sb = new StringBuilder();
        if (firstName != null && !firstName.isBlank()) {
            sb.append(firstName);
        }
        if (middleNames != null && !middleNames.isBlank()) {
            if (sb.length() > 0) sb.append(" ");
            sb.append(middleNames);
        }
        if (surname != null && !surname.isBlank()) {
            if (sb.length() > 0) sb.append(" ");
            sb.append(surname);
        }
        return sb.length() == 0 ? "Unknown" : sb.toString();
    }

    public String displayName() {
        String first = firstName != null ? firstName : "";
        String last = surname != null ? surname : "";
        String full = (first + " " + last).trim();
        return full.isEmpty() ? "Unknown" : full;
    }

    public String lifespan() {
        Integer birth = birthYear();
        Integer death = deathYear();
        if (birth == null && death == null) {
            return "";
        }
        String birthStr = birth != null ? String.valueOf(birth) : "?";
        String deathStr = death != null ? String.valueOf(death) : "";
        if (deathStr.isEmpty() && birth != null) {
            return "b. " + birthStr;
        }
        return birthStr + " - " + deathStr;
    }

    public Integer birthYear() {
        if (birthDate != null) return birthDate.getYear();
        return birthYearApprox;
    }

    public Integer deathYear() {
        if (deathDate != null) return deathDate.getYear();
        return deathYearApprox;
    }

    // Convenience getters for backwards compatibility
    public Long motherId() { return parent2Id; }
    public Long fatherId() { return parent1Id; }
}
