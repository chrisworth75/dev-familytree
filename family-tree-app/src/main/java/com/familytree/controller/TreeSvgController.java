package com.familytree.controller;

import com.familytree.service.TreeDataService;
import com.familytree.service.TreeRenderService;
import com.familytree.service.TreeRenderService.D3ServiceException;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/tree-svg")
public class TreeSvgController {

    private static final MediaType SVG_MEDIA_TYPE = MediaType.valueOf("image/svg+xml");

    private final TreeDataService treeDataService;
    private final TreeRenderService treeRenderService;

    public TreeSvgController(TreeDataService treeDataService, TreeRenderService treeRenderService) {
        this.treeDataService = treeDataService;
        this.treeRenderService = treeRenderService;
    }

    /**
     * Render descendants of a person as an SVG tree.
     */
    @GetMapping(value = "/descendants/{id}", produces = "image/svg+xml")
    public ResponseEntity<byte[]> getDescendantsSvg(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int maxDepth) {

        int depth = Math.min(maxDepth, 20);

        return treeDataService.buildDescendantsHierarchy(id, depth)
                .map(tree -> {
                    try {
                        byte[] svg = treeRenderService.renderToSvg(tree);
                        return ResponseEntity.ok().contentType(SVG_MEDIA_TYPE).body(svg);
                    } catch (D3ServiceException e) {
                        return ResponseEntity.status(502).contentType(SVG_MEDIA_TYPE)
                                .body(errorSvg("D3 service unavailable"));
                    }
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Render ancestors of a person as an SVG tree.
     */
    @GetMapping(value = "/ancestors/{id}", produces = "image/svg+xml")
    public ResponseEntity<byte[]> getAncestorsSvg(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int maxDepth) {

        int depth = Math.min(maxDepth, 20);

        return treeDataService.buildAncestorsHierarchy(id, depth)
                .map(tree -> {
                    try {
                        byte[] svg = treeRenderService.renderToSvg(tree);
                        return ResponseEntity.ok().contentType(SVG_MEDIA_TYPE).body(svg);
                    } catch (D3ServiceException e) {
                        return ResponseEntity.status(502).contentType(SVG_MEDIA_TYPE)
                                .body(errorSvg("D3 service unavailable"));
                    }
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Render the path between two people via their Most Recent Common Ancestor as an SVG tree.
     */
    @GetMapping(value = "/mrca", produces = "image/svg+xml")
    public ResponseEntity<byte[]> getMrcaSvg(
            @RequestParam Long personA,
            @RequestParam Long personB) {

        return treeDataService.buildMrcaPath(personA, personB)
                .map(tree -> {
                    try {
                        byte[] svg = treeRenderService.renderToSvg(tree);
                        return ResponseEntity.ok().contentType(SVG_MEDIA_TYPE).body(svg);
                    } catch (D3ServiceException e) {
                        return ResponseEntity.status(502).contentType(SVG_MEDIA_TYPE)
                                .body(errorSvg("D3 service unavailable"));
                    }
                })
                .orElse(ResponseEntity.notFound().build());
    }

    private byte[] errorSvg(String message) {
        String svg = String.format("""
            <?xml version="1.0" encoding="UTF-8"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="400" height="100" viewBox="0 0 400 100">
              <rect width="100%%" height="100%%" fill="#fee2e2"/>
              <text x="200" y="55" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#dc2626">
                %s
              </text>
            </svg>
            """, message);
        return svg.getBytes();
    }
}
