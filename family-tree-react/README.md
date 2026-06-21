# Family Tree React

React frontend for the Family Tree genealogy application. Displays family trees with D3.js visualizations.

## Tech Stack

- React 19
- Vite
- D3.js for tree visualization
- React Router

## Running locally from the IDEs (the everyday setup)

This is the frontend half of the IDE workflow described in
`../family-tree-app/README.md`. Three things must be up: the **API**, **Keycloak**,
and this **dev server**.

```bash
# Install deps (first time only)
npm install

# Start the Vite dev server
npm run dev
```

App available at http://localhost:4202. Vite proxies `/api` (and `/uploads`) to the
backend on `:3200`, so you don't hit CORS. At the Keycloak login page, sign in as
**`dev-owner` / `dev-owner`**.

### Auth — the frontend DOES need Keycloak (unlike the API)

This is the important difference from the backend. The API can run standalone with
Basic auth, but **the React UI cannot run without Keycloak**:

- `main.jsx` calls `keycloak.init({ onLoad: 'login-required' })`, which **redirects to
  Keycloak before the app renders**. After login, `api.js` attaches the `Bearer` token
  to every `/api` call (the UI uses JWT, not Basic).
- If Keycloak is unreachable you get a **"Sign-in unavailable"** page instead of the app.
- Local-dev config comes from `src/config.js` defaults (because `public/env.js` is empty
  in dev): Keycloak `http://localhost:8081`, realm `family-tree`, client
  `family-tree-frontend`, API `http://localhost:3200`. No env file to edit.
- **Login: `dev-owner` / `dev-owner`.**

So to run the UI you need **all of**:

1. **API** on `:3200` — run the backend with the `bigtree` profile
   (`cd ../family-tree-app && mvn spring-boot:run -Dspring-boot.run.profiles=bigtree`).
2. **Keycloak** on `:8081` with the `family-tree` realm — the `keycloak` service in
   `../family-tree-app/docker-compose.dev.yml` is set to `restart: unless-stopped`, so it
   **auto-starts with Docker Desktop** and is normally already up. If not (or after an
   explicit stop): `docker compose -f ../family-tree-app/docker-compose.dev.yml up -d keycloak`.
   ⚠️ only one Keycloak can own :8081 — stop `vote-keycloak` if it's holding the port.
3. **D3 tree renderer** on `:3300` — the API proxies tree rendering to it; **without it the
   UI loads but trees stay empty**. The `d3` service (same compose file) also has
   `restart: unless-stopped`, so it auto-starts with Docker Desktop. If not:
   `docker compose -f ../family-tree-app/docker-compose.dev.yml up -d d3`.
4. **This dev server** (`npm run dev`).

> If you only need to poke the **API** (not the UI), skip all of this — use curl/Bruno
> with Basic `chris/chris`. See `../family-tree-app/README.md` → "Auth in this setup".

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server with HMR |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
