package com.familytree.controller;

import com.familytree.model.CensusRecord;
import com.familytree.model.Person;
import com.familytree.model.PersonUrl;
import com.familytree.repository.CensusRepository;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.PersonUrlRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/persons")
public class PersonApiController {

    private final PersonRepository personRepository;
    private final CensusRepository censusRepository;
    private final PersonUrlRepository personUrlRepository;

    public PersonApiController(PersonRepository personRepository, CensusRepository censusRepository, PersonUrlRepository personUrlRepository) {
        this.personRepository = personRepository;
        this.censusRepository = censusRepository;
        this.personUrlRepository = personUrlRepository;
    }

    // ========== CREATE/UPDATE/DELETE ==========

    @PostMapping
    public ResponseEntity<Map<String, Object>> createPerson(@RequestBody Map<String, Object> body) {
        String firstName = (String) body.get("firstName");
        if (firstName == null) firstName = (String) body.get("forename"); // backwards compat
        String surname = (String) body.get("surname");
        Integer birthYear = body.get("birthYear") != null ? ((Number) body.get("birthYear")).intValue() : null;
        Integer deathYear = body.get("deathYear") != null ? ((Number) body.get("deathYear")).intValue() : null;
        String birthPlace = (String) body.get("birthPlace");
        Long parent1Id = body.get("parent1Id") != null ? ((Number) body.get("parent1Id")).longValue() : null;
        if (parent1Id == null) parent1Id = body.get("fatherId") != null ? ((Number) body.get("fatherId")).longValue() : null;
        Long parent2Id = body.get("parent2Id") != null ? ((Number) body.get("parent2Id")).longValue() : null;
        if (parent2Id == null) parent2Id = body.get("motherId") != null ? ((Number) body.get("motherId")).longValue() : null;

        Long id = personRepository.save(firstName, surname, birthYear, deathYear, birthPlace, parent1Id, parent2Id);

        return personRepository.findById(id)
            .map(person -> ResponseEntity.ok(Map.of("id", id, "person", person)))
            .orElse(ResponseEntity.internalServerError().build());
    }

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
        if (personRepository.findById(id).isEmpty()) {
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
            parentId = personRepository.save(firstName, surname, birthYear, null, null, null, null);
        }

        // Update child's parent reference
        Person child = personRepository.findById(id).get();
        if ("F".equalsIgnoreCase(gender)) {
            // Female parent = parent_2_id (mother)
            personRepository.updateParents(id, child.fatherId(), parentId);
        } else {
            // Male parent = parent_1_id (father)
            personRepository.updateParents(id, parentId, child.motherId());
        }

        return personRepository.findById(parentId)
            .map(parent -> ResponseEntity.ok(Map.of("id", parentId, "person", parent)))
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

            childId = personRepository.save(firstName, surname, birthYear, null, null, parent1Id, parent2Id);
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
            .map(child -> ResponseEntity.ok(Map.of("id", childId, "person", child)))
            .orElse(ResponseEntity.internalServerError().build());
    }

    @PostMapping("/{id}/spouse")
    public ResponseEntity<Map<String, Object>> addSpouse(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        if (personRepository.findById(id).isEmpty()) {
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
            spouseId = personRepository.save(firstName, surname, birthYear, null, null, null, null);
        }

        personRepository.addMarriage(id, spouseId);

        return personRepository.findById(spouseId)
            .map(spouse -> ResponseEntity.ok(Map.of("id", spouseId, "person", spouse)))
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
        return ResponseEntity.ok(Map.of("id", urlId));
    }

    @DeleteMapping("/{id}/urls/{urlId}")
    public ResponseEntity<Void> deleteUrl(@PathVariable Long id, @PathVariable Long urlId) {
        personUrlRepository.delete(urlId);
        return ResponseEntity.noContent().build();
    }
}
