package com.familytree.service;

import com.familytree.service.TreeDataService.TreeNode;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Tests for TreeDataService using real Worthington family data.
 *
 * Structure:
 *     Henry Wrathall (575341) ─┬─ Mary Alice (511037)
 *                              │
 *     Arthur Goodall (4004) ───┼─── Constance Mary Wrathall (4005)
 *                              │
 *         ┌────────────────────┴────────────────────┐
 *         │                                         │
 *     Arthur Gordon (3002) ─┬─ Marjorie         Bryan (31)
 *                           │
 *     ┌─────────┬───────────┴───────────┬───────────┐
 *     │         │                       │           │
 * Jonathan   Rosalind               David        Tony
 *  (2001)    (2002)                 (2003)      (2004)
 *     │
 *  ┌──┴───┬────────┬────────┐
 *  │      │        │        │
 * Tim   Chris   Rebecca  Jennifer
 * (1001) (1000)  (1002)   (1003)
 *          │                 │
 *     ┌────┴────┐       ┌────┴────┐
 *     │         │       │         │
 *   Hugo    Zachary    Joe     Grace
 *   (100)    (101)    (400)    (401)
 */
@SpringBootTest
@ActiveProfiles("test")
@Transactional
@Sql("/worthington-family.sql")
class TreeDataServiceTest {

    @Autowired
    private TreeDataService treeDataService;

    // Known IDs from test data
    private static final Long HENRY_WRATHALL = 575341L;
    private static final Long MARY_ALICE = 511037L;
    private static final Long CONSTANCE = 4005L;
    private static final Long ARTHUR_GOODALL = 4004L;
    private static final Long ARTHUR_GORDON = 3002L;
    private static final Long MARJORIE = 3003L;
    private static final Long BRYAN = 31L;
    private static final Long JONATHAN = 2001L;
    private static final Long PATRICIA = 2000L;
    private static final Long ROSALIND = 2002L;
    private static final Long DAVID = 2003L;
    private static final Long TONY = 2004L;
    private static final Long TIMOTHY = 1001L;
    private static final Long CHRIS = 1000L;
    private static final Long SARAH = 1004L;
    private static final Long REBECCA = 1002L;
    private static final Long JENNIFER = 1003L;
    private static final Long HUGO = 100L;
    private static final Long ZACHARY = 101L;
    private static final Long JOE = 400L;
    private static final Long GRACE = 401L;
    private static final Long BRUCE = 900200L;
    private static final Long STUART = 900201L;
    private static final Long CAITLYN = 900202L;
    private static final Long FRANK_UNRELATED = 99001L;
    private static final Long PAT_NULL_GENDER = 99003L;
    private static final Long NON_EXISTENT = 999999L;

    // ========== DESCENDANTS ==========

    @Nested
    class BuildDescendantsHierarchy {

        @Test
        void returnsEmptyWhenPersonNotFound() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(NON_EXISTENT, 10);

            assertThat(result).isEmpty();
        }

        @Test
        void returnsSingleNodeWhenNoChildren() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(HUGO, 10);

