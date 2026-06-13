package com.familytree.controller;

import com.familytree.dto.CreateTreeRequest;
import com.familytree.dto.PersonDto;
import com.familytree.dto.PersonRequest;
import com.familytree.dto.TreeDto;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.TreeRepository;
import com.familytree.service.PersonService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/tree")
public class TreeApiController {

    private final PersonRepository personRepository;
    private final TreeRepository treeRepository;
    private final PersonService personService;

    public TreeApiController(PersonRepository personRepository, TreeRepository treeRepository,
                             PersonService personService) {
        this.personRepository = personRepository;
        this.treeRepository = treeRepository;
        this.personService = personService;
    }

    // ========== TREE CRUD ==========

    @GetMapping
    public ResponseEntity<List<TreeDto>> getAllTrees() {
        return ResponseEntity.ok(treeRepository.findAll().stream().map(TreeDto::from).toList());
    }

    @GetMapping("/db/{id}")
    public ResponseEntity<TreeDto> getTreeById(@PathVariable Long id) {
        return treeRepository.findById(id)
                .map(tree -> ResponseEntity.ok(TreeDto.from(tree)))
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<TreeDto> createTree(@Valid @RequestBody CreateTreeRequest req) {
        Long id = treeRepository.save(req.name(), req.source(), req.ownerName(), req.notes(),
                req.dnaTestId(), req.ancestryTreeId(), req.size());

        return treeRepository.findById(id)
                .map(tree -> ResponseEntity.status(HttpStatus.CREATED).body(TreeDto.from(tree)))
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
            @Valid @RequestBody PersonRequest req) {

        if (treeRepository.findById(treeId).isEmpty()) {
            return ResponseEntity.notFound().build();
        }

        Long id = personService.createPerson(req, req.fatherId(), req.motherId(), treeId.intValue());

        return personRepository.findById(id)
                .map(person -> ResponseEntity.status(HttpStatus.CREATED)
                        .body(Map.of("id", id, "person", PersonDto.from(person))))
                .orElse(ResponseEntity.internalServerError().build());
    }
}
