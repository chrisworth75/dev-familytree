package com.familytree.controller;

import com.familytree.service.TreeDataService;
import com.familytree.service.TreeDataService.TreeNode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/tree-data")
public class TreeDataController {

    private final TreeDataService treeDataService;

    public TreeDataController(TreeDataService treeDataService) {
        this.treeDataService = treeDataService;
    }

    /**
     * Get descendants of a person as a hierarchical tree structure.
     */
    @GetMapping("/person/{id}/descendants")
    public ResponseEntity<TreeNode> getDescendants(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int maxDepth) {

        int depth = Math.min(maxDepth, 20);
        return treeDataService.buildDescendantsHierarchy(id, depth)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Get ancestors of a person as a hierarchical tree structure.
     */
    @GetMapping("/person/{id}/ancestors")
    public ResponseEntity<TreeNode> getAncestors(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int maxDepth) {

        int depth = Math.min(maxDepth, 20);
        return treeDataService.buildAncestorsHierarchy(id, depth)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Find the Most Recent Common Ancestor (MRCA) of two people and return
     * the path from each person to the MRCA.
     */
    @GetMapping("/mrca")
    public ResponseEntity<TreeNode> getMrca(
            @RequestParam Long personA,
            @RequestParam Long personB) {

        return treeDataService.buildMrcaPath(personA, personB)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
