package com.familytree.service;

import com.familytree.config.PhotoConfig;
import com.familytree.model.Photo;
import com.familytree.model.PhotoTag;
import com.familytree.repository.PhotoRepository;
import net.coobird.thumbnailator.Thumbnails;
import net.coobird.thumbnailator.geometry.Positions;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;

@Service
public class PhotoService {

    private final PhotoRepository photoRepository;
    private final PhotoConfig photoConfig;

    public PhotoService(PhotoRepository photoRepository, PhotoConfig photoConfig) {
        this.photoRepository = photoRepository;
        this.photoConfig = photoConfig;
    }

    public Photo uploadPhoto(MultipartFile file, String description, Integer yearTaken) throws IOException {
        String contentType = file.getContentType();
        if (contentType == null || (!contentType.equals("image/jpeg") && !contentType.equals("image/png"))) {
            throw new IllegalArgumentException("Only JPEG and PNG images are supported");
        }

        Long id = photoRepository.save(file.getOriginalFilename(), description, yearTaken);

        try {
            Path photoDir = Path.of(photoConfig.getStoragePath(), id.toString());
            Files.createDirectories(photoDir);

            Path originalPath = photoDir.resolve("original.jpg");
            Thumbnails.of(file.getInputStream())
                .scale(1.0)
                .outputFormat("jpg")
                .toFile(originalPath.toFile());

            Path thumbPath = photoDir.resolve("thumb.jpg");
            Thumbnails.of(file.getInputStream())
                .size(200, 200)
                .crop(Positions.CENTER)
                .outputFormat("jpg")
                .toFile(thumbPath.toFile());
        } catch (IOException e) {
            photoRepository.delete(id);
            throw e;
        }

        return photoRepository.findById(id).orElseThrow();
    }

    public void deletePhoto(Long id) throws IOException {
        photoRepository.delete(id);
        Path photoDir = Path.of(photoConfig.getStoragePath(), id.toString());
        if (Files.exists(photoDir)) {
            try (var paths = Files.walk(photoDir)) {
                paths.sorted(Comparator.reverseOrder())
                    .forEach(path -> {
                        try { Files.delete(path); } catch (IOException ignored) {}
                    });
            }
        }
    }

    public Optional<Resource> getImageResource(Long id, String variant) {
        Path filePath = Path.of(photoConfig.getStoragePath(), id.toString(), variant + ".jpg");
        if (Files.exists(filePath)) {
            return Optional.of(new FileSystemResource(filePath));
        }
        return Optional.empty();
    }

    public Optional<Photo> getPhotoDetail(Long id) {
        return photoRepository.findById(id);
    }

    public List<PhotoTag> getPhotoTags(Long photoId) {
        return photoRepository.findTagsByPhotoId(photoId);
    }

    public List<Photo> getAllPhotos() {
        return photoRepository.findAllWithTagCount();
    }

    public List<Photo> getPhotosForPerson(Long personId) {
        return photoRepository.findPhotosByPersonId(personId);
    }

    public void addTag(Long photoId, Long personId, Double xPosition, Double yPosition) {
        photoRepository.addTag(photoId, personId, xPosition, yPosition);
    }

    public boolean tagExists(Long photoId, Long personId) {
        return photoRepository.tagExists(photoId, personId);
    }

    public void removeTag(Long photoId, Long personId) {
        photoRepository.removeTag(photoId, personId);
    }
}
