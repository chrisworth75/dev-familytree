package com.familytree.integration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.ActiveProfiles;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * End-to-end CI proof: a fresh Postgres container is created, Flyway builds the
 * schema from V1, the app boots against it, and the curated tree is seeded purely
 * through the HTTP API (create tree -> me -> father -> mother) — the same flow as
 * {@code seed/seed.py}. This is the seeder doubling as an integration test.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("it")
@Testcontainers
class SeedFlowIntegrationTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @Autowired
    TestRestTemplate rest;

    private HttpEntity<Map<String, Object>> body(Map<String, Object> json) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        return new HttpEntity<>(json, headers);
    }

    @Test
    void seedsRootAndParentsThroughTheApi() {
        // 1. tree
        ResponseEntity<Map> tree = rest.postForEntity("/api/tree",
                body(Map.of("name", "My Direct Line", "ownerName", "Chris Worthington")), Map.class);
        assertThat(tree.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        Number treeId = (Number) tree.getBody().get("id");

        // 2. me (root) — NB the create endpoint requires "dd MM yyyy" dates
        ResponseEntity<Map> me = rest.postForEntity("/api/tree/" + treeId + "/person",
                body(Map.of("firstName", "Chris", "surname", "Worthington",
                        "gender", "M", "birthDate", "30 09 1975")), Map.class);
        assertThat(me.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        Number meId = (Number) me.getBody().get("id");

        // 3. parents — gender M -> father (parent1), gender F -> mother (parent2)
        rest.postForEntity("/api/person/" + meId + "/parent",
                body(Map.of("firstName", "Father", "surname", "Worthington", "gender", "M")), Map.class);
        rest.postForEntity("/api/person/" + meId + "/parent",
                body(Map.of("firstName", "Mother", "surname", "Worthington", "gender", "F")), Map.class);

        // 4. read me back: DOB stored, both parents wired and resolved
        ResponseEntity<Map> read = rest.getForEntity("/api/person/" + meId, Map.class);
        assertThat(read.getStatusCode()).isEqualTo(HttpStatus.OK);

        @SuppressWarnings("unchecked")
        Map<String, Object> person = (Map<String, Object>) read.getBody().get("person");
        assertThat(person.get("birthDate")).isEqualTo("1975-09-30");
        assertThat(person.get("parent1Id")).isNotNull();
        assertThat(person.get("parent2Id")).isNotNull();
        assertThat(read.getBody().get("father")).isNotNull();
        assertThat(read.getBody().get("mother")).isNotNull();
    }
}
