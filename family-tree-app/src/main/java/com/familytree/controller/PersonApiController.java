package com.familytree.controller;

import com.familytree.model.CensusRecord;
import com.familytree.model.Person;
import com.familytree.model.PersonUrl;
import com.familytree.repository.CensusRepository;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.PersonUrlRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping({"/api/person", "/api/people"})
public class PersonApiController {

    private final PersonRepository personRepository;
    private final CensusRepository censusRepository;
    private final PersonUrlRepository personUrlRepository;

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

    public PersonApiController(PersonRepository personRepository, CensusRepository censusRepository, PersonUrlRepository personUrlRepository) {
        this.personRepository = personRepository;
        this.censusRepository = censusRepository;
        this.personUrlRepository = personUrlRepository;
    }

    // ========== UPDATE/DELETE ==========
    // Note: Person creation moved to POST /tree/{treeId}/person (see TreeApiController)

    @PutMapping("/{id}")
    public ResponseEntity<Map<String, Object>> updatePerson(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        String firstName = (String) body.get("firstName");
        if (firstName == null) firstName = (String) body.get("forename");
        String surname = (String) body.get("surname");
        Integer birthYear = body.get("birthYear") != null ? ((Number) body.get("birthYear")).intValue() : null;
        Integer deathYear = body.get("deathYear") != null ? ((Number) body.get("deathYear")).intValue() : null;
        String birthPlace = (String) body.get("birthPlace");

        personRepository.update(id, firstName, surname, birthYear, deathYear, birthPlace);

        return personRepository.findById(id)
            .map(person -> ResponseEntity.ok(Map.of("id", id, "person", person)))
            .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deletePerson(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        personRepository.delete(id);
        return ResponseEntity.noContent().build();
    }

    // ========== RELATIONSHIP MANAGEMENT ==========

    @PostMapping("/{id}/parent")
    public ResponseEntity<Map<String, Object>> addParent(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        Person child = personRepository.findById(id).orElse(null);
        if (child == null) {
            return ResponseEntity.notFound().build();
        }

        String gender = (String) body.get("gender");
        Long existingParentId = body.get("parentId") != null ? ((Number) body.get("parentId")).longValue() : null;

        Long parentId;
        if (existingParentId != null) {
            parentId = existingParentId;
        } else {
            String firstName = (String) body.get("firstName");
            if (firstName == null) firstName = (String) body.get("forename");
            String surname = (String) body.get("surname");
            Integer birthYear = body.get("birthYear") != null ? ((Number) body.get("birthYear")).intValue() : null;
            // Inherit tree_id from child
            parentId = personRepository.save(firstName, surname, birthYear, null, null, null, null, child.treeId());
        }

        // Update child's parent reference
        if ("F".equalsIgnoreCase(gender)) {
            // Female parent = parent_2_id (mother)
            personRepository.updateParents(id, child.fatherId(), parentId);
        } else {
            // Male parent = parent_1_id (father)
            personRepository.updateParents(id, parentId, child.motherId());
        }

        return personRepository.findById(parentId)
            .map(parent -> ResponseEntity.status(HttpStatus.CREATED).body(Map.of("id", parentId, "person", parent)))
            .orElse(ResponseEntity.internalServerError().build());
    }

    @PostMapping("/{id}/child")
    public ResponseEntity<Map<String, Object>> addChild(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        Person parent = personRepository.findById(id).orElse(null);
        if (parent == null) {
            return ResponseEntity.notFound().build();
        }

        Long existingChildId = body.get("childId") != null ? ((Number) body.get("childId")).longValue() : null;
        String parentGender = (String) body.get("parentGender");

        Long childId;
        if (existingChildId != null) {
            childId = existingChildId;
        } else {
            String firstName = (String) body.get("firstName");
            if (firstName == null) firstName = (String) body.get("forename");
            String surname = (String) body.get("surname");
            Integer birthYear = body.get("birthYear") != null ? ((Number) body.get("birthYear")).intValue() : null;

            Long parent1Id = "M".equalsIgnoreCase(parentGender) ? id : null;
            Long parent2Id = "F".equalsIgnoreCase(parentGender) ? id : null;

            // Inherit tree_id from parent
            childId = personRepository.save(firstName, surname, birthYear, null, null, parent1Id, parent2Id, parent.treeId());
        }

        // If linking existing child, update their parent reference
        if (existingChildId != null) {
            Person child = personRepository.findById(childId).get();
            if ("F".equalsIgnoreCase(parentGender)) {
                personRepository.updateParents(childId, child.fatherId(), id);
            } else {
                personRepository.updateParents(childId, id, child.motherId());
            }
        }

        return personRepository.findById(childId)
            .map(child -> ResponseEntity.status(HttpStatus.CREATED).body(Map.of("id", childId, "person", child)))
            .orElse(ResponseEntity.internalServerError().build());
    }

    @PostMapping("/{id}/spouse")
    public ResponseEntity<Map<String, Object>> addSpouse(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        Person person = personRepository.findById(id).orElse(null);
        if (person == null) {
            return ResponseEntity.notFound().build();
        }

        Long existingSpouseId = body.get("spouseId") != null ? ((Number) body.get("spouseId")).longValue() : null;

        Long spouseId;
        if (existingSpouseId != null) {
            spouseId = existingSpouseId;
        } else {
            String firstName = (String) body.get("firstName");
            if (firstName == null) firstName = (String) body.get("forename");
            String surname = (String) body.get("surname");
            Integer birthYear = body.get("birthYear") != null ? ((Number) body.get("birthYear")).intValue() : null;
            // Inherit tree_id from person
            spouseId = personRepository.save(firstName, surname, birthYear, null, null, null, null, person.treeId());
        }

        personRepository.addMarriage(id, spouseId);

        return personRepository.findById(spouseId)
            .map(spouse -> ResponseEntity.status(HttpStatus.CREATED).body(Map.of("id", spouseId, "person", spouse)))
            .orElse(ResponseEntity.internalServerError().build());
    }

    @DeleteMapping("/{id}/spouse/{spouseId}")
    public ResponseEntity<Void> removeSpouse(@PathVariable Long id, @PathVariable Long spouseId) {
        personRepository.removeMarriage(id, spouseId);
        return ResponseEntity.noContent().build();
    }

    // ========== READ OPERATIONS ==========

    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getPerson(@PathVariable Long id) {
        return personRepository.findById(id)
            .map(person -> {
                Person mother = person.motherId() != null
                    ? personRepository.findById(person.motherId()).orElse(null)
                    : null;
                Person father = person.fatherId() != null
                    ? personRepository.findById(person.fatherId()).orElse(null)
                    : null;
                List<Person> children = personRepository.findChildren(id);
                List<Person> spouses = personRepository.findSpouses(id);
                List<Person> siblings = personRepository.findSiblings(id);

                Map<String, Object> response = new java.util.LinkedHashMap<>();
                response.put("person", person);
                response.put("mother", mother);
                response.put("father", father);
                response.put("spouses", spouses);
                response.put("children", children);
                response.put("siblings", siblings);

                return ResponseEntity.ok(response);
            })
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/ancestors")
    public ResponseEntity<List<Person>> getAncestors(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int generations) {

        if (!personRepository.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }

        int maxGen = Math.min(generations, 20);
        List<Person> ancestors = personRepository.findAncestors(id, maxGen);
        return ResponseEntity.ok(ancestors);
    }

    @GetMapping("/{id}/descendants")
    public ResponseEntity<List<Person>> getDescendants(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int generations) {

        if (!personRepository.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }

        int maxGen = Math.min(generations, 20);
        List<Person> descendants = personRepository.findDescendants(id, maxGen);
        return ResponseEntity.ok(descendants);
    }

    @GetMapping("/search")
    public ResponseEntity<List<Person>> search(
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String birthPlace,
            @RequestParam(defaultValue = "50") int limit) {

        if ((name == null || name.isBlank()) && (birthPlace == null || birthPlace.isBlank())) {
            return ResponseEntity.badRequest().build();
        }

        int maxLimit = Math.min(limit, 500);
        List<Person> results = personRepository.search(name, birthPlace, maxLimit);
        return ResponseEntity.ok(results);
    }

    @GetMapping("/{id}/census")
    public ResponseEntity<List<CensusRecord>> getCensusRecords(@PathVariable Long id) {
        if (!personRepository.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }

        List<CensusRecord> records = censusRepository.findByPersonId(id);
        return ResponseEntity.ok(records);
    }

    @GetMapping("/{id}/siblings")
    public ResponseEntity<List<Person>> getSiblings(@PathVariable Long id) {
        if (!personRepository.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }

        List<Person> siblings = personRepository.findSiblings(id);
        return ResponseEntity.ok(siblings);
    }

    @GetMapping("/{id}/children")
    public ResponseEntity<List<Person>> getChildren(@PathVariable Long id) {
        if (!personRepository.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }

        List<Person> children = personRepository.findChildren(id);
        return ResponseEntity.ok(children);
    }

    @GetMapping("/{id}/spouses")
    public ResponseEntity<List<Person>> getSpouses(@PathVariable Long id) {
        if (!personRepository.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }

        List<Person> spouses = personRepository.findSpouses(id);
        return ResponseEntity.ok(spouses);
    }

    @GetMapping("/{id}/urls")
    public ResponseEntity<List<PersonUrl>> getUrls(@PathVariable Long id) {
        if (!personRepository.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }

        List<PersonUrl> urls = personUrlRepository.findByPersonId(id);
        return ResponseEntity.ok(urls);
    }

    @PostMapping("/{id}/urls")
    public ResponseEntity<Map<String, Object>> addUrl(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        if (!personRepository.findById(id).isPresent()) {
            return ResponseEntity.notFound().build();
        }

        String url = (String) body.get("url");
        String description = (String) body.get("description");

        Long urlId = personUrlRepository.save(id, url, description);
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of("id", urlId));
    }

    @DeleteMapping("/{id}/urls/{urlId}")
    public ResponseEntity<Void> deleteUrl(@PathVariable Long id, @PathVariable Long urlId) {
        personUrlRepository.delete(urlId);
        return ResponseEntity.noContent().build();
    }

    // ========== HIERARCHICAL DESCENDANTS ==========

    /**
     * Get descendants as nested hierarchical JSON (same format as /api/trees/{slug}/hierarchy).
     */
    @GetMapping("/{id}/descendants/hierarchy")
    public ResponseEntity<Map<String, Object>> getDescendantsHierarchy(
            @PathVariable Long id,
            @RequestParam(defaultValue = "15") int maxDepth) {

        Optional<Person> rootOpt = personRepository.findById(id);
        if (rootOpt.isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        int depth = Math.min(maxDepth, 20);
        Map<String, Object> hierarchy = buildPersonNode(rootOpt.get(), new HashSet<>(), depth);
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
        node.put("name", person.displayName());
        node.put("dates", formatDates(person));
        node.put("gender", detectGender(person));

        // Get spouse info
        List<Person> spouses = personRepository.findSpouses(person.id());
        if (!spouses.isEmpty()) {
            Person spouse = spouses.get(0);
            node.put("spouse", spouse.displayName());
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
        if (person.gender() != null && !person.gender().isBlank()) {
            return person.gender();
        }
        if (person.firstName() == null) return "U";
        String firstName = person.firstName().toLowerCase().split(" ")[0];
        return FEMALE_NAMES.contains(firstName) ? "F" : "M";
    }
}
