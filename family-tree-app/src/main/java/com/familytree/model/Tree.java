package com.familytree.model;

public record Tree(
    Long id,
    String name,
    String source,
    String ownerName,
    Long matchPersonId,
    String notes
) {
    public String displayName() {
        if (name != null && !name.startsWith("Tree ")) {
            return name;
        }
        if (ownerName != null && !ownerName.isBlank()) {
            return ownerName + "'s Tree";
        }
        return name != null ? name : "Tree #" + id;
    }
}
