package com.familytree.controller;

import com.familytree.model.CensusRecord;
import com.familytree.model.Person;
import com.familytree.repository.CensusRepository;
import com.familytree.repository.PersonRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/persons")
public class PersonApiController {

    private final PersonRepository personRepository;
    private final CensusRepository censusRepository;

    public PersonApiController(PersonRepository personRepository, CensusRepository censusRepository) {
        this.personRepository = personRepository;
        this.censusRepository = censusRepository;
    }

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

        int maxGen = Math.min(generations, 20); // Cap at 20 generations
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

        int maxGen = Math.min(generations, 20); // Cap at 20 generations
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

        int maxLimit = Math.min(limit, 500); // Cap at 500 results
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
}
