package com.familytree.controller;

import com.familytree.model.DnaMatch;
import com.familytree.repository.DnaMatchRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/matches")
public class DnaMatchApiController {

    private final DnaMatchRepository dnaMatchRepository;

    public DnaMatchApiController(DnaMatchRepository dnaMatchRepository) {
        this.dnaMatchRepository = dnaMatchRepository;
    }

    @GetMapping
    public ResponseEntity<List<DnaMatch>> getMatches(
            @RequestParam(name = "person_id", required = false) Long personId,
            @RequestParam(required = false) Double minCm,
            @RequestParam(defaultValue = "100") int limit) {

        List<DnaMatch> matches;

        if (personId != null) {
            matches = dnaMatchRepository.findByMatchedToPersonId(personId);
        } else if (minCm != null) {
            matches = dnaMatchRepository.findByMinCm(minCm, Math.min(limit, 500));
        } else {
            matches = dnaMatchRepository.findAll(Math.min(limit, 500));
        }

        return ResponseEntity.ok(matches);
    }
}