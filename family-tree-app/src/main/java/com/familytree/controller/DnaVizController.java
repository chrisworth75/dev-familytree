package com.familytree.controller;

import com.familytree.model.DnaMatch;
import com.familytree.repository.DnaMatchRepository;
import com.familytree.service.DnaVizService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/person/{personId}/dna-viz")
public class DnaVizController {

    private static final MediaType SVG_MEDIA_TYPE = MediaType.valueOf("image/svg+xml");

    private final DnaMatchRepository dnaMatchRepository;
    private final DnaVizService dnaVizService;

    public DnaVizController(DnaMatchRepository dnaMatchRepository, DnaVizService dnaVizService) {
        this.dnaMatchRepository = dnaMatchRepository;
        this.dnaVizService = dnaVizService;
    }

    private DnaMatch lookupMatch(Long personId) {
        return dnaMatchRepository.findMatchByPersonId(personId);
    }

    @GetMapping("/chromo-bar")
    public ResponseEntity<String> chromoBar(@PathVariable Long personId,
                                            @RequestParam(defaultValue = "320") int width) {
        DnaMatch match = lookupMatch(personId);
        if (match == null) {
            return ResponseEntity.notFound().build();
        }
        String svg = dnaVizService.generateChromoBar(
                match.sharedCm().doubleValue(),
                match.predictedRelationship(),
                match.sharedSegments(),
                width);
        return ResponseEntity.ok().contentType(SVG_MEDIA_TYPE).body(svg);
    }

    @GetMapping("/strand")
    public ResponseEntity<String> strand(@PathVariable Long personId) {
        DnaMatch match = lookupMatch(personId);
        if (match == null) {
            return ResponseEntity.notFound().build();
        }
        String svg = dnaVizService.generateStrandCompact(
                match.sharedCm().doubleValue(),
                match.predictedRelationship());
        return ResponseEntity.ok().contentType(SVG_MEDIA_TYPE).body(svg);
    }
}
