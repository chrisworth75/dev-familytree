package com.familytree.service;

import com.familytree.model.DashboardStats;
import com.familytree.model.TopAncestor;
import com.familytree.model.TopCensusAncestor;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
@Sql(scripts = {"/worthington-family.sql", "/stats-census-fixture.sql"},
     executionPhase = Sql.ExecutionPhase.BEFORE_TEST_METHOD)
@Transactional
class StatsServiceTest {

    @Autowired
    private StatsService statsService;

    private static final long ARTHUR_GORDON = 3002L;
    private static final long CONSTANCE = 4005L;
    private static final long CHRIS = 1000L;
    private static final long TIMOTHY = 1001L;
    private static final long ARTHUR_GOODALL = 4004L;

    @Nested
    @DisplayName("getTopAncestorsByCensus")
    class TopByCensus {

        @Test
        void ranksPeopleByCensusRecordCountDescending() {
            List<TopCensusAncestor> result = statsService.getTopAncestorsByCensus();

            assertThat(result).extracting(TopCensusAncestor::id)
                .containsExactly(ARTHUR_GORDON, CONSTANCE, CHRIS);
            assertThat(result).extracting(TopCensusAncestor::censusCount)
                .containsExactly(3L, 2L, 1L);
        }

        @Test
        void mapsNameAndBirthYear() {
            TopCensusAncestor chris = censusEntry(CHRIS);

            assertThat(chris.name()).isEqualTo("Chris Worthington");
            assertThat(chris.birthYear()).isEqualTo(1975);
        }

        @Test
        void countsOnlyCensusRecordsNotOtherSourceTypes() {
            // Chris has 1 census + 1 probate record; only the census must count.
            assertThat(censusEntry(CHRIS).censusCount()).isEqualTo(1L);
        }

        @Test
        void excludesPeopleWithNoCensusRecords() {
            assertThat(statsService.getTopAncestorsByCensus())
                .extracting(TopCensusAncestor::id)
                .doesNotContain(TIMOTHY);
        }

        private TopCensusAncestor censusEntry(long id) {
            return statsService.getTopAncestorsByCensus().stream()
                .filter(a -> a.id() == id).findFirst().orElseThrow();
        }
    }

    @Nested
    @DisplayName("getDashboardStats")
    class Dashboard {

        @Test
        void treeSizeMatchesPersonCount() {
            assertThat(statsService.getDashboardStats().treeSize()).isGreaterThan(0);
        }

        @Test
        void linkedPlusUnlinkedEqualsTotalDnaMatches() {
            DashboardStats stats = statsService.getDashboardStats();
            assertThat(stats.linkedMatches() + stats.unlinkedMatches())
                .isEqualTo(stats.dnaMatchCount());
        }
    }

    @Nested
    @DisplayName("getTopAncestorsByDescendants")
    class TopByDescendants {

        @Test
        void ordersByDescendantCountDescending() {
            List<TopAncestor> result = statsService.getTopAncestorsByDescendants();

            assertThat(result).isNotEmpty();
            for (int i = 1; i < result.size(); i++) {
                assertThat(result.get(i - 1).descendantCount())
                    .isGreaterThanOrEqualTo(result.get(i).descendantCount());
            }
        }

        @Test
        void countsTransitiveDescendants() {
            // Arthur Goodall (4004) heads a multi-generation subtree.
            TopAncestor arthurGoodall = statsService.getTopAncestorsByDescendants().stream()
                .filter(a -> a.id() == ARTHUR_GOODALL).findFirst().orElseThrow();

            assertThat(arthurGoodall.descendantCount()).isGreaterThan(1L);
        }
    }
}
