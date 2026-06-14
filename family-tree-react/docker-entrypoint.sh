#!/bin/sh
# Runs (via nginx:alpine's /docker-entrypoint.d) before nginx starts.
# Writes a runtime config the SPA reads as window.__ENV__, so the same image
# is configured per-environment purely through container env vars.
set -e

cat > /usr/share/nginx/html/env.js <<EOF
window.__ENV__ = {
  API_BASE: "${API_BASE:-}",
  KEYCLOAK_URL: "${KEYCLOAK_URL:-}",
  KEYCLOAK_REALM: "${KEYCLOAK_REALM:-family-tree}",
  KEYCLOAK_CLIENT_ID: "${KEYCLOAK_CLIENT_ID:-family-tree-frontend}"
};
EOF

echo "wrote /usr/share/nginx/html/env.js (API_BASE=${API_BASE:-<empty>})"
