package com.familytree.model;

/** Aggregate counts shown on the dashboard. */
public record DashboardStats(
    long treeSize,
    long dnaMatchCount,
    long linkedMatches,
    long unlinkedMatches,
    long linkedPeopleCount
) {}
