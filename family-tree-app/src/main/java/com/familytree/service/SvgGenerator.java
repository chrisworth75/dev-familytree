package com.familytree.service;

import com.familytree.service.TreeService.SvgMember;
import com.familytree.service.TreeService.SvgRelationship;
import com.familytree.service.TreeService.TreeData;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class SvgGenerator {

    private static final int NODE_WIDTH = 140;
    private static final int NODE_HEIGHT = 50;
    private static final int H_SPACING = 30;
    private static final int V_SPACING = 70;
    private static final int PADDING = 40;

    public String generateSvg(TreeData treeData) {
        List<SvgMember> members = treeData.members();
        List<SvgRelationship> relationships = treeData.relationships();

        if (members.isEmpty()) {
            return emptyTreeSvg();
        }

        // Build member lookup
        Map<String, SvgMember> memberMap = new HashMap<>();
        for (SvgMember m : members) {
            memberMap.put(m.id(), m);
        }

        // Build parent-child map: childId -> list of parentIds
        Map<String, List<String>> childToParents = new HashMap<>();
        Map<String, List<String>> parentToChildren = new HashMap<>();

        for (SvgRelationship rel : relationships) {
            if ("parent-child".equals(rel.type())) {
                childToParents.computeIfAbsent(rel.childId(), k -> new ArrayList<>()).add(rel.parentId());
                parentToChildren.computeIfAbsent(rel.parentId(), k -> new ArrayList<>()).add(rel.childId());
            }
        }

        // Find roots (people without parents in this tree)
        Set<String> roots = new HashSet<>();
        for (SvgMember m : members) {
            if (!childToParents.containsKey(m.id())) {
                roots.add(m.id());
            }
        }

        // If no clear roots, take oldest people
        if (roots.isEmpty() && !members.isEmpty()) {
            roots.add(members.get(0).id());
        }

        // Assign generations using BFS from roots
        Map<String, Integer> generations = new HashMap<>();
        Queue<String> queue = new LinkedList<>(roots);
        for (String root : roots) {
            generations.put(root, 0);
        }

        while (!queue.isEmpty()) {
            String current = queue.poll();
            int gen = generations.get(current);
            List<String> children = parentToChildren.getOrDefault(current, List.of());
            for (String child : children) {
                if (!generations.containsKey(child)) {
                    generations.put(child, gen + 1);
                    queue.add(child);
                }
            }
        }

        // Handle unassigned members (disconnected from roots)
        for (SvgMember m : members) {
            if (!generations.containsKey(m.id())) {
                generations.put(m.id(), 0);
            }
        }

        // Group by generation
        Map<Integer, List<String>> genToMembers = new TreeMap<>();
        for (Map.Entry<String, Integer> e : generations.entrySet()) {
            genToMembers.computeIfAbsent(e.getValue(), k -> new ArrayList<>()).add(e.getKey());
        }

        // Calculate positions
        Map<String, int[]> positions = new HashMap<>(); // id -> [x, y]
        int maxWidth = 0;

        for (Map.Entry<Integer, List<String>> e : genToMembers.entrySet()) {
            int gen = e.getKey();
            List<String> genMembers = e.getValue();
            int y = PADDING + gen * (NODE_HEIGHT + V_SPACING);
            int totalWidth = genMembers.size() * (NODE_WIDTH + H_SPACING) - H_SPACING;
            maxWidth = Math.max(maxWidth, totalWidth);

            int x = PADDING;
            for (String id : genMembers) {
                positions.put(id, new int[]{x, y});
                x += NODE_WIDTH + H_SPACING;
            }
        }

        int svgWidth = Math.max(maxWidth + PADDING * 2, 400);
        int svgHeight = PADDING * 2 + genToMembers.size() * (NODE_HEIGHT + V_SPACING);

        // Center each generation
        for (Map.Entry<Integer, List<String>> e : genToMembers.entrySet()) {
            List<String> genMembers = e.getValue();
            int totalWidth = genMembers.size() * (NODE_WIDTH + H_SPACING) - H_SPACING;
            int offset = (svgWidth - totalWidth) / 2 - PADDING;
            for (String id : genMembers) {
                int[] pos = positions.get(id);
                pos[0] += offset;
            }
        }

        // Generate SVG
        StringBuilder svg = new StringBuilder();
        svg.append(String.format("""
            <?xml version="1.0" encoding="UTF-8"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">
              <defs>
                <style>
                  .person-box { fill: #f8f9fa; stroke: #495057; stroke-width: 1.5; rx: 6; }
                  .person-box:hover { fill: #e9ecef; }
                  .person-name { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; fill: #212529; text-anchor: middle; font-weight: 500; }
                  .person-dates { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 10px; fill: #6c757d; text-anchor: middle; }
                  .connector { stroke: #adb5bd; stroke-width: 1.5; fill: none; }
                </style>
              </defs>
              <rect width="100%%" height="100%%" fill="#ffffff"/>
            """, svgWidth, svgHeight, svgWidth, svgHeight));

        // Draw connectors first (so they're behind boxes)
        svg.append("  <!-- Connectors -->\n");
        for (SvgRelationship rel : relationships) {
            if (!"parent-child".equals(rel.type())) continue;

            int[] parentPos = positions.get(rel.parentId());
            int[] childPos = positions.get(rel.childId());
            if (parentPos == null || childPos == null) continue;

            int px = parentPos[0] + NODE_WIDTH / 2;
            int py = parentPos[1] + NODE_HEIGHT;
            int cx = childPos[0] + NODE_WIDTH / 2;
            int cy = childPos[1];
            int midY = py + (cy - py) / 2;

            svg.append(String.format(
                "  <path class=\"connector\" d=\"M %d %d L %d %d L %d %d L %d %d\"/>\n",
                px, py, px, midY, cx, midY, cx, cy
            ));
        }

        // Draw person boxes
        svg.append("  <!-- People -->\n");
        for (SvgMember member : members) {
            int[] pos = positions.get(member.id());
            if (pos == null) continue;

            int x = pos[0];
            int y = pos[1];

            svg.append(String.format("  <g>\n"));
            svg.append(String.format("    <rect class=\"person-box\" x=\"%d\" y=\"%d\" width=\"%d\" height=\"%d\"/>\n",
                x, y, NODE_WIDTH, NODE_HEIGHT));

            // Name (truncate if too long)
            String name = member.name();
            if (name.length() > 18) {
                name = name.substring(0, 16) + "...";
            }
            svg.append(String.format("    <text class=\"person-name\" x=\"%d\" y=\"%d\">%s</text>\n",
                x + NODE_WIDTH / 2, y + 22, escapeXml(name)));

            // Dates
            String dates = formatDates(member.birthYear(), member.deathYear());
            if (!dates.isEmpty()) {
                svg.append(String.format("    <text class=\"person-dates\" x=\"%d\" y=\"%d\">%s</text>\n",
                    x + NODE_WIDTH / 2, y + 38, dates));
            }

            svg.append("  </g>\n");
        }

        svg.append("</svg>");
        return svg.toString();
    }

    private String formatDates(Integer birth, Integer death) {
        if (birth == null && death == null) return "";
        if (death == null) return "b. " + birth;
        if (birth == null) return "d. " + death;
        return birth + " - " + death;
    }

    private String escapeXml(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&apos;");
    }

    private String emptyTreeSvg() {
        return """
            <?xml version="1.0" encoding="UTF-8"?>
            <svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">
              <rect width="100%" height="100%" fill="#f8f9fa"/>
              <text x="200" y="100" text-anchor="middle" font-family="sans-serif" fill="#6c757d">
                No family members found
              </text>
            </svg>
            """;
    }
}
