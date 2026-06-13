package com.familytree.controller;

import com.familytree.dto.PersonDetailDto;
import com.familytree.dto.PersonDto;
import com.familytree.dto.PersonRequest;
import com.familytree.model.CensusHousehold;
import com.familytree.model.Person;
import com.familytree.model.Photo;
import com.familytree.model.PersonUrl;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.PersonUrlRepository;
import com.familytree.service.CensusService;
import com.familytree.service.PersonService;
import com.familytree.service.PhotoService;
import jakarta.validation.Valid;
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
    private final PhotoService photoService;

    public PersonApiController(PersonRepository personRepository,
                               CensusService censusService,
                               PersonUrlRepository personUrlRepository,
                               PersonService personService,
                               PhotoService photoService) {
        this.personRepository = personRepository;
        this.censusService = censusService;
        this.personUrlRepository = personUrlRepository;
        this.personService = personService;
        this.photoService = photoService;
    }

    private static List<PersonDto> toDtos(List<Person> people) {
        return people.stream().map(PersonDto::from).toList();
    }

    // ========== UPDATE/DELETE ==========

    @PutMapping("/{id}")
    public ResponseEntity<Map<String, Object>> updatePerson(@PathVariable Long id, @Valid @RequestBody PersonRequest req) {
        return personService.updatePerson(id, req)
            .map(person -> ResponseEntity.ok(Map.of("id", id, "person", PersonDto.from(person))))
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
    public ResponseEntity<Map<String, Object>> addParent(@PathVariable Long id, @Valid @RequestBody PersonRequest req) {
        return personService.addParent(id, req)
            .map(parent -> ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("id", parent.id(), "person", PersonDto.from(parent))))
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/child")
    public ResponseEntity<Map<String, Object>> addChild(@PathVariable Long id, @Valid @RequestBody PersonRequest req) {
        return personService.addChild(id, req, req.parentGender())
            .map(child -> ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("id", child.id(), "person", PersonDto.from(child))))
            .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping("/{id}/spouse")
    public ResponseEntity<Map<String, Object>> addSpouse(@PathVariable Long id, @Valid @RequestBody PersonRequest req) {
        return personService.addSpouse(id, req)
            .map(spouse -> ResponseEntity.status(HttpStatus.CREATED)
                .body(Map.of("id", spouse.id(), "person", PersonDto.from(spouse))))
            .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}/spouse/{spouseId}")
    public ResponseEntity<Void> removeSpouse(@PathVariable Long id, @PathVariable Long spouseId) {
        personRepository.removeMarriage(id, spouseId);
        return ResponseEntity.noContent().build();
    }

    // ========== READ OPERATIONS ==========

    @GetMapping("/{id}")
    public ResponseEntity<PersonDetailDto> getPerson(@PathVariable Long id) {
        return personService.getPersonDetail(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/summary")
    public ResponseEntity<PersonDetailDto> getPersonSummary(@PathVariable Long id) {
        return personService.getPersonSummary(id)
            .map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/ancestors")
    public ResponseEntity<List<PersonDto>> getAncestors(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int generations) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(toDtos(personRepository.findAncestors(id, Math.min(generations, 20))));
    }

    @GetMapping("/{id}/descendants")
    public ResponseEntity<List<PersonDto>> getDescendants(
            @PathVariable Long id,
            @RequestParam(defaultValue = "10") int generations) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(toDtos(personRepository.findDescendants(id, Math.min(generations, 20))));
    }

    @GetMapping("/search")
    public ResponseEntity<List<PersonDto>> search(
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String birthPlace,
            @RequestParam(defaultValue = "false") boolean familyOnly,
            @RequestParam(defaultValue = "50") int limit) {
        if ((name == null || name.isBlank()) && (birthPlace == null || birthPlace.isBlank())) {
            return ResponseEntity.badRequest().build();
        }
        return ResponseEntity.ok(toDtos(personRepository.search(name, birthPlace, familyOnly, Math.min(limit, 500))));
    }

    @GetMapping("/{id}/census")
    public ResponseEntity<List<CensusHousehold>> getCensusRecords(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(censusService.getCensusHouseholds(id));
    }

    @GetMapping("/{id}/siblings")
    public ResponseEntity<List<PersonDto>> getSiblings(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(toDtos(personRepository.findSiblings(id)));
    }

    @GetMapping("/{id}/children")
    public ResponseEntity<List<PersonDto>> getChildren(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(toDtos(personRepository.findChildren(id)));
    }

    @GetMapping("/{id}/spouses")
    public ResponseEntity<List<PersonDto>> getSpouses(@PathVariable Long id) {
        if (personRepository.findById(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(toDtos(personRepository.findSpouses(id)));
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
