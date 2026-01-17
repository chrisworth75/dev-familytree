package com.familytree.controller;

import com.familytree.config.TreesConfig;
import com.familytree.model.FamilyTreeConfig;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

@Controller
@RequestMapping("/tree")
public class TreeController {

    private final TreesConfig treesConfig;

    public TreeController(TreesConfig treesConfig) {
        this.treesConfig = treesConfig;
    }

    @GetMapping("/{slug}")
    public String viewTree(@PathVariable String slug,
                           @AuthenticationPrincipal UserDetails user,
                           Model model) {
        FamilyTreeConfig tree = treesConfig.getTreeBySlug(slug);

        if (tree == null) {
            return "redirect:/?error=notfound";
        }

        if (!tree.isAccessibleBy(user.getUsername())) {
            return "redirect:/?error=noaccess";
        }

        // Redirect to family-chart viewer
        return "redirect:/family-chart.html?tree=" + slug;
    }

    private String getSvgContent(FamilyTreeConfig tree) {
        // Try to load static SVG file
        Resource svgResource = new ClassPathResource("static/trees/" + tree.slug() + ".svg");

        if (svgResource.exists()) {
            try {
                return svgResource.getContentAsString(StandardCharsets.UTF_8);
            } catch (IOException e) {
                // Fall through to placeholder
            }
        }

        // Return placeholder SVG if file doesn't exist
        return generatePlaceholderSvg(tree);
    }

    @GetMapping(value = "/{slug}/svg", produces = "image/svg+xml")
    public ResponseEntity<String> getTreeSvg(@PathVariable String slug,
                                              @AuthenticationPrincipal UserDetails user) {
        FamilyTreeConfig tree = treesConfig.getTreeBySlug(slug);

        if (tree == null || !tree.isAccessibleBy(user.getUsername())) {
            return ResponseEntity.notFound().build();
        }

        // Try to load static SVG file
        Resource svgResource = new ClassPathResource("static/trees/" + slug + ".svg");

        if (svgResource.exists()) {
            try {
                String svg = svgResource.getContentAsString(StandardCharsets.UTF_8);
                return ResponseEntity.ok()
                    .contentType(MediaType.valueOf("image/svg+xml"))
                    .body(svg);
            } catch (IOException e) {
                // Fall through to placeholder
            }
        }

        // Return placeholder SVG if file doesn't exist
        String placeholder = generatePlaceholderSvg(tree);
        return ResponseEntity.ok()
            .contentType(MediaType.valueOf("image/svg+xml"))
            .body(placeholder);
    }

    private String generatePlaceholderSvg(FamilyTreeConfig tree) {
        return String.format("""
            <?xml version="1.0" encoding="UTF-8"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300">
              <rect width="100%%" height="100%%" fill="#f8f9fa"/>
              <text x="300" y="130" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#6b6b6b">
                %s
              </text>
              <text x="300" y="160" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#9b9b9b">
                Tree diagram coming soon
              </text>
              <text x="300" y="190" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#9b9b9b">
                Place SVG file at: static/trees/%s.svg
              </text>
            </svg>
            """, tree.displayName(), tree.slug());
    }
}
