package com.familytree.service;

import com.familytree.dto.PersonDetailDto;
import com.familytree.dto.PersonDto;
import com.familytree.dto.PersonRequest;
import com.familytree.model.Person;
import com.familytree.repository.DnaMatchRepository;
import com.familytree.repository.PersonRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Optional;

@Service
public class PersonService {

    private final PersonRepository personRepository;
    private final DnaMatchRepository dnaMatchRepository;

    private static final DateTimeFormatter DATE_FORMAT = DateTimeFormatter.ofPattern("dd MM yyyy");

    public PersonService(PersonRepository personRepository, DnaMatchRepository dnaMatchRepository) {
        this.personRepository = personRepository;
        this.dnaMatchRepository = dnaMatchRepository;
    }

    /** The person plus immediate relations (mother, father, spouses, children, siblings). */
    public Optional<PersonDetailDto> getPersonDetail(Long id) {
        return personRepository.findById(id).map(person -> new PersonDetailDto(
            PersonDto.from(person),
            PersonDto.from(parent(person.motherId())),
            PersonDto.from(parent(person.fatherId())),
            toDtos(personRepository.findSpouses(id)),
            toDtos(personRepository.findChildren(id)),
            toDtos(personRepository.findSiblings(id)),
            null, null, null
        ));
    }

    /** As {@link #getPersonDetail} plus DNA match and ancestor/descendant counts. */
    public Optional<PersonDetailDto> getPersonSummary(Long id) {
        return personRepository.findById(id).map(person -> new PersonDetailDto(
            PersonDto.from(person),
            PersonDto.from(parent(person.motherId())),
            PersonDto.from(parent(person.fatherId())),
            toDtos(personRepository.findSpouses(id)),
            toDtos(personRepository.findChildren(id)),
            toDtos(personRepository.findSiblings(id)),
            dnaMatchRepository.findMatchByPersonId(id),
            personRepository.countAncestors(id),
            personRepository.countDescendants(id)
        ));
    }

    private Person parent(Long parentId) {
        return parentId != null ? personRepository.findById(parentId).orElse(null) : null;
    }

    private static List<PersonDto> toDtos(List<Person> people) {
        return people.stream().map(PersonDto::from).toList();
    }

    /**
     * Update an existing person with the provided fields.
     *
     * @param id  the person ID to update
     * @param req the person fields
     * @return the updated Person, or empty if not found
     */
    public Optional<Person> updatePerson(Long id, PersonRequest req) {
        if (personRepository.findById(id).isEmpty()) {
            return Optional.empty();
        }

        LocalDate birthDate = parseDate(req.birthDate());
        Integer birthYear = birthDate == null ? req.birthYear() : null;
        LocalDate deathDate = parseDate(req.deathDate());
        Integer deathYear = deathDate == null ? req.deathYear() : null;

        personRepository.update(id, req.firstName(), req.middleNames(), req.surname(), req.birthSurname(),
                               birthDate, birthYear, req.birthPlace(),
                               deathDate, deathYear, req.deathPlace(),
                               req.gender(), req.notes());

        return personRepository.findById(id);
    }

    /**
     * Add a parent to a child. Creates a new person unless {@code req.parentId()} links an existing one.
     *
     * @param childId the child's ID
     * @param req     the parent data (or {@code parentId} for an existing parent)
     * @return the parent Person, or empty if child not found
     */
    public Optional<Person> addParent(Long childId, PersonRequest req) {
        Person child = personRepository.findById(childId).orElse(null);
        if (child == null) {
            return Optional.empty();
        }

        Long parentId = req.parentId() != null
            ? req.parentId()
            : createPerson(req, null, null, child.treeId());

        // Female = mother (parent2), Male = father (parent1)
        if ("F".equalsIgnoreCase(req.gender())) {
            personRepository.updateParents(childId, child.fatherId(), parentId);
        } else {
            personRepository.updateParents(childId, parentId, child.motherId());
        }

        return personRepository.findById(parentId);
    }

    /**
     * Add a child to a parent. Creates a new person unless {@code req.childId()} links an existing one.
     *
     * @param parentId     the parent's ID
     * @param req          the child data (or {@code childId} for an existing child)
     * @param parentGender the parent's gender ("M" or "F"), to set the correct parent field
     * @return the child Person, or empty if parent not found
     */
    public Optional<Person> addChild(Long parentId, PersonRequest req, String parentGender) {
        Person parent = personRepository.findById(parentId).orElse(null);
        if (parent == null) {
            return Optional.empty();
        }

        Long childId;
        if (req.childId() != null) {
            childId = req.childId();
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
            childId = createPerson(req, fatherId, motherId, parent.treeId());
        }

        return personRepository.findById(childId);
    }

    /**
     * Add a spouse to a person. Creates a new person if spouseId is not provided.
     *
     * @param personId the person's ID
     * @param req      the spouse data (or {@code spouseId} for an existing spouse)
     * @return the spouse Person, or empty if person not found
     */
    public Optional<Person> addSpouse(Long personId, PersonRequest req) {
        Person person = personRepository.findById(personId).orElse(null);
        if (person == null) {
            return Optional.empty();
        }

        Long spouseId = req.spouseId() != null
            ? req.spouseId()
            : createPerson(req, null, null, person.treeId());

        personRepository.addMarriage(personId, spouseId);

        return personRepository.findById(spouseId);
    }

    /**
     * Create a new person from the request.
     *
     * @param req      the person fields
     * @param fatherId optional father ID
     * @param motherId optional mother ID
     * @param treeId   optional tree ID
     * @return the new person's ID
     */
    public Long createPerson(PersonRequest req, Long fatherId, Long motherId, Integer treeId) {
        LocalDate birthDate = parseDate(req.birthDate());
        Integer birthYear = birthDate == null ? req.birthYear() : null;
        LocalDate deathDate = parseDate(req.deathDate());
        Integer deathYear = deathDate == null ? req.deathYear() : null;

        return personRepository.save(req.id(), req.firstName(), req.middleNames(), req.surname(), req.birthSurname(),
                                     birthDate, birthYear, req.birthPlace(),
                                     deathDate, deathYear, req.deathPlace(),
                                     req.gender(), req.notes(), fatherId, motherId, treeId);
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
