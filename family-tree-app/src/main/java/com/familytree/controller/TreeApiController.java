package com.familytree.controller;

import com.familytree.model.Tree;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.TreeRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/tree")
public class TreeApiController {

    private final PersonRepository personRepository;
    private final TreeRepository treeRepository;

    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.ofPattern("dd MM yyyy");

    public TreeApiController(PersonRepository personRepository, TreeRepository treeRepository) {
        this.personRepository = personRepository;
        this.treeRepository = treeRepository;
    }

    // ========== TREE CRUD ==========

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

        Long id = savePerson(body, treeId.intValue());

        return personRepository.findById(id)
                .map(person -> ResponseEntity.status(HttpStatus.CREATED)
                        .body(Map.of("id", id, "person", person)))
                .orElse(ResponseEntity.internalServerError().build());
    }

    private Long savePerson(Map<String, Object> body, Integer treeId) {
        Long id = body.get("id") != null ? ((Number) body.get("id")).longValue() : null;
        String firstName = (String) body.get("firstName");
        if (firstName == null) firstName = (String) body.get("forename");
        String middleNames = (String) body.get("middleNames");
        String surname = (String) body.get("surname");
        String birthSurname = (String) body.get("birthSurname");
        String birthPlace = (String) body.get("birthPlace");
        String deathPlace = (String) body.get("deathPlace");
        String gender = (String) body.get("gender");
        String notes = (String) body.get("notes");

        LocalDate birthDate = parseDate((String) body.get("birthDate"));
        Integer birthYear = birthDate == null && body.get("birthYear") != null
                ? ((Number) body.get("birthYear")).intValue() : null;
        LocalDate deathDate = parseDate((String) body.get("deathDate"));
        Integer deathYear = deathDate == null && body.get("deathYear") != null
                ? ((Number) body.get("deathYear")).intValue() : null;

        Long fatherId = body.get("fatherId") != null ? ((Number) body.get("fatherId")).longValue() : null;
        Long motherId = body.get("motherId") != null ? ((Number) body.get("motherId")).longValue() : null;

        return personRepository.save(id, firstName, middleNames, surname, birthSurname,
                birthDate, birthYear, birthPlace,
                deathDate, deathYear, deathPlace,
                gender, notes, fatherId, motherId, treeId);
    }

    private LocalDate parseDate(String dateStr) {
        if (dateStr == null || dateStr.isBlank()) return null;
        try {
            return LocalDate.parse(dateStr, DATE_FORMAT);
        } catch (Exception e) {
            return null;
        }
    }
}
