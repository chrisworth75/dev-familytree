package com.familytree.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class AvatarOverlayServiceTest {

    private AvatarOverlayService service;

    @BeforeEach
    void setUp() {
        service = new AvatarOverlayService();
    }

    @Nested
    @DisplayName("overlayAvatars")
    class OverlayAvatars {

        @Test
        void returnsUnchangedWhenNoAvatars() {
            String svg = "<svg><g class=\"node\" data-person-id=\"1\"><circle r=\"48\"/></g></svg>";

            String result = service.overlayAvatars(svg, Map.of(), 48);

            assertThat(result).isEqualTo(svg);
        }

        @Test
        void returnsUnchangedWhenNullAvatars() {
            String svg = "<svg><g class=\"node\" data-person-id=\"1\"><circle r=\"48\"/></g></svg>";

            String result = service.overlayAvatars(svg, null, 48);

            assertThat(result).isEqualTo(svg);
        }

        @Test
        void addsAvatarClipPathToDefs() {
            String svg = "<svg><defs></defs><g class=\"node\" data-person-id=\"123\"><circle r=\"48\"/></g></svg>";

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/test.jpg"), 48);

            assertThat(result).contains("clipPath id=\"avatar-clip-123\"");
        }

        @Test
        void addsImageElementAfterCircle() {
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="123">
                <circle r="48" fill="#2196f3"/>
                <text dy="0.35em" fill="#fff" font-size="20px">AB</text>
                </g></svg>""";

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/avatar.jpg"), 48);

            // XML serializer may order attributes differently, so check each separately
            assertThat(result).contains("href=\"/uploads/avatar.jpg\"");
            assertThat(result).contains("clip-path=\"url(#avatar-clip-123)\"");
        }

        @Test
        void removesInitialsTextWhenAvatarAdded() {
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="123">
                <circle r="48" fill="#2196f3"/>
                <text dy="0.35em" text-anchor="middle" font-size="20px" font-weight="bold" fill="#fff">AB</text>
                <text y="68">Name</text>
                </g></svg>""";

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/avatar.jpg"), 48);

            // Initials text (dy="0.35em" fill="#fff") should be removed
            assertThat(result).doesNotContain(">AB</text>");
            // But name text (y="68") should remain
            assertThat(result).contains("y=\"68\"");
        }

        @Test
        void preservesNameLabelsOnSmallNodes() {
            // Ancestors/descendants trees use small nodes (r=8) with name labels
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="123">
                <circle r="8" fill="#2196f3" stroke="#fff" stroke-width="2"/>
                <text dy="0.35em" x="12" text-anchor="start" font-family="Arial, sans-serif" font-size="12px" fill="#333">Arthur Worthington</text>
                </g></svg>""";

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/avatar.jpg"), 8);

            // Avatar should be added with small dimensions
            assertThat(result).contains("width=\"16\"");
            assertThat(result).contains("height=\"16\"");
            assertThat(result).contains("x=\"-8\"");
            assertThat(result).contains("y=\"-8\"");
            // Name label (fill="#333") should NOT be removed
            assertThat(result).contains(">Arthur Worthington</text>");
        }

        @Test
        void updatesExistingImageHref() {
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="123">
                <circle r="48"/>
                <image href="avatars/old.jpg" x="-48" y="-48"/>
                </g></svg>""";

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/avatars/new.jpg"), 48);

            assertThat(result).contains("href=\"/uploads/avatars/new.jpg\"");
            assertThat(result).doesNotContain("avatars/old.jpg");
        }

        @Test
        void handlesMultipleNodes() {
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="1"><circle r="48"/><text dy="0.35em" fill="#fff" font-size="20px">A</text></g>
                <g class="node" data-person-id="2"><circle r="48"/><text dy="0.35em" fill="#fff" font-size="20px">B</text></g>
                <g class="node" data-person-id="3"><circle r="48"/><text dy="0.35em" fill="#fff" font-size="20px">C</text></g>
                </svg>""";

            // Only person 1 and 3 have avatars
            String result = service.overlayAvatars(svg, Map.of(
                1L, "/uploads/a.jpg",
                3L, "/uploads/c.jpg"
            ), 48);

            assertThat(result).contains("avatar-clip-1");
            assertThat(result).contains("avatar-clip-3");
            assertThat(result).doesNotContain("avatar-clip-2");

            // Person 2 should still have initials
            assertThat(result).contains(">B</text>");
        }

        @Test
        void preservesNodeWithoutAvatar() {
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="999">
                <circle r="48" fill="#e91e63"/>
                <text dy="0.35em" fill="#fff" font-size="20px">XY</text>
                </g></svg>""";

            // No avatar for person 999
            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/other.jpg"), 48);

            // Node 999 should be unchanged
            assertThat(result).contains("data-person-id=\"999\"");
            assertThat(result).contains(">XY</text>");
            assertThat(result).doesNotContain("avatar-clip-999");
        }
    }
}
