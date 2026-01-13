package com.familytree.model;

import java.util.List;

/**
 * Configuration for a family tree displayed on the landing page.
 * Trees are configured in application.yml rather than stored in the database.
 */
public record FamilyTreeConfig(
    String slug,           // URL-safe identifier, e.g. "worthington"
    String displayName,    // Display name, e.g. "Worthington Family"
    String subtitle,       // Subtitle, e.g. "Yorkshire, England"
    String initials,       // Avatar initials, e.g. "WF"
    String avatarColor,    // CSS class for avatar color: blue, teal, green, olive, brown, rust, rose, purple, slate
    Integer personCount,   // Number of people (for display)
    List<String> allowedUsers  // Usernames who can access this tree
) {
    public boolean isAccessibleBy(String username) {
        return allowedUsers != null && allowedUsers.contains(username);
    }
}
