package com.familytree.controller;

import com.familytree.service.AvatarOverlayService;
import com.familytree.service.TreeDataService;
import com.familytree.service.TreeDataService.TreeNode;
import com.familytree.service.TreeRenderService;
import com.familytree.service.TreeRenderService.D3ServiceException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/tree-svg")
public class TreeSvgController {

    private static final Logger log = LoggerFactory.getLogger(TreeSvgController.class);
    private static final MediaType SVG_MEDIA_TYPE = MediaType.valueOf("image/svg+xml");

    private final TreeDataService treeDataService;
    private final TreeRenderService treeRenderService;
    private final AvatarOverlayService avatarOverlayService;
    private final Path uploadsDir;

    public TreeSvgController(TreeDataService treeDataService,
                             TreeRenderService treeRenderService,
                             AvatarOverlayService avatarOverlayService,
                             @Value("${familytree.uploads.dir:uploads}") String uploadsDir) {
        this.treeDataService = treeDataService;
        this.treeRenderService = treeRenderService;
        this.avatarOverlayService = avatarOverlayService;
        this.uploadsDir = Path.of(uploadsDir);
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
                        svg = overlayAvatarsOnSvg(svg, tree);
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
                        svg = overlayAvatarsOnSvg(svg, tree);
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
     * Uses vertical layout with large photo nodes optimised for small MRCA diagrams.
     * Avatar images are overlaid for persons who have them.
     */
    @GetMapping(value = "/mrca", produces = "image/svg+xml")
    public ResponseEntity<byte[]> getMrcaSvg(
            @RequestParam Long personA,
            @RequestParam Long personB) {

        return treeDataService.buildMrcaPath(personA, personB)
                .map(tree -> {
                    try {
                        byte[] svg = treeRenderService.renderMrcaToSvg(tree);
                        svg = overlayAvatarsOnSvg(svg, tree);
                        return ResponseEntity.ok().contentType(SVG_MEDIA_TYPE).body(svg);
                    } catch (D3ServiceException e) {
                        return ResponseEntity.status(502).contentType(SVG_MEDIA_TYPE)
                                .body(errorSvg("D3 service unavailable"));
                    }
                })
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Overlay avatar images onto SVG tree nodes.
     */
    private byte[] overlayAvatarsOnSvg(byte[] svg, TreeNode tree) {
        Map<Long, String> avatarMap = buildAvatarMap(tree);
        if (!avatarMap.isEmpty()) {
            String svgContent = new String(svg);
            svgContent = avatarOverlayService.overlayAvatars(svgContent, avatarMap);
            return svgContent.getBytes();
        }
        return svg;
    }

    /**
     * Build a map of personId to base64 data URL for all persons in the tree who have avatars.
     */
    private Map<Long, String> buildAvatarMap(TreeNode node) {
        Map<Long, String> avatarMap = new HashMap<>();
        collectAvatars(node, avatarMap);
        return avatarMap;
    }

    /**
     * Recursively collect avatars from tree nodes, converting to base64 data URLs.
     * Base64 embedding is required because SVG loaded via img src blocks external resources.
     */
    private void collectAvatars(TreeNode node, Map<Long, String> avatarMap) {
        if (node == null) return;

        String avatarPath = node.getAvatarPath();
        if (avatarPath != null && !avatarPath.isBlank()) {
            Path fullPath = uploadsDir.resolve(avatarPath);
            if (Files.exists(fullPath)) {
                try {
                    byte[] imageBytes = Files.readAllBytes(fullPath);
                    String base64 = Base64.getEncoder().encodeToString(imageBytes);
                    String mimeType = getMimeType(avatarPath);
                    String dataUrl = "data:" + mimeType + ";base64," + base64;
                    avatarMap.put(node.getId(), dataUrl);
                } catch (IOException e) {
                    log.warn("Failed to read avatar file: {}", fullPath, e);
                }
            }
        }

        if (node.getChildren() != null) {
            for (TreeNode child : node.getChildren()) {
                collectAvatars(child, avatarMap);
            }
        }
    }

    /**
     * Get MIME type from file extension.
     */
    private String getMimeType(String path) {
        String lower = path.toLowerCase();
        if (lower.endsWith(".png")) return "image/png";
        if (lower.endsWith(".gif")) return "image/gif";
        if (lower.endsWith(".webp")) return "image/webp";
        return "image/jpeg"; // default for .jpg, .jpeg
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
