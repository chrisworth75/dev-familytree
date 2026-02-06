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

            String result = service.overlayAvatars(svg, Map.of());

            assertThat(result).isEqualTo(svg);
        }

        @Test
        void returnsUnchangedWhenNullAvatars() {
            String svg = "<svg><g class=\"node\" data-person-id=\"1\"><circle r=\"48\"/></g></svg>";

            String result = service.overlayAvatars(svg, null);

            assertThat(result).isEqualTo(svg);
        }

        @Test
        void addsAvatarClipPathToDefs() {
            String svg = "<svg><defs></defs><g class=\"node\" data-person-id=\"123\"><circle r=\"48\"/></g></svg>";

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/test.jpg"));

            assertThat(result).contains("clipPath id=\"avatar-clip-123\"");
        }

        @Test
        void addsImageElementAfterCircle() {
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="123">
                <circle r="48" fill="#2196f3"/>
                <text dy="0.35em" font-size="20px">AB</text>
                </g></svg>""";

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/avatar.jpg"));

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

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/avatar.jpg"));

            // Initials text (dy="0.35em" font-size="20px") should be removed
            assertThat(result).doesNotContain("dy=\"0.35em\"");
            // But name text (y="68") should remain
            assertThat(result).contains("y=\"68\"");
        }

        @Test
        void updatesExistingImageHref() {
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="123">
                <circle r="48"/>
                <image href="avatars/old.jpg" x="-48" y="-48"/>
                </g></svg>""";

            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/avatars/new.jpg"));

            assertThat(result).contains("href=\"/uploads/avatars/new.jpg\"");
            assertThat(result).doesNotContain("avatars/old.jpg");
        }

        @Test
        void handlesMultipleNodes() {
            String svg = """
                <svg><defs></defs>
                <g class="node" data-person-id="1"><circle r="48"/><text dy="0.35em" font-size="20px">A</text></g>
                <g class="node" data-person-id="2"><circle r="48"/><text dy="0.35em" font-size="20px">B</text></g>
                <g class="node" data-person-id="3"><circle r="48"/><text dy="0.35em" font-size="20px">C</text></g>
                </svg>""";

            // Only person 1 and 3 have avatars
            String result = service.overlayAvatars(svg, Map.of(
                1L, "/uploads/a.jpg",
                3L, "/uploads/c.jpg"
            ));

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
                <text dy="0.35em" font-size="20px">XY</text>
                </g></svg>""";

            // No avatar for person 999
            String result = service.overlayAvatars(svg, Map.of(123L, "/uploads/other.jpg"));

            // Node 999 should be unchanged
            assertThat(result).contains("data-person-id=\"999\"");
            assertThat(result).contains(">XY</text>");
            assertThat(result).doesNotContain("avatar-clip-999");
        }
    }
}
