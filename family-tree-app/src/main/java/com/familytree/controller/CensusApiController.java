package com.familytree.controller;

import com.familytree.model.CensusRecord;
import com.familytree.repository.CensusRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/census")
public class CensusApiController {

    private final CensusRepository censusRepository;

    public CensusApiController(CensusRepository censusRepository) {
        this.censusRepository = censusRepository;
    }

    @GetMapping("/search")
    public ResponseEntity<List<CensusRecord>> searchBySurname(
            @RequestParam String surname,
            @RequestParam(required = false) Integer year,
            @RequestParam(defaultValue = "50") int limit) {

        if (surname == null || surname.isBlank()) {
            return ResponseEntity.badRequest().build();
        }

        List<CensusRecord> results = censusRepository.searchBySurname(surname, year, limit);
        return ResponseEntity.ok(results);
    }
}
