package com.familytree.service;

import com.familytree.model.Person;
import com.familytree.repository.PersonRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.Optional;

@Service
public class PersonService {

    private final PersonRepository personRepository;

    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.ofPattern("dd MM yyyy");

    public PersonService(PersonRepository personRepository) {
        this.personRepository = personRepository;
    }

    /**
     * Update an existing person with the provided fields.
     *
     * @param id   the person ID to update
     * @param body map containing field values (firstName, surname, birthDate, etc.)
     * @return the updated Person, or empty if not found
     */
    public Optional<Person> updatePerson(Long id, Map<String, Object> body) {
        if (personRepository.findById(id).isEmpty()) {
            return Optional.empty();
        }

        String firstName = (String) body.get("firstName");
        if (firstName == null) firstName = (String) body.get("forename");
        String middleNames = (String) body.get("middleNames");
        String surname = (String) body.get("surname");
        String birthSurname = (String) body.get("birthSurname");
        String birthPlace = (String) body.get("birthPlace");
        String deathPlace = (String) body.get("deathPlace");
        String gender = (String) body.get("gender");
        String notes = (String) body.get("notes");

        LocalDate birthDate = parseDate((String) body.get("birthDate"));
        Integer birthYear = birthDate == null && body.get("birthYear") != null
            ? ((Number) body.get("birthYear")).intValue() : null;
        LocalDate deathDate = parseDate((String) body.get("deathDate"));
        Integer deathYear = deathDate == null && body.get("deathYear") != null
            ? ((Number) body.get("deathYear")).intValue() : null;

        personRepository.update(id, firstName, middleNames, surname, birthSurname,
                               birthDate, birthYear, birthPlace,
                               deathDate, deathYear, deathPlace,
                               gender, notes);

        return personRepository.findById(id);
    }

    /**
     * Add a parent to a child. Creates a new person if parentId is not provided.
     *
     * @param childId the child's ID
     * @param body    map containing parent data or parentId for existing parent
     * @return the parent Person, or empty if child not found
     */
    public Optional<Person> addParent(Long childId, Map<String, Object> body) {
        Person child = personRepository.findById(childId).orElse(null);
        if (child == null) {
            return Optional.empty();
        }

        String gender = (String) body.get("gender");
        Long existingParentId = body.get("parentId") != null
            ? ((Number) body.get("parentId")).longValue() : null;

        Long parentId;
        if (existingParentId != null) {
            parentId = existingParentId;
        } else {
            parentId = createPerson(body, null, null, child.treeId());
        }

        // Female = mother (parent2), Male = father (parent1)
        if ("F".equalsIgnoreCase(gender)) {
            personRepository.updateParents(childId, child.fatherId(), parentId);
        } else {
            personRepository.updateParents(childId, parentId, child.motherId());
        }

        return personRepository.findById(parentId);
    }

    /**
     * Add a child to a parent. Creates a new person if childId is not provided.
     *
     * @param parentId     the parent's ID
     * @param body         map containing child data or childId for existing child
     * @param parentGender the parent's gender ("M" or "F") to determine which parent field to set
     * @return the child Person, or empty if parent not found
     */
    public Optional<Person> addChild(Long parentId, Map<String, Object> body, String parentGender) {
        Person parent = personRepository.findById(parentId).orElse(null);
        if (parent == null) {
            return Optional.empty();
        }

        Long existingChildId = body.get("childId") != null
            ? ((Number) body.get("childId")).longValue() : null;

        Long childId;
        if (existingChildId != null) {
            childId = existingChildId;
            // Link existing child to this parent
            Person child = personRepository.findById(childId).orElse(null);
            if (child != null) {
                if ("F".equalsIgnoreCase(parentGender)) {
                    personRepository.updateParents(childId, child.fatherId(), parentId);
                } else {
                    personRepository.updateParents(childId, parentId, child.motherId());
                }
            }
        } else {
            // Create new child with parent reference
            Long fatherId = "M".equalsIgnoreCase(parentGender) ? parentId : null;
            Long motherId = "F".equalsIgnoreCase(parentGender) ? parentId : null;
            childId = createPerson(body, fatherId, motherId, parent.treeId());
        }

        return personRepository.findById(childId);
    }

    /**
     * Add a spouse to a person. Creates a new person if spouseId is not provided.
     *
     * @param personId the person's ID
     * @param body     map containing spouse data or spouseId for existing spouse
     * @return the spouse Person, or empty if person not found
     */
    public Optional<Person> addSpouse(Long personId, Map<String, Object> body) {
        Person person = personRepository.findById(personId).orElse(null);
        if (person == null) {
            return Optional.empty();
        }

        Long existingSpouseId = body.get("spouseId") != null
            ? ((Number) body.get("spouseId")).longValue() : null;

        Long spouseId;
        if (existingSpouseId != null) {
            spouseId = existingSpouseId;
        } else {
            spouseId = createPerson(body, null, null, person.treeId());
        }

        personRepository.addMarriage(personId, spouseId);

        return personRepository.findById(spouseId);
    }

    /**
     * Create a new person with the provided data.
     *
     * @param body     map containing person fields
     * @param fatherId optional father ID
     * @param motherId optional mother ID
     * @param treeId   optional tree ID
     * @return the new person's ID
     */
    public Long createPerson(Map<String, Object> body, Long fatherId, Long motherId, Integer treeId) {
        Long id = body.get("id") != null ? ((Number) body.get("id")).longValue() : null;
        String firstName = (String) body.get("firstName");
        if (firstName == null) firstName = (String) body.get("forename");
        String middleNames = (String) body.get("middleNames");
        String surname = (String) body.get("surname");
        String birthSurname = (String) body.get("birthSurname");
        String birthPlace = (String) body.get("birthPlace");
        String deathPlace = (String) body.get("deathPlace");
        String gender = (String) body.get("gender");
        String notes = (String) body.get("notes");

        LocalDate birthDate = parseDate((String) body.get("birthDate"));
        Integer birthYear = birthDate == null && body.get("birthYear") != null
            ? ((Number) body.get("birthYear")).intValue() : null;
        LocalDate deathDate = parseDate((String) body.get("deathDate"));
        Integer deathYear = deathDate == null && body.get("deathYear") != null
            ? ((Number) body.get("deathYear")).intValue() : null;

        return personRepository.save(id, firstName, middleNames, surname, birthSurname,
                                     birthDate, birthYear, birthPlace,
                                     deathDate, deathYear, deathPlace,
                                     gender, notes, fatherId, motherId, treeId);
    }

    /**
     * Parse a date string in "dd MM yyyy" format.
     *
     * @param dateStr the date string to parse
     * @return LocalDate or null if parsing fails or input is null/blank
     */
    public LocalDate parseDate(String dateStr) {
        if (dateStr == null || dateStr.isBlank()) return null;
        try {
            return LocalDate.parse(dateStr, DATE_FORMAT);
        } catch (Exception e) {
            return null;
        }
    }
}
