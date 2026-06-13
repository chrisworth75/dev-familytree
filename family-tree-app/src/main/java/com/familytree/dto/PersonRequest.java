package com.familytree.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import jakarta.validation.constraints.Pattern;

/**
 * Request body for creating/updating a person and for the relationship endpoints
 * (parent/child/spouse). A single flat record covers all of them — the relationship
 * fields ({@code parentId}/{@code childId}/{@code spouseId}/{@code parentGender}) are
 * optional and ignored where not relevant.
 * <p>
 * Validation lives here (the point of typed request DTOs): the {@code @Pattern} on the
 * dates rejects anything not in {@code dd MM yyyy} with a 400 instead of the old silent
 * null. {@code firstName} also accepts the legacy {@code forename} JSON key.
 */
public record PersonRequest(
    Long id,
    @JsonAlias("forename") String firstName,
    String middleNames,
    String surname,
    String birthSurname,
    String birthPlace,
    String deathPlace,
    @Pattern(regexp = "^[MFmf]$", message = "gender must be M or F") String gender,
    String notes,
    @Pattern(regexp = "^\\d{2} \\d{2} \\d{4}$", message = "birthDate must be 'dd MM yyyy'") String birthDate,
    Integer birthYear,
    @Pattern(regexp = "^\\d{2} \\d{2} \\d{4}$", message = "deathDate must be 'dd MM yyyy'") String deathDate,
    Integer deathYear,
    Long parentId,
    Long childId,
    Long spouseId,
    Long fatherId,
    Long motherId,
    @Pattern(regexp = "^[MFmf]$", message = "parentGender must be M or F") String parentGender
) {
    public static Builder builder() {
        return new Builder();
    }

    /** Fluent builder for programmatic construction (tests, seeders). */
    public static final class Builder {
        private Long id;
        private String firstName, middleNames, surname, birthSurname, birthPlace,
            deathPlace, gender, notes, birthDate, deathDate, parentGender;
        private Integer birthYear, deathYear;
        private Long parentId, childId, spouseId, fatherId, motherId;

        public Builder id(Long v) { this.id = v; return this; }
        public Builder firstName(String v) { this.firstName = v; return this; }
        public Builder middleNames(String v) { this.middleNames = v; return this; }
        public Builder surname(String v) { this.surname = v; return this; }
        public Builder birthSurname(String v) { this.birthSurname = v; return this; }
        public Builder birthPlace(String v) { this.birthPlace = v; return this; }
        public Builder deathPlace(String v) { this.deathPlace = v; return this; }
        public Builder gender(String v) { this.gender = v; return this; }
        public Builder notes(String v) { this.notes = v; return this; }
        public Builder birthDate(String v) { this.birthDate = v; return this; }
        public Builder birthYear(Integer v) { this.birthYear = v; return this; }
        public Builder deathDate(String v) { this.deathDate = v; return this; }
        public Builder deathYear(Integer v) { this.deathYear = v; return this; }
        public Builder parentId(Long v) { this.parentId = v; return this; }
        public Builder childId(Long v) { this.childId = v; return this; }
        public Builder spouseId(Long v) { this.spouseId = v; return this; }
        public Builder fatherId(Long v) { this.fatherId = v; return this; }
        public Builder motherId(Long v) { this.motherId = v; return this; }
        public Builder parentGender(String v) { this.parentGender = v; return this; }

        public PersonRequest build() {
            return new PersonRequest(id, firstName, middleNames, surname, birthSurname,
                birthPlace, deathPlace, gender, notes, birthDate, birthYear, deathDate, deathYear,
                parentId, childId, spouseId, fatherId, motherId, parentGender);
        }
    }
}
