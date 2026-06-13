package com.familytree.dto;

import jakarta.validation.constraints.NotBlank;

/** Request body for creating a tree. */
public record CreateTreeRequest(
    @NotBlank(message = "tree name is required") String name,
    String source,
    String ownerName,
    String notes,
    String dnaTestId,
    Long ancestryTreeId,
    Integer size
) {
}
