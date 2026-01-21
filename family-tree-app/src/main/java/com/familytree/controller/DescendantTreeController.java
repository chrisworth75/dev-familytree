package com.familytree.controller;

import com.familytree.model.Person;
import com.familytree.repository.PersonRepository;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.*;

@Controller
@RequestMapping("/prototype")
public class DescendantTreeController {

    private final PersonRepository personRepository;

    // Layout constants
    private static final int CARD_W = 120;
    private static final int CARD_H = 45;
    private static final int H_GAP = 30;
    private static final int V_GAP = 60;

    // George Worthington
    private static final Long DEFAULT_ROOT_ID = 6000L;

    public DescendantTreeController(PersonRepository personRepository) {
        this.personRepository = personRepository;
    }

    @GetMapping("/svg")
    public String showDescendantTree(
            @RequestParam(required = false) Long rootId,
            Model model) {

        Long id = (rootId != null) ? rootId : DEFAULT_ROOT_ID;

        Optional<Person> rootOpt = personRepository.findById(id);
        if (rootOpt.isEmpty()) {
            model.addAttribute("error", "Person not found");
            return "descendant-tree";
        }

        Person root = rootOpt.get();

        // Build tree structure
        List<TreeNode> allNodes = new ArrayList<>();
        TreeNode rootNode = buildDescendantTree(root, 0, allNodes);

        // Calculate positions (top-down, recursive width calculation)
        calculateSubtreeWidths(rootNode);
        int startX = 50;
        positionNodes(rootNode, startX, 50);

        // Find bounds
        int maxX = allNodes.stream().mapToInt(n -> n.x + CARD_W).max().orElse(CARD_W);
        int maxY = allNodes.stream().mapToInt(n -> n.y + CARD_H).max().orElse(CARD_H);

        // Add padding
        int padding = 50;
        int svgWidth = maxX + padding;
        int svgHeight = maxY + padding;

        // Build connector lines
        List<Line> lines = new ArrayList<>();
        buildLines(rootNode, lines);

        model.addAttribute("nodes", allNodes);
        model.addAttribute("lines", lines);
        model.addAttribute("svgWidth", svgWidth);
        model.addAttribute("svgHeight", svgHeight);
        model.addAttribute("rootPerson", root);
        model.addAttribute("cardWidth", CARD_W);
        model.addAttribute("cardHeight", CARD_H);

        return "descendant-tree";
    }

    private TreeNode buildDescendantTree(Person person, int generation, List<TreeNode> allNodes) {
        TreeNode node = new TreeNode();
        node.person = person;
        node.generation = generation;
        node.children = new ArrayList<>();
        allNodes.add(node);

        // Get children (people whose mother_id or father_id is this person)
        List<Person> children = personRepository.findChildren(person.id());

        // Sort by birth year
        children.sort(Comparator.comparing(
            p -> p.birthYear() != null ? p.birthYear() : 9999
        ));

        for (Person child : children) {
            TreeNode childNode = buildDescendantTree(child, generation + 1, allNodes);
            node.children.add(childNode);
        }

        return node;
    }

    private void calculateSubtreeWidths(TreeNode node) {
        if (node.children.isEmpty()) {
            node.subtreeWidth = CARD_W;
        } else {
            int totalWidth = 0;
            for (TreeNode child : node.children) {
                calculateSubtreeWidths(child);
                totalWidth += child.subtreeWidth;
            }
            // Add gaps between children
            totalWidth += (node.children.size() - 1) * H_GAP;
            node.subtreeWidth = Math.max(CARD_W, totalWidth);
        }
    }

    private void positionNodes(TreeNode node, int left, int top) {
        // Center this node over its subtree
        node.x = left + (node.subtreeWidth - CARD_W) / 2;
        node.y = top;

        if (!node.children.isEmpty()) {
            int childTop = top + CARD_H + V_GAP;
            int childLeft = left;

            for (TreeNode child : node.children) {
                positionNodes(child, childLeft, childTop);
                childLeft += child.subtreeWidth + H_GAP;
            }
        }
    }

    private void buildLines(TreeNode node, List<Line> lines) {
        if (node.children.isEmpty()) return;

        int parentCenterX = node.x + CARD_W / 2;
        int parentBottomY = node.y + CARD_H;

        if (node.children.size() == 1) {
            // Single child - straight line down
            TreeNode child = node.children.get(0);
            int childCenterX = child.x + CARD_W / 2;
            int childTopY = child.y;
            lines.add(new Line(parentCenterX, parentBottomY, childCenterX, childTopY));
        } else {
            // Multiple children - line down, then horizontal, then down to each child
            int midY = parentBottomY + V_GAP / 2;

            // Vertical line from parent to mid-point
            lines.add(new Line(parentCenterX, parentBottomY, parentCenterX, midY));

            // Find leftmost and rightmost child centers
            TreeNode firstChild = node.children.get(0);
            TreeNode lastChild = node.children.get(node.children.size() - 1);
            int leftX = firstChild.x + CARD_W / 2;
            int rightX = lastChild.x + CARD_W / 2;

            // Horizontal line connecting all children
            lines.add(new Line(leftX, midY, rightX, midY));

            // Vertical lines down to each child
            for (TreeNode child : node.children) {
                int childCenterX = child.x + CARD_W / 2;
                int childTopY = child.y;
                lines.add(new Line(childCenterX, midY, childCenterX, childTopY));
            }
        }

        // Recurse for children
        for (TreeNode child : node.children) {
            buildLines(child, lines);
        }
    }

    // Inner classes
    public static class TreeNode {
        public Person person;
        public int x, y;
        public int generation;
        public int subtreeWidth;
        public List<TreeNode> children;

        public Person getPerson() { return person; }
        public int getX() { return x; }
        public int getY() { return y; }
    }

    public static class Line {
        public int x1, y1, x2, y2;

        public Line(int x1, int y1, int x2, int y2) {
            this.x1 = x1; this.y1 = y1;
            this.x2 = x2; this.y2 = y2;
        }

        public int getX1() { return x1; }
        public int getY1() { return y1; }
        public int getX2() { return x2; }
        public int getY2() { return y2; }
    }
}
