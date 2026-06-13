package com.familytree.integration;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
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

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * End-to-end CI proof, driven by the real {@code seed/} files (the single source of
 * truth shared with {@code seed/seed.py}). A fresh Postgres container is created,
 * Flyway builds the schema from V1, the app boots, and this test reads
 * {@code manifest.json} + the {@code people/*.json} payloads, POSTs them through the
 * HTTP API, then reads the result back and asserts it matches what the files said.
 * No person data is duplicated in this class.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("it")
@Testcontainers
class SeedFlowIntegrationTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    // The create endpoint parses dates as "dd MM yyyy" and silently nulls anything else.
    private static final DateTimeFormatter SEED_DATE = DateTimeFormatter.ofPattern("dd MM yyyy");
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final Path SEED_DIR = locateSeedDir();

    @Autowired
    TestRestTemplate rest;

    /** seed/ lives at the repo root; tests run from family-tree-app/, hence ../seed. */
    private static Path locateSeedDir() {
        for (String candidate : new String[] {"../seed", "seed", "../../seed"}) {
            Path p = Path.of(candidate);
            if (Files.exists(p.resolve("manifest.json"))) {
                return p.toAbsolutePath().normalize();
            }
        }
        throw new IllegalStateException("Could not locate the seed/ directory (no manifest.json found)");
    }

    private Map<String, Object> readJson(String relativePath) throws IOException {
        return MAPPER.readValue(Files.readString(SEED_DIR.resolve(relativePath)),
                new TypeReference<Map<String, Object>>() {});
    }

    private HttpEntity<Map<String, Object>> entity(Map<String, Object> jsonBody) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        return new HttpEntity<>(jsonBody, headers);
    }

    @Test
    @SuppressWarnings("unchecked")
    void seedsTheCuratedTreeFromTheSeedFiles() throws IOException {
        TestRestTemplate api = rest.withBasicAuth("chris", "chris");
        Map<String, Object> manifest = readJson("manifest.json");

        // 1. tree, from manifest.tree
        Map<String, Object> treeBody = (Map<String, Object>) manifest.get("tree");
        ResponseEntity<Map> tree = api.postForEntity("/api/tree", entity(treeBody), Map.class);
        assertThat(tree.getStatusCode()).isEqualTo(HttpStatus.CREATED);
        Number treeId = (Number) tree.getBody().get("id");

        // 2. walk the manifest steps, POSTing the actual seed JSON payloads.
        //    Symbolic refs are resolved to DB-assigned ids at run time.
        Map<String, Number> ids = new HashMap<>();                    // ref -> DB id
        Map<String, Map<String, Object>> payloads = new HashMap<>();  // ref -> the JSON we sent
        for (Map<String, Object> step : (List<Map<String, Object>>) manifest.get("steps")) {
            String ref = (String) step.get("ref");
            String kind = (String) step.get("create");                // root | parent | spouse | child
            Map<String, Object> personBody = readJson((String) step.get("body"));
            payloads.put(ref, personBody);

            String url;
            if ("root".equals(kind)) {
                url = "/api/tree/" + treeId + "/person";
            } else {
                Number ofId = ids.get(step.get("of"));
                assertThat(ofId)
                        .as("step '%s' references ref '%s', which must be created first", ref, step.get("of"))
                        .isNotNull();
                url = "/api/person/" + ofId + "/" + kind;
            }
            ResponseEntity<Map> created = api.postForEntity(url, entity(personBody), Map.class);
            assertThat(created.getStatusCode()).as("creating '%s'", ref).isEqualTo(HttpStatus.CREATED);
            ids.put(ref, (Number) created.getBody().get("id"));
        }

        // 3. read 'me' back and confirm it matches the seed files exactly
        Map<String, Object> meJson = payloads.get("me");
        ResponseEntity<Map> read = api.getForEntity("/api/person/" + ids.get("me"), Map.class);
        assertThat(read.getStatusCode()).isEqualTo(HttpStatus.OK);

        Map<String, Object> person = (Map<String, Object>) read.getBody().get("person");
        assertThat(person.get("firstName")).isEqualTo(meJson.get("firstName"));
        assertThat(person.get("surname")).isEqualTo(meJson.get("surname"));
        assertThat(person.get("gender")).isEqualTo(meJson.get("gender"));
        // seed file date is "dd MM yyyy"; the API returns ISO
        String expectedIso = LocalDate.parse((String) meJson.get("birthDate"), SEED_DATE).toString();
        assertThat(person.get("birthDate")).isEqualTo(expectedIso);

        // parents wired and resolved, names matching dad.json / mum.json
        assertThat(person.get("parent1Id")).isNotNull();
        assertThat(person.get("parent2Id")).isNotNull();
        Map<String, Object> father = (Map<String, Object>) read.getBody().get("father");
        Map<String, Object> mother = (Map<String, Object>) read.getBody().get("mother");
        assertThat(father).as("father resolved").isNotNull();
        assertThat(mother).as("mother resolved").isNotNull();
        assertThat(father.get("firstName")).isEqualTo(payloads.get("dad").get("firstName"));
        assertThat(mother.get("firstName")).isEqualTo(payloads.get("mum").get("firstName"));
    }
}
