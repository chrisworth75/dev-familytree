package com.familytree.controller;

import com.familytree.model.CensusHousehold;
import com.familytree.model.DnaMatch;
import com.familytree.model.Person;
import com.familytree.model.Photo;
import com.familytree.model.PersonUrl;
import com.familytree.repository.DnaMatchRepository;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.PersonUrlRepository;
import com.familytree.service.CensusService;
import com.familytree.service.PersonService;
import com.familytree.service.PhotoService;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@RequestMapping({"/api/person", "/api/people"})
public class PersonApiController {

    private final PersonRepository personRepository;
    private final CensusService censusService;
    private final PersonUrlRepository personUrlRepository;
    private final PersonService personService;
    private final DnaMatchRepository dnaMatchRepository;
    private final PhotoService photoService;

    public PersonApiController(PersonRepository personRepository,
                               CensusService censusService,
                               PersonUrlRepository personUrlRepository,
                               PersonService personService,
                               DnaMatchRepository dnaMatchRepository,
                               PhotoService photoService) {
        this.personRepository = personRepository;
        this.censusService = censusService;
        this.personUrlRepository = personUrlRepository;
        this.personService = personService;
        this.dnaMatchRepository = dnaMatchRepository;
        this.photoService = photoService;
    }

    // ========== UPDATE/DELETE ==========

    @PutMapping("/{id}")
    public ResponseEntity<Map<String, Object>> updatePerson(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        return personService.updatePerson(id, body)
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
        return personService.addParent(id, body)
            .map(parent -> ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("id", parent.id(), "person", parent)))
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/child")
    public ResponseEntity<Map<String, Object>> addChild(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        String parentGender = (String) body.get("parentGender");
        return personService.addChild(id, body, parentGender)
            .map(child -> ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("id", child.id(), "person", child)))
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/spouse")
    public ResponseEntity<Map<String, Object>> addSpouse(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        return personService.addSpouse(id, body)
            .map(spouse -> ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("id", spouse.id(), "person", spouse)))
            .orElse(ResponseEntity.notFound().build());
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
                    ? personRepository.findById(person.motherId()).orElse(null) : null;
                Person father = person.fatherId() != null
                    ? personRepository.findById(person.fatherId()).orElse(null) : null;

                Map<String, Object> response = new LinkedHashMap<>();
                response.put("person", person);
                response.put("mother", mother);
                response.put("father", father);
                response.put("spouses", personRepository.findSpouses(id));
                response.put("children", personRepository.findChildren(id));
                response.put("siblings", personRepository.findSiblings(id));
                return ResponseEntity.ok(response);
            })
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/summary")
    public ResponseEntity<Map<String, Object>> getPersonSummary(@PathVariable Long id) {
        return personRepository.findById(id)
            .map(person -> {
                Person mother = person.motherId() != null
                    ? personRepository.findById(person.motherId()).orElse(null) : null;
                Person father = person.fatherId() != null
                    ? personRepository.findById(person.fatherId()).orElse(null) : null;

                DnaMatch match = dnaMatchRepository.findMatchByPersonId(id);

                Map<String, Object> response = new LinkedHashMap<>();
                response.put("person", person);
                response.put("mother", mother);
                response.put("father", father);
                response.put("spouses", personRepository.findSpouses(id));
                response.put("children", personRepository.findChildren(id));
                response.put("siblings", personRepository.findSiblings(id));
                response.put("match", match);
                response.put("ancestorCount", personRepository.countAncestors(id));
                response.put("descendantCount", personRepository.countDescendants(id));
                return ResponseEntity.ok(response);
            })
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/ancestors")
    public ResponseEntity<List<Person>> getAncestors(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int generations) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(personRepository.findAncestors(id, Math.min(generations, 20)));
    }

    @GetMapping("/{id}/descendants")
    public ResponseEntity<List<Person>> getDescendants(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int generations) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(personRepository.findDescendants(id, Math.min(generations, 20)));
    }

    @GetMapping("/search")
    public ResponseEntity<List<Person>> search(
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String birthPlace,
            @RequestParam(defaultValue = "false") boolean familyOnly,
            @RequestParam(defaultValue = "50") int limit) {
        if ((name == null || name.isBlank()) && (birthPlace == null || birthPlace.isBlank())) {
            return ResponseEntity.badRequest().build();
        }
        return ResponseEntity.ok(personRepository.search(name, birthPlace, familyOnly, Math.min(limit, 500)));
    }

    @GetMapping("/{id}/census")
    public ResponseEntity<List<CensusHousehold>> getCensusRecords(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(censusService.getCensusHouseholds(id));
    }

    @GetMapping("/{id}/siblings")
    public ResponseEntity<List<Person>> getSiblings(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(personRepository.findSiblings(id));
    }

    @GetMapping("/{id}/children")
    public ResponseEntity<List<Person>> getChildren(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(personRepository.findChildren(id));
    }

    @GetMapping("/{id}/spouses")
    public ResponseEntity<List<Person>> getSpouses(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(personRepository.findSpouses(id));
    }

    @GetMapping("/{id}/urls")
    public ResponseEntity<List<PersonUrl>> getUrls(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(personUrlRepository.findByPersonId(id));
    }

    @PostMapping("/{id}/urls")
    public ResponseEntity<Map<String, Object>> addUrl(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        Long urlId = personUrlRepository.save(id, (String) body.get("url"), (String) body.get("description"));
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of("id", urlId));
    }

    @DeleteMapping("/{id}/urls/{urlId}")
    public ResponseEntity<Void> deleteUrl(@PathVariable Long id, @PathVariable Long urlId) {
        personUrlRepository.delete(urlId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{id}/photos")
    public ResponseEntity<List<Photo>> getPhotos(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(photoService.getPhotosForPerson(id));
    }
}