            assertThat(result).isPresent();
            TreeNode node = result.get();
            assertThat(node.getId()).isEqualTo(HUGO);
            assertThat(node.getName()).isEqualTo("Hugo Worthington");
            assertThat(node.getGender()).isEqualTo("M");
            assertThat(node.getChildren()).isNull();
        }

        @Test
        void includesSpouseInfo() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(CHRIS, 10);

            assertThat(result).isPresent();
            TreeNode node = result.get();
            assertThat(node.getSpouse()).isEqualTo("Sarah Worthington");
            assertThat(node.getSpouseId()).isEqualTo(SARAH);
        }

        @Test
        void buildsTreeWithChildren() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(JONATHAN, 10);

            assertThat(result).isPresent();
            TreeNode node = result.get();
            assertThat(node.getChildren()).hasSize(4);
            assertThat(node.getChildren()).extracting(TreeNode::getName)
                    .containsExactlyInAnyOrder(
                            "Timothy Jonathon Patrick Worthington",
                            "Chris Worthington",
                            "Rebecca Worthington",
                            "Jennifer Clare Worthington"
                    );
        }

        @Test
        void sortsChildrenByBirthYear() {
            // Jonathan's children: Tim (1974), Chris (1975), Rebecca (1978), Jennifer (1982)
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(JONATHAN, 10);

            assertThat(result).isPresent();
            assertThat(result.get().getChildren()).extracting(TreeNode::getName)
                    .containsExactly(
                            "Timothy Jonathon Patrick Worthington",
                            "Chris Worthington",
                            "Rebecca Worthington",
                            "Jennifer Clare Worthington"
                    );
        }

        @Test
        void respectsMaxDepthOfOne() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(ARTHUR_GORDON, 1);

            assertThat(result).isPresent();
            assertThat(result.get().getChildren()).isNull();
        }

        @Test
        void respectsMaxDepthOfTwo() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(ARTHUR_GORDON, 2);

            assertThat(result).isPresent();
            TreeNode arthurGordon = result.get();
            assertThat(arthurGordon.getChildren()).hasSize(4); // Jonathan, Rosalind, David, Tony

            for (TreeNode child : arthurGordon.getChildren()) {
                assertThat(child.getChildren()).isNull();
            }
        }

        @Test
        void buildsThreeGenerations() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(ARTHUR_GORDON, 10);

            assertThat(result).isPresent();
            TreeNode arthurGordon = result.get();
            assertThat(arthurGordon.getName()).isEqualTo("Arthur Gordon Lonsdale Worthington");

            TreeNode jonathan = arthurGordon.getChildren().stream()
                    .filter(n -> n.getName().equals("Jonathan P Worthington"))
                    .findFirst().orElseThrow();
            assertThat(jonathan.getChildren()).hasSize(4);

            TreeNode chris = jonathan.getChildren().stream()
                    .filter(n -> n.getName().equals("Chris Worthington"))
                    .findFirst().orElseThrow();
            assertThat(chris.getChildren()).hasSize(2); // Hugo and Zachary
        }

        @Test
        void buildsFourGenerationsFromConstance() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(CONSTANCE, 10);

            assertThat(result).isPresent();
            TreeNode constance = result.get();
            assertThat(constance.getChildren()).hasSize(2); // Arthur Gordon and Bryan

            TreeNode arthurGordon = constance.getChildren().stream()
                    .filter(n -> n.getName().contains("Arthur"))
                    .findFirst().orElseThrow();
            assertThat(arthurGordon.getChildren()).hasSize(4);

            TreeNode jonathan = arthurGordon.getChildren().stream()
                    .filter(n -> n.getName().equals("Jonathan P Worthington"))
                    .findFirst().orElseThrow();
            assertThat(jonathan.getChildren()).hasSize(4);
        }

        @Test
        void includesBryanAsSiblingBranch() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(CONSTANCE, 10);

            assertThat(result).isPresent();
            assertThat(result.get().getChildren()).extracting(TreeNode::getName)
                    .contains("Bryan Worthington");
        }
    }

    // ========== ANCESTORS ==========

    @Nested
    class BuildAncestorsHierarchy {

        @Test
        void returnsEmptyWhenPersonNotFound() {
            Optional<TreeNode> result = treeDataService.buildAncestorsHierarchy(NON_EXISTENT, 10);

            assertThat(result).isEmpty();
        }

        @Test
        void returnsSingleNodeWhenNoParents() {
            Optional<TreeNode> result = treeDataService.buildAncestorsHierarchy(HENRY_WRATHALL, 10);

            assertThat(result).isPresent();
            TreeNode node = result.get();
            assertThat(node.getId()).isEqualTo(HENRY_WRATHALL);
            assertThat(node.getChildren()).isNull();
        }

        @Test
        void buildsTreeWithBothParents() {
            Optional<TreeNode> result = treeDataService.buildAncestorsHierarchy(CHRIS, 10);

            assertThat(result).isPresent();
            TreeNode chris = result.get();
            assertThat(chris.getChildren()).hasSize(2);
            assertThat(chris.getChildren()).extracting(TreeNode::getName)
                    .containsExactlyInAnyOrder("Jonathan P Worthington", "Patricia Worthington");
        }

        @Test
        void buildsTreeWithOneParent() {
            // Bruce only has mother (Rosalind)
            Optional<TreeNode> result = treeDataService.buildAncestorsHierarchy(BRUCE, 10);

            assertThat(result).isPresent();
            TreeNode bruce = result.get();
            assertThat(bruce.getChildren()).hasSize(1);
            assertThat(bruce.getChildren().get(0).getName()).isEqualTo("Rosalind Worthington");
        }

        @Test
        void buildsFourGenerationsFromHugo() {
            // Hugo -> Chris -> Jonathan -> Arthur Gordon -> Constance/Arthur Goodall
            Optional<TreeNode> result = treeDataService.buildAncestorsHierarchy(HUGO, 10);

            assertThat(result).isPresent();
            TreeNode hugo = result.get();
            assertThat(hugo.getName()).isEqualTo("Hugo Worthington");

            TreeNode chris = hugo.getChildren().stream()
                    .filter(n -> n.getName().equals("Chris Worthington"))
                    .findFirst().orElseThrow();

            TreeNode jonathan = chris.getChildren().stream()
                    .filter(n -> n.getName().equals("Jonathan P Worthington"))
                    .findFirst().orElseThrow();

            TreeNode arthurGordon = jonathan.getChildren().stream()
                    .filter(n -> n.getName().contains("Arthur Gordon"))
                    .findFirst().orElseThrow();

            assertThat(arthurGordon.getChildren()).hasSize(2); // Constance and Arthur Goodall
        }

        @Test
        void reachesConstanceFromChris() {
            Optional<TreeNode> result = treeDataService.buildAncestorsHierarchy(CHRIS, 10);

            assertThat(result).isPresent();

            // Navigate: Chris -> Jonathan -> Arthur Gordon -> Constance
            TreeNode chris = result.get();
            TreeNode jonathan = chris.getChildren().stream()
                    .filter(n -> n.getName().equals("Jonathan P Worthington"))
                    .findFirst().orElseThrow();
            TreeNode arthurGordon = jonathan.getChildren().stream()
                    .filter(n -> n.getName().contains("Arthur Gordon"))
                    .findFirst().orElseThrow();

            assertThat(arthurGordon.getChildren()).extracting(TreeNode::getName)
                    .contains("Constance Mary Worthington");
        }

        @Test
        void respectsMaxDepthOfTwo() {
            Optional<TreeNode> result = treeDataService.buildAncestorsHierarchy(CHRIS, 2);

            assertThat(result).isPresent();
            TreeNode chris = result.get();
            assertThat(chris.getChildren()).hasSize(2); // Jonathan and Patricia

            for (TreeNode parent : chris.getChildren()) {
                assertThat(parent.getChildren()).isNull();
            }
        }

        @Test
        void includesSpouseInfo() {
            Optional<TreeNode> result = treeDataService.buildAncestorsHierarchy(ARTHUR_GORDON, 10);

            assertThat(result).isPresent();
            TreeNode arthurGordon = result.get();
            assertThat(arthurGordon.getSpouse()).isEqualTo("Marjorie Worthington");
            assertThat(arthurGordon.getSpouseId()).isEqualTo(MARJORIE);
        }
    }

    // ========== MRCA ==========

    @Nested
    class BuildMrcaPath {

        @Test
        void returnsEmptyWhenPersonANotFound() {
            Optional<TreeNode> result = treeDataService.buildMrcaPath(NON_EXISTENT, CHRIS);

            assertThat(result).isEmpty();
        }

        @Test
        void returnsEmptyWhenPersonBNotFound() {
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, NON_EXISTENT);

            assertThat(result).isEmpty();
        }

        @Test
        void returnsEmptyWhenNoCommonAncestor() {
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, FRANK_UNRELATED);

            assertThat(result).isEmpty();
        }

        @Test
        void findsMrcaForSiblings() {
            // Chris and Timothy are siblings - MRCA is Jonathan
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, TIMOTHY);

            assertThat(result).isPresent();
            TreeNode mrca = result.get();
            assertThat(mrca.getName()).isEqualTo("Jonathan P Worthington");
            assertThat(mrca.getChildren()).hasSize(2);
            assertThat(mrca.getChildren()).extracting(TreeNode::getName)
                    .containsExactlyInAnyOrder("Chris Worthington", "Timothy Jonathon Patrick Worthington");
        }

        @Test
        void findsMrcaForChrisAndJennifer() {
            // Chris and Jennifer are siblings - MRCA is Jonathan
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, JENNIFER);

            assertThat(result).isPresent();
            assertThat(result.get().getName()).isEqualTo("Jonathan P Worthington");
        }

        @Test
        void findsMrcaForCousins() {
            // Chris and Bruce are cousins - MRCA is Arthur Gordon
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, BRUCE);

            assertThat(result).isPresent();
            TreeNode mrca = result.get();
            assertThat(mrca.getName()).isEqualTo("Arthur Gordon Lonsdale Worthington");
            assertThat(mrca.getChildren()).hasSize(2);
        }

        @Test
        void mrcaPathIncludesIntermediateGenerations() {
            // Chris and Bruce: Arthur Gordon -> Jonathan -> Chris, Arthur Gordon -> Rosalind -> Bruce
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, BRUCE);

            assertThat(result).isPresent();
            TreeNode arthurGordon = result.get();

            for (TreeNode branch : arthurGordon.getChildren()) {
                String name = branch.getName();
                if (name.equals("Jonathan P Worthington")) {
                    assertThat(branch.getChildren()).hasSize(1);
                    assertThat(branch.getChildren().get(0).getName()).isEqualTo("Chris Worthington");
                } else if (name.equals("Rosalind Worthington")) {
                    assertThat(branch.getChildren()).hasSize(1);
                    assertThat(branch.getChildren().get(0).getName()).isEqualTo("Bruce Worthington");
                }
            }
        }

        @Test
        void findsMrcaForHugoAndJoe() {
            // Hugo (Chris's son) and Joe (Jennifer's son) - MRCA is Jonathan
            Optional<TreeNode> result = treeDataService.buildMrcaPath(HUGO, JOE);

            assertThat(result).isPresent();
            assertThat(result.get().getName()).isEqualTo("Jonathan P Worthington");
        }

        @Test
        void findsMrcaForHugoAndCaitlyn() {
            // Hugo (Chris -> Jonathan -> Arthur Gordon) and Caitlyn (Bruce -> Rosalind -> Arthur Gordon)
            // MRCA is Arthur Gordon
            Optional<TreeNode> result = treeDataService.buildMrcaPath(HUGO, CAITLYN);

            assertThat(result).isPresent();
            assertThat(result.get().getName()).isEqualTo("Arthur Gordon Lonsdale Worthington");
        }

        @Test
        void choosesClosestMrca() {
            // Chris and Bruce share both Arthur Gordon and Constance as ancestors
            // Should choose Arthur Gordon (closer)
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, BRUCE);

            assertThat(result).isPresent();
            assertThat(result.get().getName()).isEqualTo("Arthur Gordon Lonsdale Worthington");
        }

        @Test
        void handlesDirectAncestor() {
            // Jonathan and Chris - Jonathan is direct ancestor
            Optional<TreeNode> result = treeDataService.buildMrcaPath(JONATHAN, CHRIS);

            assertThat(result).isPresent();
            assertThat(result.get().getName()).isEqualTo("Jonathan P Worthington");
        }

        @Test
        void handlesSamePerson() {
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, CHRIS);

            assertThat(result).isPresent();
            assertThat(result.get().getName()).isEqualTo("Chris Worthington");
        }

        @Test
        void findsMrcaForChrisAndBryan() {
            // Chris (Jonathan -> Arthur Gordon -> Constance) and Bryan (-> Constance)
            // MRCA is Constance or Arthur Goodall
            Optional<TreeNode> result = treeDataService.buildMrcaPath(CHRIS, BRYAN);

            assertThat(result).isPresent();
            assertThat(result.get().getName()).containsAnyOf("Constance", "Arthur Goodall");
        }
    }

    // ========== DATE FORMATTING ==========

    @Nested
    class DateFormatting {

        @Test
        void formatsBirthDateAsYear() {
            // Chris: born 1975-09-30
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(CHRIS, 1);

            assertThat(result).isPresent();
            assertThat(result.get().getDates()).isEqualTo("1975-");
        }

        @Test
        void handlesNoDates() {
            // Bryan: no dates
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(BRYAN, 1);

            assertThat(result).isPresent();
            assertThat(result.get().getDates()).isEqualTo("-");
        }
    }

    // ========== GENDER DETECTION ==========

    @Nested
    class GenderDetection {

        @Test
        void returnsMale() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(CHRIS, 1);

            assertThat(result).isPresent();
            assertThat(result.get().getGender()).isEqualTo("M");
        }

        @Test
        void returnsFemale() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(JENNIFER, 1);

            assertThat(result).isPresent();
            assertThat(result.get().getGender()).isEqualTo("F");
        }

        @Test
        void returnsUnknownWhenNull() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(PAT_NULL_GENDER, 1);

            assertThat(result).isPresent();
            assertThat(result.get().getGender()).isEqualTo("U");
        }
    }

    // ========== AVATAR PATH ==========

    @Nested
    class AvatarPath {

        @Test
        void includesAvatarPath() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(CHRIS, 1);

            assertThat(result).isPresent();
            assertThat(result.get().getAvatarPath()).isEqualTo("avatars/chris.jpg");
        }

        @Test
        void handlesNullAvatarPath() {
            Optional<TreeNode> result = treeDataService.buildDescendantsHierarchy(HUGO, 1);

            assertThat(result).isPresent();
            assertThat(result.get().getAvatarPath()).isNull();
        }
    }
}