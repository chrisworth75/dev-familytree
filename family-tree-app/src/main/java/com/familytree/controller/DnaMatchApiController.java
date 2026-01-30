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
            @RequestParam(required = false) Double minCm,
            @RequestParam(required = false) String side,
            @RequestParam(required = false) Boolean linked,
            @RequestParam(defaultValue = "100") int limit) {

        List<DnaMatch> matches;
        int maxLimit = Math.min(limit, 500);

        if (minCm != null) {
            matches = dnaMatchRepository.findByMinCm(minCm, maxLimit);
        } else if (side != null) {
            matches = dnaMatchRepository.findByMatchSide(side, maxLimit);
        } else if (Boolean.TRUE.equals(linked)) {
            matches = dnaMatchRepository.findLinked(maxLimit);
        } else {
            matches = dnaMatchRepository.findAll(maxLimit);
        }

        return ResponseEntity.ok(matches);
    }
}
