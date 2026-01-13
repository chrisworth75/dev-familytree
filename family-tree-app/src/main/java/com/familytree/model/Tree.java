package com.familytree.model;

public record Tree(
    Long id,
    String name,
    String ownerName,
    Integer personCount,
    String treeType,
    String ancestryTreeId
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
