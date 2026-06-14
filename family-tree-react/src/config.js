// Runtime config, read from window.__ENV__ (see index.html / public/env.js).
// Falls back to local-dev defaults so `vite dev` works with no env.js values.
const env = (typeof window !== 'undefined' && window.__ENV__) || {};

export const API_BASE = env.API_BASE || 'http://localhost:3200';
export const MY_PERSON_ID = 1000;

// Which deploy tier this instance is (e.g. "1 · local"). Shown by TierBanner.
export const TIER = env.TIER || '';

// Keycloak settings — consumed by the upcoming React auth phase.
export const KEYCLOAK_URL = env.KEYCLOAK_URL || 'http://localhost:8081';
export const KEYCLOAK_REALM = env.KEYCLOAK_REALM || 'family-tree';
export const KEYCLOAK_CLIENT_ID = env.KEYCLOAK_CLIENT_ID || 'family-tree-frontend';
