package com.familytree.dto;

import com.familytree.model.Tree;
import com.fasterxml.jackson.annotation.JsonInclude;

/** API response representation of a tree, including the computed {@code displayName}. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TreeDto(
    Long id,
    String name,
    String displayName,
    String source,
    String ownerName,
    Long matchPersonId,
    String notes,
    String dnaTestId,
    Long ancestryTreeId,
    Integer size
) {
    public static TreeDto from(Tree t) {
        if (t == null) {
            return null;
        }
        return new TreeDto(t.id(), t.name(), t.displayName(), t.source(), t.ownerName(),
            t.matchPersonId(), t.notes(), t.dnaTestId(), t.ancestryTreeId(), t.size());
    }
}
