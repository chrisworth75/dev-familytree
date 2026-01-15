package com.familytree.controller;

import com.familytree.config.TreesConfig;
import com.familytree.model.FamilyTreeConfig;
import com.familytree.model.Person;
import com.familytree.repository.PersonRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping("/api/trees")
public class TreeApiController {

    private final TreesConfig treesConfig;
    private final PersonRepository personRepository;

    // Common female forenames for gender detection
    private static final Set<String> FEMALE_NAMES = Set.of(
        "mary", "alice", "constance", "blanche", "evelyn", "ethel", "jane",
        "margaret", "angela", "janet", "betty", "susan", "ann", "elizabeth",
        "doris", "marjorie", "patricia", "nina", "rachel", "verity", "kathleen",
        "muriel", "agnes", "sarah", "emma", "lily", "rose", "irene", "annie",
        "loreen", "betsy", "theodora", "maria", "ellen", "elsie", "grace",
        "rebecca", "jennifer", "helen", "florence", "mildred", "harriet",
        "martha", "matilda", "hannah", "sophia", "charlotte", "emily", "clara",
        "eliza", "nancy", "miriam", "lucy", "harriett"
    );

    public TreeApiController(TreesConfig treesConfig, PersonRepository personRepository) {
        this.treesConfig = treesConfig;
        this.personRepository = personRepository;
    }

    /**
     * Get tree hierarchy as nested JSON for D3.js visualization.
     * Returns the root person with all descendants nested as children.
     */
    @GetMapping("/{slug}/hierarchy")
    public ResponseEntity<Map<String, Object>> getTreeHierarchy(@PathVariable String slug) {
        FamilyTreeConfig tree = treesConfig.getTreeBySlug(slug);
        if (tree == null) {
            return ResponseEntity.notFound().build();
        }

        Long rootId = tree.rootPersonId();
        if (rootId == null) {
            return ResponseEntity.badRequest().build();
        }

        Optional<Person> rootOpt = personRepository.findById(rootId);
        if (rootOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        // Build the hierarchy recursively
        Map<String, Object> hierarchy = buildPersonNode(rootOpt.get(), new HashSet<>(), 15);
        return ResponseEntity.ok(hierarchy);
    }

    /**
     * Recursively build a person node with children.
     */
    private Map<String, Object> buildPersonNode(Person person, Set<Long> visited, int maxDepth) {
        if (visited.contains(person.id()) || maxDepth <= 0) {
            return null;
        }
        visited.add(person.id());

        Map<String, Object> node = new LinkedHashMap<>();
        node.put("id", person.id());
        node.put("name", formatName(person));
        node.put("dates", formatDates(person));
        node.put("gender", detectGender(person));
        node.put("birthPlace", person.birthPlace());

        // Get spouse info
        List<Person> spouses = personRepository.findSpouses(person.id());
        if (!spouses.isEmpty()) {
            Person spouse = spouses.get(0);
            node.put("spouse", formatName(spouse));
            node.put("spouseId", spouse.id());
        }

        // Get children and recursively build their nodes
        List<Person> children = personRepository.findChildren(person.id());
        if (!children.isEmpty()) {
            List<Map<String, Object>> childNodes = new ArrayList<>();
            for (Person child : children) {
                Map<String, Object> childNode = buildPersonNode(child, visited, maxDepth - 1);
                if (childNode != null) {
                    childNodes.add(childNode);
                }
            }
            // Sort by birth year
            childNodes.sort((a, b) -> {
                String datesA = (String) a.get("dates");
                String datesB = (String) b.get("dates");
                return datesA.compareTo(datesB);
            });
            if (!childNodes.isEmpty()) {
                node.put("children", childNodes);
            }
        }

        return node;
    }

    private String formatName(Person person) {
        String name = "";
        if (person.forename() != null) name += person.forename();
        if (person.surname() != null) name += " " + person.surname();
        return name.trim();
    }

    private String formatDates(Person person) {
        String dates = "";
        if (person.birthYearEstimate() != null) {
            dates += person.birthYearEstimate();
        }
        dates += "-";
        if (person.deathYearEstimate() != null) {
            dates += person.deathYearEstimate();
        }
        return dates;
    }

    private String detectGender(Person person) {
        if (person.forename() == null) return "U";
        String firstName = person.forename().toLowerCase().split(" ")[0];
        return FEMALE_NAMES.contains(firstName) ? "F" : "M";
    }
}
