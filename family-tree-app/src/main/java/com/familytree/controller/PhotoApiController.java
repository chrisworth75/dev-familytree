package com.familytree.controller;

import com.familytree.model.Photo;
import com.familytree.model.PhotoTag;
import com.familytree.service.PhotoService;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/photos")
public class PhotoApiController {

    private final PhotoService photoService;

    public PhotoApiController(PhotoService photoService) {
        this.photoService = photoService;
    }

    @PostMapping
    public ResponseEntity<?> uploadPhoto(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "description", required = false) String description,
            @RequestParam(value = "yearTaken", required = false) Integer yearTaken) {
        try {
            Photo photo = photoService.uploadPhoto(file, description, yearTaken);
            return ResponseEntity.status(HttpStatus.CREATED).body(photo);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(Map.of("error", "Failed to save photo"));
        }
    }

    @GetMapping
    public ResponseEntity<List<Photo>> listPhotos() {
        return ResponseEntity.ok(photoService.getAllPhotos());
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> getPhoto(@PathVariable Long id) {
        return photoService.getPhotoDetail(id)
            .map(photo -> {
                List<PhotoTag> tags = photoService.getPhotoTags(id);
                Map<String, Object> response = new LinkedHashMap<>();
                response.put("photo", photo);
                response.put("tags", tags);
                return ResponseEntity.ok((Object) response);
            })
            .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deletePhoto(@PathVariable Long id) {
        if (photoService.getPhotoDetail(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        try {
            photoService.deletePhoto(id);
            return ResponseEntity.noContent().build();
        } catch (IOException e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    @PostMapping("/{id}/tags")
    public ResponseEntity<?> addTag(@PathVariable Long id, @RequestBody Map<String, Object> body) {
        if (photoService.getPhotoDetail(id).isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        Long personId = ((Number) body.get("personId")).longValue();
        Double xPosition = body.get("xPosition") != null ? ((Number) body.get("xPosition")).doubleValue() : null;
        Double yPosition = body.get("yPosition") != null ? ((Number) body.get("yPosition")).doubleValue() : null;

        if (photoService.tagExists(id, personId)) {
            return ResponseEntity.status(HttpStatus.CONFLICT)
                .body(Map.of("error", "Person is already tagged in this photo"));
        }

        photoService.addTag(id, personId, xPosition, yPosition);
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(Map.of("photoId", id, "personId", personId));
    }

    @DeleteMapping("/{id}/tags/{personId}")
    public ResponseEntity<Void> removeTag(@PathVariable Long id, @PathVariable Long personId) {
        if (!photoService.tagExists(id, personId)) {
            return ResponseEntity.notFound().build();
        }
        photoService.removeTag(id, personId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/images/{id}/{variant}")
    public ResponseEntity<Resource> getImage(@PathVariable Long id, @PathVariable String variant) {
        if (!variant.equals("original") && !variant.equals("thumb")) {
            return ResponseEntity.badRequest().build();
        }
        return photoService.getImageResource(id, variant)
            .map(resource -> ResponseEntity.ok()
                .contentType(MediaType.IMAGE_JPEG)
                .body(resource))
            .orElse(ResponseEntity.notFound().build());
    }
}
