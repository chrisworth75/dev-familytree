package com.familytree.controller;

import com.familytree.model.DnaMatch;
import com.familytree.repository.DnaMatchRepository;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.UUID;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class DnaMatchApiController {

    private final DnaMatchRepository dnaMatchRepository;

    public DnaMatchApiController(DnaMatchRepository dnaMatchRepository) {
        this.dnaMatchRepository = dnaMatchRepository;
    }

    // ========== DNA MATCHES (via view) ==========

    @GetMapping({"/match", "/matches"})
    public ResponseEntity<List<DnaMatch>> getMatches(
            @RequestParam(required = false) Double minCm,
            @RequestParam(required = false) String side,
            @RequestParam(required = false) Boolean linked,
            @RequestParam(required = false) Boolean hasAvatar,
            @RequestParam(defaultValue = "100") int limit,
            @RequestParam(defaultValue = "0") int offset) {

        List<DnaMatch> matches;
        int maxLimit = Math.min(limit, 500);

        if (Boolean.TRUE.equals(hasAvatar)) {
            matches = dnaMatchRepository.findWithAvatar(maxLimit, offset);
        } else if (minCm != null) {
            matches = dnaMatchRepository.findByMinCm(minCm, maxLimit, offset);
        } else if (side != null) {
            matches = dnaMatchRepository.findByMatchSide(side, maxLimit, offset);
        } else if (Boolean.TRUE.equals(linked)) {
            matches = dnaMatchRepository.findLinked(maxLimit, offset);
        } else {
            matches = dnaMatchRepository.findAll(maxLimit, offset);
        }

        return ResponseEntity.ok(matches);
    }

    @GetMapping({"/match/{dnaTestId}", "/matches/{dnaTestId}"})
    public ResponseEntity<DnaMatch> getMatch(@PathVariable String dnaTestId) {
        DnaMatch match = dnaMatchRepository.findByDnaTestId(dnaTestId);
        if (match == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(match);
    }

    @PostMapping("/match/{dnaTestId}/avatar")
    public ResponseEntity<DnaMatch> uploadAvatar(
            @PathVariable String dnaTestId,
            @RequestParam("avatar") MultipartFile file) {

        if (dnaMatchRepository.findTesterById(dnaTestId) == null) {
            return ResponseEntity.notFound().build();
        }

        try {
            // Create uploads directory if needed
            Path uploadDir = Paths.get("uploads/avatars");
            Files.createDirectories(uploadDir);

            // Generate unique filename
            String extension = getFileExtension(file.getOriginalFilename());
            String filename = UUID.randomUUID().toString() + extension;
            Path filePath = uploadDir.resolve(filename);

            // Save file
            Files.copy(file.getInputStream(), filePath);

            // Update database with relative path
            String avatarPath = "avatars/" + filename;
            dnaMatchRepository.updateAvatarPath(dnaTestId, avatarPath);

            // Return updated match
            DnaMatch updated = dnaMatchRepository.findByDnaTestId(dnaTestId);
            return ResponseEntity.ok(updated);

        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    private String getFileExtension(String filename) {
        if (filename == null) return ".jpg";
        int lastDot = filename.lastIndexOf('.');
        return lastDot > 0 ? filename.substring(lastDot) : ".jpg";
    }

    // ========== DNA TESTERS ==========

    @GetMapping("/dna-tester/{dnaTestId}/link-status")
    public ResponseEntity<Map<String, Object>> getLinkStatus(@PathVariable String dnaTestId) {
        Long personId = dnaMatchRepository.findTesterPersonId(dnaTestId);
        Map<String, Object> result = new java.util.LinkedHashMap<>();
        result.put("personId", personId);
        return ResponseEntity.ok(result);
    }

    @GetMapping({"/dna-tester/{dnaTestId}", "/dna-testers/{dnaTestId}"})
    public ResponseEntity<Map<String, Object>> getTester(@PathVariable String dnaTestId) {
        Map<String, Object> tester = dnaMatchRepository.findTesterById(dnaTestId);
        if (tester == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(tester);
    }

    @PostMapping({"/dna-tester", "/dna-testers"})
    public ResponseEntity<Map<String, Object>> createTester(@RequestBody Map<String, Object> body) {
        String dnaTestId = (String) body.get("dnaTestId");
        String name = (String) body.get("name");

        if (dnaTestId == null || name == null) {
            return ResponseEntity.badRequest().build();
        }

        Boolean hasTree = body.get("hasTree") != null ? (Boolean) body.get("hasTree") : false;
        Integer treeSize = body.get("treeSize") != null ? ((Number) body.get("treeSize")).intValue() : null;
        Integer adminLevel = body.get("adminLevel") != null ? ((Number) body.get("adminLevel")).intValue() : null;
        String notes = (String) body.get("notes");
        Long personId = body.get("personId") != null ? ((Number) body.get("personId")).longValue() : null;
        Integer generationDepth = body.get("generationDepth") != null ? ((Number) body.get("generationDepth")).intValue() : null;

        dnaMatchRepository.saveTester(dnaTestId, name, hasTree, treeSize, adminLevel, notes, personId, generationDepth);

        Map<String, Object> created = dnaMatchRepository.findTesterById(dnaTestId);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @DeleteMapping({"/dna-tester/{dnaTestId}", "/dna-testers/{dnaTestId}"})
    public ResponseEntity<Void> deleteTester(@PathVariable String dnaTestId) {
        if (dnaMatchRepository.findTesterById(dnaTestId) == null) {
            return ResponseEntity.notFound().build();
        }
        dnaMatchRepository.deleteTester(dnaTestId);
        return ResponseEntity.noContent().build();
    }

    // ========== DNA MATCH RELATIONSHIPS ==========

    @PostMapping({"/dna-match", "/dna-matches"})
    public ResponseEntity<Map<String, Object>> createDnaMatch(@RequestBody Map<String, Object> body) {
        String tester1Id = (String) body.get("tester1Id");
        String tester2Id = (String) body.get("tester2Id");

        if (tester1Id == null || tester2Id == null) {
            return ResponseEntity.badRequest().build();
        }

        BigDecimal sharedCm = body.get("sharedCm") != null
            ? new BigDecimal(body.get("sharedCm").toString()) : null;
        Integer sharedSegments = body.get("sharedSegments") != null
            ? ((Number) body.get("sharedSegments")).intValue() : null;
        String predictedRelationship = (String) body.get("predictedRelationship");
        String matchSide = (String) body.get("matchSide");

        dnaMatchRepository.saveMatch(tester1Id, tester2Id, sharedCm, sharedSegments,
            predictedRelationship, matchSide);

        Map<String, Object> created = dnaMatchRepository.findMatch(tester1Id, tester2Id);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @DeleteMapping({"/dna-match", "/dna-matches"})
    public ResponseEntity<Void> deleteDnaMatch(
            @RequestParam String tester1Id,
            @RequestParam String tester2Id) {

        if (dnaMatchRepository.findMatch(tester1Id, tester2Id) == null) {
            return ResponseEntity.notFound().build();
        }
        dnaMatchRepository.deleteMatch(tester1Id, tester2Id);
        return ResponseEntity.noContent().build();
    }
}
