package com.familytree.config;

import com.familytree.model.FamilyTreeConfig;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.ArrayList;
import java.util.List;

/**
 * Configuration for available family trees.
 * Define trees in application.yml under 'familytree.trees'
 */
@Configuration
@ConfigurationProperties(prefix = "familytree")
public class TreesConfig {

    private List<TreeDefinition> trees = new ArrayList<>();

    public List<TreeDefinition> getTrees() {
        return trees;
    }

    public void setTrees(List<TreeDefinition> trees) {
        this.trees = trees;
    }

    public List<FamilyTreeConfig> getTreesForUser(String username) {
        return trees.stream()
            .map(TreeDefinition::toConfig)
            .filter(tree -> tree.isAccessibleBy(username))
            .toList();
    }

    public FamilyTreeConfig getTreeBySlug(String slug) {
        return trees.stream()
            .filter(t -> t.getSlug().equals(slug))
            .map(TreeDefinition::toConfig)
            .findFirst()
            .orElse(null);
    }

    /**
     * Mutable class for Spring Boot configuration binding
     */
    public static class TreeDefinition {
        private String slug;
        private String displayName;
        private String subtitle;
        private String initials;
        private String avatarColor;
        private Integer personCount;
        private List<String> allowedUsers = new ArrayList<>();

        public FamilyTreeConfig toConfig() {
            return new FamilyTreeConfig(
                slug, displayName, subtitle, initials, avatarColor, personCount, allowedUsers
            );
        }

        // Getters and setters for Spring Boot binding
        public String getSlug() { return slug; }
        public void setSlug(String slug) { this.slug = slug; }

        public String getDisplayName() { return displayName; }
        public void setDisplayName(String displayName) { this.displayName = displayName; }

        public String getSubtitle() { return subtitle; }
        public void setSubtitle(String subtitle) { this.subtitle = subtitle; }

        public String getInitials() { return initials; }
        public void setInitials(String initials) { this.initials = initials; }

        public String getAvatarColor() { return avatarColor; }
        public void setAvatarColor(String avatarColor) { this.avatarColor = avatarColor; }

        public Integer getPersonCount() { return personCount; }
        public void setPersonCount(Integer personCount) { this.personCount = personCount; }

        public List<String> getAllowedUsers() { return allowedUsers; }
        public void setAllowedUsers(List<String> allowedUsers) { this.allowedUsers = allowedUsers; }
    }
}
