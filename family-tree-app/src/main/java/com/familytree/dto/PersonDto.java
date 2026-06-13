package com.familytree.dto;

import com.familytree.model.Person;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.LocalDate;

/**
 * API response representation of a person. Decouples the wire format from the
 * {@link Person} persistence record so the JSON contract can be shaped here —
 * e.g. {@code @JsonInclude} to drop nulls, {@code @JsonFormat} on dates, or
 * hiding internal fields — without touching the model or the repository.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record PersonDto(
    Long id,
    String firstName,
    String middleNames,
    String surname,
    String birthSurname,
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
    Integer treeId,
    String avatarPath
) {
    public static PersonDto from(Person p) {
        if (p == null) {
            return null;
        }
        return new PersonDto(
            p.id(), p.firstName(), p.middleNames(), p.surname(), p.birthSurname(),
            p.birthDate(), p.birthYearApprox(), p.birthPlace(),
            p.deathDate(), p.deathYearApprox(), p.deathPlace(),
            p.gender(), p.parent1Id(), p.parent2Id(), p.notes(),
            p.treeId(), p.avatarPath()
        );
    }
}
