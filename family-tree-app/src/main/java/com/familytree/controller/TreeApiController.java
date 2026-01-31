package com.familytree.controller;

import com.familytree.config.TreesConfig;
import com.familytree.model.FamilyTreeConfig;
import com.familytree.model.Person;
import com.familytree.model.Tree;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.TreeRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.*;

@RestController
@RequestMapping("/api/tree")
public class TreeApiController {

    private final TreesConfig treesConfig;
    private final PersonRepository personRepository;
    private final TreeRepository treeRepository;

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

    public TreeApiController(TreesConfig treesConfig, PersonRepository personRepository,
                            TreeRepository treeRepository) {
        this.treesConfig = treesConfig;
        this.personRepository = personRepository;
        this.treeRepository = treeRepository;
    }

    // ========== DATABASE TREE CRUD ==========

    @GetMapping
    public ResponseEntity<List<Tree>> getAllTrees() {
        return ResponseEntity.ok(treeRepository.findAll());
    }

    @GetMapping("/db/{id}")
    public ResponseEntity<Tree> getTreeById(@PathVariable Long id) {
        return treeRepository.findById(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Tree> createTree(@RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String source = (String) body.get("source");
        String ownerName = (String) body.get("ownerName");
        String notes = (String) body.get("notes");
        String dnaTestId = (String) body.get("dnaTestId");
        Long ancestryTreeId = body.get("ancestryTreeId") != null
            ? ((Number) body.get("ancestryTreeId")).longValue() : null;
        Integer size = body.get("size") != null
            ? ((Number) body.get("size")).intValue() : null;

        Long id = treeRepository.save(name, source, ownerName, notes, dnaTestId, ancestryTreeId, size);

        return treeRepository.findById(id)
            .map(tree -> ResponseEntity.status(HttpStatus.CREATED).body(tree))
            .orElse(ResponseEntity.internalServerError().build());
    }

    @DeleteMapping("/db/{id}")
    public ResponseEntity<Void> deleteTree(@PathVariable Long id) {
        if (treeRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        treeRepository.delete(id);
        return ResponseEntity.noContent().build();
    }

    // ========== PERSON UNDER TREE ==========

    @PostMapping("/{treeId}/person")
    public ResponseEntity<Map<String, Object>> createPersonInTree(
            @PathVariable Long treeId,
            @RequestBody Map<String, Object> body) {

        if (treeRepository.findById(treeId).isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        String firstName = (String) body.get("firstName");
        if (firstName == null) firstName = (String) body.get("forename");
        String surname = (String) body.get("surname");
        Integer birthYear = body.get("birthYear") != null ? ((Number) body.get("birthYear")).intValue() : null;
        Integer deathYear = body.get("deathYear") != null ? ((Number) body.get("deathYear")).intValue() : null;
        String birthPlace = (String) body.get("birthPlace");

        Long id = personRepository.save(firstName, surname, birthYear, deathYear, birthPlace, null, null, treeId.intValue());

        return personRepository.findById(id)
            .map(person -> ResponseEntity.status(HttpStatus.CREATED).body(Map.of("id", id, "person", person)))
            .orElse(ResponseEntity.internalServerError().build());
    }

    // ========== TREE VISUALIZATION ==========

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
        return person.displayName();
    }

    private String formatDates(Person person) {
        String dates = "";
        if (person.birthYear() != null) {
            dates += person.birthYear();
        }
        dates += "-";
        if (person.deathYear() != null) {
            dates += person.deathYear();
        }
        return dates;
    }

    private String detectGender(Person person) {
        // Use database gender if set
        if (person.gender() != null && !person.gender().isBlank()) {
            return person.gender();
        }
        // Fall back to name detection
        if (person.firstName() == null) return "U";
        String firstName = person.firstName().toLowerCase().split(" ")[0];
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

        // Ensure all relatives of people in the map are also collected
        // This handles cases where processing might skip some relatives
        Set<Long> idsToProcess = new HashSet<>(peopleMap.keySet());
        for (Long personId : idsToProcess) {
            Person person = peopleMap.get(personId);
            if (person != null) {
                // Get children and add them if not already in map
                List<Person> children = personRepository.findChildren(personId);
                for (Person child : children) {
                    if (!peopleMap.containsKey(child.id())) {
                        collectPeople(child, peopleMap, 10);
                    }
                }
                // Get spouses and add them if not already in map
                List<Person> spouses = personRepository.findSpouses(personId);
                for (Person spouse : spouses) {
                    if (!peopleMap.containsKey(spouse.id())) {
                        peopleMap.put(spouse.id(), spouse);
                    }
                }
                // Get ancestors and add them if not already in map
                collectAncestors(person, peopleMap, 10);
            }
        }

        // Second pass to ensure ancestors' siblings are included
        idsToProcess = new HashSet<>(peopleMap.keySet());
        for (Long personId : idsToProcess) {
            Person person = peopleMap.get(personId);
            if (person != null) {
                List<Person> siblings = personRepository.findSiblings(personId);
                for (Person sibling : siblings) {
                    if (!peopleMap.containsKey(sibling.id())) {
                        collectPeople(sibling, peopleMap, 10);
                    }
                }
            }
        }

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

        // Add siblings (including half-siblings) and their descendants
        List<Person> siblings = personRepository.findSiblings(person.id());
        for (Person sibling : siblings) {
            if (!peopleMap.containsKey(sibling.id())) {
                // Recursively collect sibling and their descendants
                collectPeople(sibling, peopleMap, depth - 1);
            }
        }

        // Add spouses and their shared children
        List<Person> spouses = personRepository.findSpouses(person.id());
        for (Person spouse : spouses) {
            if (!peopleMap.containsKey(spouse.id())) {
                peopleMap.put(spouse.id(), spouse);
                // Also collect spouse's ancestors
                collectAncestors(spouse, peopleMap, depth - 1);
                // Also collect spouse's siblings
                List<Person> spouseSiblings = personRepository.findSiblings(spouse.id());
                for (Person sibling : spouseSiblings) {
                    if (!peopleMap.containsKey(sibling.id())) {
                        peopleMap.put(sibling.id(), sibling);
                    }
                }
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

        // Add mother (parent_2) and her ancestors
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

        // Add father (parent_1) and his ancestors
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
        if (person.firstName() != null) data.put("first name", person.firstName());
        if (person.surname() != null) data.put("last name", person.surname());
        if (person.birthYear() != null) data.put("birthday", String.valueOf(person.birthYear()));
        if (person.deathYear() != null) data.put("deathday", String.valueOf(person.deathYear()));
        if (person.birthPlace() != null) data.put("birthPlace", person.birthPlace());
        if (person.notes() != null) data.put("bio", person.notes());
        data.put("db_id", person.id());  // Include database ID for API lookups

        // Check if this person is a DNA match and add shared cM
        Double sharedCm = personRepository.findDnaMatchCm(person.id());
        if (sharedCm != null && sharedCm > 0) {
            data.put("shared_cm", String.format("%.0f cM", sharedCm));
        }
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
