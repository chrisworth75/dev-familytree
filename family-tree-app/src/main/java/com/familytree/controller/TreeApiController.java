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

    /**
     * Get tree data in family-chart format (flat array with bidirectional relationships).
     * This format is compatible with the family-chart library (https://github.com/donatso/family-chart).
     */
    @GetMapping("/{slug}/family-chart")
    public ResponseEntity<List<Map<String, Object>>> getFamilyChartData(
            @PathVariable String slug,
            @RequestParam(defaultValue = "15") int maxDepth) {

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

        // Collect all people in the tree
        Map<Long, Person> peopleMap = new LinkedHashMap<>();
        collectPeople(rootOpt.get(), peopleMap, Math.min(maxDepth, 20));

        // Build family-chart format
        List<Map<String, Object>> result = new ArrayList<>();
        for (Person person : peopleMap.values()) {
            result.add(buildFamilyChartNode(person, peopleMap));
        }

        return ResponseEntity.ok(result);
    }

    /**
     * Recursively collect all people in the tree (ancestors, descendants, and their spouses).
     */
    private void collectPeople(Person person, Map<Long, Person> peopleMap, int depth) {
        if (person == null || peopleMap.containsKey(person.id()) || depth <= 0) {
            return;
        }
        peopleMap.put(person.id(), person);

        // Add spouses
        List<Person> spouses = personRepository.findSpouses(person.id());
        for (Person spouse : spouses) {
            if (!peopleMap.containsKey(spouse.id())) {
                peopleMap.put(spouse.id(), spouse);
                // Also collect spouse's ancestors
                collectAncestors(spouse, peopleMap, depth - 1);
            }
        }

        // Recursively add ancestors
        collectAncestors(person, peopleMap, depth);

        // Recursively add children
        List<Person> children = personRepository.findChildren(person.id());
        for (Person child : children) {
            collectPeople(child, peopleMap, depth - 1);
        }
    }

    /**
     * Recursively collect ancestors (parents, grandparents, etc.)
     */
    private void collectAncestors(Person person, Map<Long, Person> peopleMap, int depth) {
        if (person == null || depth <= 0) {
            return;
        }

        // Add mother and her ancestors
        if (person.motherId() != null && !peopleMap.containsKey(person.motherId())) {
            personRepository.findById(person.motherId()).ifPresent(mother -> {
                peopleMap.put(mother.id(), mother);
                // Add mother's spouse (father of person, if different)
                List<Person> motherSpouses = personRepository.findSpouses(mother.id());
                for (Person spouse : motherSpouses) {
                    if (!peopleMap.containsKey(spouse.id())) {
                        peopleMap.put(spouse.id(), spouse);
                    }
                }
                collectAncestors(mother, peopleMap, depth - 1);
            });
        }

        // Add father and his ancestors
        if (person.fatherId() != null && !peopleMap.containsKey(person.fatherId())) {
            personRepository.findById(person.fatherId()).ifPresent(father -> {
                peopleMap.put(father.id(), father);
                // Add father's spouse (mother of person, if different)
                List<Person> fatherSpouses = personRepository.findSpouses(father.id());
                for (Person spouse : fatherSpouses) {
                    if (!peopleMap.containsKey(spouse.id())) {
                        peopleMap.put(spouse.id(), spouse);
                    }
                }
                collectAncestors(father, peopleMap, depth - 1);
            });
        }
    }

    /**
     * Build a single person node in family-chart format.
     */
    private Map<String, Object> buildFamilyChartNode(Person person, Map<Long, Person> peopleMap) {
        Map<String, Object> node = new LinkedHashMap<>();
        node.put("id", String.valueOf(person.id()));

        // Data object
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("gender", detectGender(person));
        if (person.forename() != null) data.put("first name", person.forename());
        if (person.surname() != null) data.put("last name", person.surname());
        if (person.birthYearEstimate() != null) data.put("birthday", String.valueOf(person.birthYearEstimate()));
        if (person.deathYearEstimate() != null) data.put("deathday", String.valueOf(person.deathYearEstimate()));
        if (person.birthPlace() != null) data.put("birthPlace", person.birthPlace());
        data.put("db_id", person.id());  // Include database ID for API lookups
        node.put("data", data);

        // Relationships object
        Map<String, Object> rels = new LinkedHashMap<>();

        // Parents (only include if they're in the tree)
        List<String> parentIds = new ArrayList<>();
        if (person.motherId() != null && peopleMap.containsKey(person.motherId())) {
            parentIds.add(String.valueOf(person.motherId()));
        }
        if (person.fatherId() != null && peopleMap.containsKey(person.fatherId())) {
            parentIds.add(String.valueOf(person.fatherId()));
        }
        if (!parentIds.isEmpty()) {
            rels.put("parents", parentIds);
        }

        // Spouses (only include if they're in the tree)
        List<Person> spouses = personRepository.findSpouses(person.id());
        List<String> spouseIds = spouses.stream()
            .filter(s -> peopleMap.containsKey(s.id()))
            .map(s -> String.valueOf(s.id()))
            .toList();
        if (!spouseIds.isEmpty()) {
            rels.put("spouses", spouseIds);
        }

        // Children (only include if they're in the tree)
        List<Person> children = personRepository.findChildren(person.id());
        List<String> childIds = children.stream()
            .filter(c -> peopleMap.containsKey(c.id()))
            .map(c -> String.valueOf(c.id()))
            .toList();
        if (!childIds.isEmpty()) {
            rels.put("children", childIds);
        }

        node.put("rels", rels);
        return node;
    }
}
