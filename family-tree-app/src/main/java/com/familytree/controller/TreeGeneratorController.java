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
@RequestMapping("/tree-gen")
public class TreeGeneratorController {

    private final PersonRepository personRepository;

    // Layout constants
    private static final int CARD_W = 140;
    private static final int CARD_H = 50;
    private static final int H_GAP = 20;
    private static final int V_GAP = 70;
    private static final int SPOUSE_GAP = 10;

    public TreeGeneratorController(PersonRepository personRepository) {
        this.personRepository = personRepository;
    }

    @GetMapping
    public String showForm(Model model) {
        // Get all people for the dropdown, sorted by name
        List<Person> people = personRepository.findAll();
        people.sort(Comparator.comparing(Person::surname, Comparator.nullsLast(String::compareTo))
                .thenComparing(Person::firstName, Comparator.nullsLast(String::compareTo)));
        model.addAttribute("people", people);
        return "tree-generator";
    }

    @GetMapping("/render")
    public String renderTree(
            @RequestParam Long ancestorId,
            @RequestParam(defaultValue = "4") int generations,
            @RequestParam(defaultValue = "false") boolean includeSpouses,
            @RequestParam(defaultValue = "true") boolean showDates,
            Model model) {

        Optional<Person> rootOpt = personRepository.findById(ancestorId);
        if (rootOpt.isEmpty()) {
            model.addAttribute("error", "Person not found");
            return "tree-generator";
        }

        Person root = rootOpt.get();

        // Build tree structure
        List<TreeNode> allNodes = new ArrayList<>();
        TreeNode rootNode = buildAncestorTree(root, generations, 0, allNodes, includeSpouses);

        // Calculate positions (bottom-up)
        calculatePositions(rootNode);

        // Find bounds
        int minX = allNodes.stream().mapToInt(n -> n.x).min().orElse(0);
        int maxX = allNodes.stream().mapToInt(n -> n.x + n.width).max().orElse(CARD_W);
        int minY = allNodes.stream().mapToInt(n -> n.y).min().orElse(0);
        int maxY = allNodes.stream().mapToInt(n -> n.y + CARD_H).max().orElse(CARD_H);

        // Add padding
        int padding = 40;
        int svgWidth = maxX - minX + padding * 2;
        int svgHeight = maxY - minY + padding * 2;

        // Offset all nodes so minX,minY becomes padding,padding
        int offsetX = padding - minX;
        int offsetY = padding - minY;
        for (TreeNode node : allNodes) {
            node.x += offsetX;
            node.y += offsetY;
        }

        // Build connector lines
        List<Line> lines = new ArrayList<>();
        buildLines(rootNode, lines);

        model.addAttribute("nodes", allNodes);
        model.addAttribute("lines", lines);
        model.addAttribute("svgWidth", svgWidth);
        model.addAttribute("svgHeight", svgHeight);
        model.addAttribute("showDates", showDates);
        model.addAttribute("rootPerson", root);

        return "tree-render";
    }

    private TreeNode buildAncestorTree(Person person, int maxGen, int currentGen,
                                        List<TreeNode> allNodes, boolean includeSpouses) {
        TreeNode node = new TreeNode();
        node.person = person;
        node.generation = currentGen;
        node.width = CARD_W;
        allNodes.add(node);

        // Add spouse if requested
        if (includeSpouses) {
            List<Person> spouses = personRepository.findSpouses(person.id());
            if (!spouses.isEmpty()) {
                node.spouse = spouses.get(0); // Just first spouse for simplicity
                node.width = CARD_W * 2 + SPOUSE_GAP;
            }
        }

        // Recursively build ancestors
        if (currentGen < maxGen) {
            if (person.motherId() != null) {
                personRepository.findById(person.motherId()).ifPresent(mother -> {
                    node.mother = buildAncestorTree(mother, maxGen, currentGen + 1, allNodes, includeSpouses);
                });
            }
            if (person.fatherId() != null) {
                personRepository.findById(person.fatherId()).ifPresent(father -> {
                    node.father = buildAncestorTree(father, maxGen, currentGen + 1, allNodes, includeSpouses);
                });
            }
        }

        return node;
    }

    private void calculatePositions(TreeNode node) {
        // Bottom-up: first position children, then position self based on children
        if (node.mother != null) calculatePositions(node.mother);
        if (node.father != null) calculatePositions(node.father);

        // Y position based on generation
        node.y = node.generation * (CARD_H + V_GAP);

        // X position based on parents
        if (node.mother == null && node.father == null) {
            // Leaf node - position will be set by parent's centering logic
            node.x = 0;
        } else if (node.mother != null && node.father != null) {
            // Both parents - center between them
            int motherCenter = node.mother.x + node.mother.width / 2;
            int fatherCenter = node.father.x + node.father.width / 2;
            int center = (motherCenter + fatherCenter) / 2;
            node.x = center - node.width / 2;

            // Make sure parents don't overlap
            int minGap = H_GAP;
            int motherRight = node.mother.x + node.mother.width;
            if (node.father.x < motherRight + minGap) {
                int shift = (motherRight + minGap - node.father.x) / 2;
                shiftSubtree(node.mother, -shift);
                shiftSubtree(node.father, shift);
                // Recalculate center
                motherCenter = node.mother.x + node.mother.width / 2;
                fatherCenter = node.father.x + node.father.width / 2;
                center = (motherCenter + fatherCenter) / 2;
                node.x = center - node.width / 2;
            }
        } else if (node.mother != null) {
            // Only mother
            node.x = node.mother.x + node.mother.width / 2 - node.width / 2;
        } else {
            // Only father
            node.x = node.father.x + node.father.width / 2 - node.width / 2;
        }
    }

    private void shiftSubtree(TreeNode node, int dx) {
        node.x += dx;
        if (node.mother != null) shiftSubtree(node.mother, dx);
        if (node.father != null) shiftSubtree(node.father, dx);
    }

    private void buildLines(TreeNode node, List<Line> lines) {
        int childCenterX = node.x + node.width / 2;
        int childTopY = node.y;

        if (node.mother != null) {
            int parentCenterX = node.mother.x + node.mother.width / 2;
            int parentBottomY = node.mother.y + CARD_H;
            lines.add(new Line(childCenterX, childTopY, parentCenterX, parentBottomY));
            buildLines(node.mother, lines);
        }

        if (node.father != null) {
            int parentCenterX = node.father.x + node.father.width / 2;
            int parentBottomY = node.father.y + CARD_H;
            lines.add(new Line(childCenterX, childTopY, parentCenterX, parentBottomY));
            buildLines(node.father, lines);
        }
    }

    // Inner classes for tree structure
    public static class TreeNode {
        public Person person;
        public Person spouse;
        public int x, y;
        public int width;
        public int generation;
        public TreeNode mother;
        public TreeNode father;

        // Getters for Thymeleaf
        public Person getPerson() { return person; }
        public Person getSpouse() { return spouse; }
        public int getX() { return x; }
        public int getY() { return y; }
        public int getWidth() { return width; }
        public int getCardWidth() { return CARD_W; }
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
