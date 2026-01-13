package com.familytree.model;

/**
 * Simple user record for authentication.
 * Users are configured in SecurityConfig - no database table needed for MVP.
 */
public record AppUser(
    String username,
    String displayName,
    String role
) {}
