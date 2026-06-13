package com.familytree.dto;

import com.familytree.model.DnaMatch;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.util.List;

/**
 * The composite "person view": the person plus their immediate relations.
 * <p>
 * {@code mother}/{@code father} are emitted even when null (preserving the existing
 * contract). The {@code match} and *Count fields are summary-only — annotated
 * {@code NON_NULL} so the plain detail response omits them.
 */
public record PersonDetailDto(
    PersonDto person,
    PersonDto mother,
    PersonDto father,
    List<PersonDto> spouses,
    List<PersonDto> children,
    List<PersonDto> siblings,
    @JsonInclude(JsonInclude.Include.NON_NULL) DnaMatch match,
    @JsonInclude(JsonInclude.Include.NON_NULL) Integer ancestorCount,
    @JsonInclude(JsonInclude.Include.NON_NULL) Integer descendantCount
) {
}
