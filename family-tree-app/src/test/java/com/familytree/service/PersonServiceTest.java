package com.familytree.service;

import com.familytree.dto.PersonRequest;
import com.familytree.model.Person;
import com.familytree.repository.PersonRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doReturn;
import static org.mockito.Mockito.verify;

@SpringBootTest
@ActiveProfiles("test")
@Sql(scripts = "/worthington-family.sql", executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
@Transactional
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class PersonServiceTest {

    @Autowired
    private PersonService personService;

    @SpyBean
    private PersonRepository personRepository;

    // Test data IDs from worthington-family.sql
    private static final Long CHRIS = 1000L;
    private static final Long TIMOTHY = 1001L;
    private static final Long REBECCA = 1002L;
    private static final Long JENNIFER = 1003L;
    private static final Long SARAH = 1004L;
    private static final Long PATRICIA = 2000L;
    private static final Long JONATHAN = 2001L;
    private static final Long ARTHUR_GORDON = 3002L;

    @Nested
    @DisplayName("parseDate")
    class ParseDate {

        @Test
        void parsesValidDate() {
            LocalDate result = personService.parseDate("30 09 1975");
            assertThat(result).isEqualTo(LocalDate.of(1975, 9, 30));
        }

        @Test
        void parsesDateWithLeadingZeros() {
            LocalDate result = personService.parseDate("01 01 2000");
            assertThat(result).isEqualTo(LocalDate.of(2000, 1, 1));
        }

        @Test
        void returnsNullForNullInput() {
            assertThat(personService.parseDate(null)).isNull();
        }

        @Test
        void returnsNullForBlankInput() {
            assertThat(personService.parseDate("")).isNull();
            assertThat(personService.parseDate("   ")).isNull();
        }

        @Test
        void returnsNullForInvalidFormat() {
            assertThat(personService.parseDate("1975-09-30")).isNull();
            assertThat(personService.parseDate("30/09/1975")).isNull();
            assertThat(personService.parseDate("not a date")).isNull();
        }

        @Test
        void returnsNullForInvalidDate() {
            assertThat(personService.parseDate("32 13 2000")).isNull();
        }
    }

    @Nested
    @DisplayName("createPerson")
    class CreatePerson {

        @Test
        void extractsFieldsFromBodyCorrectly() {
            // Stub the repository save to return a known ID
            doReturn(9999L).when(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), any(), any(), any()
            );

            PersonRequest body = PersonRequest.builder()
                .firstName("William").middleNames("James").surname("Worthington")
                .gender("M").birthDate("15 03 1990").birthPlace("London").notes("Test person")
                .build();

            Long id = personService.createPerson(body, JONATHAN, PATRICIA, 1);

            assertThat(id).isEqualTo(9999L);

            // Verify the repository was called with correct parameters
            verify(personRepository).save(
                eq(null),  // id
                eq("William"), eq("James"), eq("Worthington"), eq(null),  // names
                eq(LocalDate.of(1990, 3, 15)), eq(null), eq("London"),  // birth
                eq(null), eq(null), eq(null),  // death
                eq("M"), eq("Test person"),  // gender, notes
                eq(JONATHAN), eq(PATRICIA), eq(1)  // parents, tree
            );
        }

        // NB: the legacy "forename" -> firstName alias is now a binding concern,
        // handled by @JsonAlias("forename") on PersonRequest.firstName (not the service).

        @Test
        void usesBirthYearWhenBirthDateNotProvided() {
            doReturn(9999L).when(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), any(), any(), any()
            );

            PersonRequest body = PersonRequest.builder()
                .firstName("Approximate").surname("Year").birthYear(1850)
                .build();

            personService.createPerson(body, null, null, 1);

            verify(personRepository).save(
                eq(null), eq("Approximate"), any(), eq("Year"), any(),
                eq(null), eq(1850), any(),  // birthDate null, birthYear 1850
                any(), any(), any(), any(), any(), any(), any(), any()
            );
        }
    }

    @Nested
    @DisplayName("addParent")
    class AddParent {

        @Test
        void addsMaleParentAsFather() {
            // Mock save to return a known ID
            doReturn(9999L).when(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), any(), any(), any()
            );
            // Mock findById for the new parent
            doReturn(Optional.of(createMockPerson(9999L, "New", "Father", "M")))
                .when(personRepository).findById(9999L);
            // Mock updateParents to avoid FK constraint
            org.mockito.Mockito.doNothing().when(personRepository).updateParents(any(), any(), any());

            PersonRequest parentBody = PersonRequest.builder()
                .firstName("New").surname("Father").gender("M").build();

            Optional<Person> result = personService.addParent(CHRIS, parentBody);

            assertThat(result).isPresent();

            // Verify parent was linked as father (first argument to updateParents)
            verify(personRepository).updateParents(eq(CHRIS), eq(9999L), any());
        }

        @Test
        void addsFemaleParentAsMother() {
            doReturn(9999L).when(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), any(), any(), any()
            );
            doReturn(Optional.of(createMockPerson(9999L, "New", "Mother", "F")))
                .when(personRepository).findById(9999L);
            org.mockito.Mockito.doNothing().when(personRepository).updateParents(any(), any(), any());

            PersonRequest parentBody = PersonRequest.builder()
                .firstName("New").surname("Mother").gender("F").build();

            Optional<Person> result = personService.addParent(CHRIS, parentBody);

            assertThat(result).isPresent();

            // Verify parent was linked as mother (second argument to updateParents)
            verify(personRepository).updateParents(eq(CHRIS), any(), eq(9999L));
        }

        @Test
        void linksExistingParentById() {
            PersonRequest parentBody = PersonRequest.builder()
                .parentId(ARTHUR_GORDON).gender("M").build();

            Optional<Person> result = personService.addParent(CHRIS, parentBody);

            assertThat(result).isPresent();
            assertThat(result.get().id()).isEqualTo(ARTHUR_GORDON);

            // Verify existing person was linked as father
            verify(personRepository).updateParents(eq(CHRIS), eq(ARTHUR_GORDON), any());
        }

        @Test
        void returnsEmptyForNonExistentChild() {
            PersonRequest parentBody = PersonRequest.builder()
                .firstName("Test").gender("M").build();

            Optional<Person> result = personService.addParent(999999L, parentBody);

            assertThat(result).isEmpty();
        }
    }

    @Nested
    @DisplayName("addChild")
    class AddChild {

        @Test
        void addsChildWithMaleParentAsFather() {
            doReturn(9999L).when(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), eq(JONATHAN), eq(null), any()
            );
            doReturn(Optional.of(createMockPerson(9999L, "NewChild", "Worthington", "F")))
                .when(personRepository).findById(9999L);

            PersonRequest childBody = PersonRequest.builder()
                .firstName("NewChild").surname("Worthington").gender("F").build();

            Optional<Person> result = personService.addChild(JONATHAN, childBody, "M");

            assertThat(result).isPresent();

            // Verify child was created with father set to JONATHAN
            verify(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), eq(JONATHAN), eq(null), any()
            );
        }

        @Test
        void addsChildWithFemaleParentAsMother() {
            doReturn(9999L).when(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), eq(null), eq(PATRICIA), any()
            );
            doReturn(Optional.of(createMockPerson(9999L, "NewChild", "Worthington", "M")))
                .when(personRepository).findById(9999L);

            PersonRequest childBody = PersonRequest.builder()
                .firstName("NewChild").surname("Worthington").gender("M").build();

            Optional<Person> result = personService.addChild(PATRICIA, childBody, "F");

            assertThat(result).isPresent();

            // Verify child was created with mother set to PATRICIA
            verify(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), eq(null), eq(PATRICIA), any()
            );
        }

        @Test
        void linksExistingChildById() {
            PersonRequest linkBody = PersonRequest.builder().childId(REBECCA).build();

            Optional<Person> result = personService.addChild(ARTHUR_GORDON, linkBody, "M");

            assertThat(result).isPresent();

            // Verify existing child was linked with father set to ARTHUR_GORDON
            verify(personRepository).updateParents(eq(REBECCA), eq(ARTHUR_GORDON), any());
        }

        @Test
        void returnsEmptyForNonExistentParent() {
            PersonRequest childBody = PersonRequest.builder().firstName("Test").build();

            Optional<Person> result = personService.addChild(999999L, childBody, "M");

            assertThat(result).isEmpty();
        }
    }

    @Nested
    @DisplayName("addSpouse")
    class AddSpouse {

        @Test
        void createsNewSpouseAndMarriage() {
            doReturn(9999L).when(personRepository).save(
                any(), any(), any(), any(), any(), any(), any(), any(),
                any(), any(), any(), any(), any(), any(), any(), any()
            );
            doReturn(Optional.of(createMockPerson(9999L, "NewSpouse", "Person", "F")))
                .when(personRepository).findById(9999L);
            org.mockito.Mockito.doNothing().when(personRepository).addMarriage(any(), any());

            PersonRequest spouseBody = PersonRequest.builder()
                .firstName("NewSpouse").surname("Person").gender("F").build();

            Optional<Person> result = personService.addSpouse(TIMOTHY, spouseBody);

            assertThat(result).isPresent();

            // Verify marriage was created
            verify(personRepository).addMarriage(TIMOTHY, 9999L);
        }

        @Test
        void linksExistingSpouseById() {
            org.mockito.Mockito.doNothing().when(personRepository).addMarriage(any(), any());

            PersonRequest linkBody = PersonRequest.builder().spouseId(SARAH).build();

            Optional<Person> result = personService.addSpouse(REBECCA, linkBody);

            assertThat(result).isPresent();
            assertThat(result.get().id()).isEqualTo(SARAH);

            verify(personRepository).addMarriage(REBECCA, SARAH);
        }

        @Test
        void returnsEmptyForNonExistentPerson() {
            PersonRequest spouseBody = PersonRequest.builder().firstName("Test").build();

            Optional<Person> result = personService.addSpouse(999999L, spouseBody);

            assertThat(result).isEmpty();
        }
    }

    @Nested
    @DisplayName("updatePerson")
    class UpdatePerson {

        @Test
        void updatesExistingPerson() {
            PersonRequest updates = PersonRequest.builder()
                .firstName("Christopher").middleNames("James").birthPlace("Manchester").notes("Updated notes")
                .build();

            Optional<Person> result = personService.updatePerson(CHRIS, updates);

            assertThat(result).isPresent();

            // Verify update was called with correct parameters
            verify(personRepository).update(
                eq(CHRIS),
                eq("Christopher"), eq("James"), any(), any(),
                any(), any(), eq("Manchester"),
                any(), any(), any(),
                any(), eq("Updated notes")
            );
        }

        @Test
        void returnsEmptyForNonExistentPerson() {
            PersonRequest updates = PersonRequest.builder().firstName("Test").build();

            Optional<Person> result = personService.updatePerson(999999L, updates);

            assertThat(result).isEmpty();
        }

        @Test
        void updatesBirthSurname() {
            PersonRequest updates = PersonRequest.builder()
                .firstName("Patricia").surname("Worthington").birthSurname("Wood")
                .build();

            Optional<Person> result = personService.updatePerson(PATRICIA, updates);

            assertThat(result).isPresent();

            verify(personRepository).update(
                eq(PATRICIA),
                eq("Patricia"), any(), eq("Worthington"), eq("Wood"),
                any(), any(), any(), any(), any(), any(), any(), any()
            );
        }
    }

    // Helper to create mock Person objects
    private Person createMockPerson(Long id, String firstName, String surname, String gender) {
        return new Person(
            id, firstName, null, surname, null,
            null, null, null, null, null, null,
            gender, null, null, null, 1, null
        );
    }
}
