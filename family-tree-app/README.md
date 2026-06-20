# Family Tree API

Spring Boot API for CRUD operations on the database


## Tech Stack

- Java 21 / Spring Boot
- PostgreSQL 16
- Flyway migrations

## Running locally from the IDEs (the everyday setup)

Run React + Spring straight from IntelliJ/WebStorm, pointed at the **native**
Postgres on this Mac (the "Chris's Big Fat Tree" DB in DataGrip — your real ~79k-person
research). No Docker, no tiers.

1. **Database** — native Postgres, auto-starts at login. If it's not up:
   ```bash
   brew services start postgresql@16
   ```
   It serves db `familytree` on `localhost:5432` (user/pass `familytree`/`familytree`).

2. **Backend** — run with the `bigtree` profile:
   ```bash
   cd family-tree-app && mvn spring-boot:run -Dspring-boot.run.profiles=bigtree
   ```
   (or set Active profiles = `bigtree` in the IntelliJ run config)
   → API on http://localhost:3200. **Boots WITHOUT Keycloak** (see Auth below).

3. **Frontend** — only if you want the UI:
   ```bash
   cd family-tree-react && npm run dev
   ```
   → http://localhost:4202. ⚠️ React forces a Keycloak login, so for the UI you ALSO
   need Keycloak on :8081 (free that port from vote-keycloak first). Backend-only work
   needs no Keycloak.

### Auth in this setup (why there's no Keycloak login for the API)

`/api/**` is still secured — but the `bigtree` profile is wired so you never need
Keycloak to use the **API**:

- The profile uses a **lazy `jwk-set-uri`** (not `issuer-uri`), so the resource server
  validates a token's *signature only if one arrives* and **never contacts Keycloak at
  startup** — the app boots standalone.
- `SecurityConfig` accepts **HTTP Basic `chris`/`chris`** (an in-memory dev user) on
  `/api/**` *alongside* Keycloak JWTs. So for local work you just use Basic auth:
  ```bash
  curl -u chris:chris http://localhost:3200/api/stats
  ```
- **Bruno**: the `bruno-collection` has request-level Basic auth (`chris`/`chris`) baked
  into every request, so it just works — no token, no Keycloak prompt. (Note: the 401
  challenge advertises `Bearer`, but Basic is still accepted.)
- **The one exception is the React UI**: it does Keycloak `login-required`, so the
  *frontend* (and only the frontend) still needs Keycloak running on :8081. The API,
  curl, Bruno, and tests do not.

> ⚠️ `chris`/`chris` is a **dev-only** in-memory credential. Local convenience only —
> not a real account, never use this pattern in a deployed environment.

> Profiles cheat-sheet: `bigtree` = native DB, run from IDE (this), no Keycloak for the
> API · `dev` = same DB but eager `issuer-uri`, needs Keycloak up · `scratch` = empty test
> DB · `e2e`/`k8s` = containers/CI only.

## Running Locally (Docker + Keycloak)

```bash
# Start local Postgres and Keycloak
docker compose -f docker-compose.dev.yml up -d

# Run with real data
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# Run with empty test database
mvn spring-boot:run -Dspring-boot.run.profiles=scratch
```

API available at http://localhost:3200/api

### Local Keycloak

Local development uses Keycloak as an OAuth2 issuer for API JWT validation.

- Admin URL: http://localhost:8081
- Admin username/password: `admin` / `admin` (local dev only)
- Realm: `family-tree`
- Client: `family-tree-backend`
- Realm import: `../infra/keycloak/realm-export.json`
- Dev test user: `dev-owner` / `dev-owner` (local dev only)

Get a local access token:

```bash
TOKEN=$(curl -s -X POST \
  http://localhost:8081/realms/family-tree/protocol/openid-connect/token \
  -H 'content-type: application/x-www-form-urlencoded' \
  -d 'grant_type=password' \
  -d 'client_id=family-tree-backend' \
  -d 'username=dev-owner' \
  -d 'password=dev-owner' | jq -r .access_token)
```

Use it against the API:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:3200/api/me
```

The realm JSON is mounted into Keycloak at `/opt/keycloak/data/import` and imported with `--import-realm` when the container starts. All default passwords and the public password-grant client are for local development only; replace them and review client flow, role, and secret handling before any production deployment.

## Database Profiles

| Profile | Database | Use |
|---------|----------|-----|
| dev | familytree | Real data |
| scratch | familytree_test | Empty test database for API testing |

### Reset the test database

```bash
# Drop and recreate for a clean slate
docker exec familytree-postgres psql -U familytree -d postgres -c "DROP DATABASE IF EXISTS familytree_test; CREATE DATABASE familytree_test OWNER familytree;"
```

---

# API Journey

This section walks through the API endpoints in logical order, starting from an empty database. Use it as:

- **Test setup sequence** - each level depends on the previous
- **API documentation** - example payloads and expected responses
- **Onboarding guide** - understand the domain by following the user journey

---

## Level 1: Tree and First Person

Every person belongs to a tree. Create the tree first, then add people to it.

### 1.1 Create a Tree

```http
POST /tree
```

```json
{
  "name": "Worthington Family Tree",
  "source": "manual",
  "ownerName": "Chris Worthington",
  "notes": "Main research tree"
}
```

**Response: 201 Created**
```json
{
  "id": 1,
  "name": "Worthington Family Tree",
  "source": "manual",
  "ownerName": "Chris Worthington"
}
```

### 1.2 Create a Person in a Tree

```http
POST /tree/1/person
```

```json
{
  "firstName": "George",
  "surname": "Worthington",
  "birthYear": 1850,
  "deathYear": 1920,
  "birthPlace": "Bolton, Lancashire"
}
```

**Response: 201 Created**
```json
{
  "id": 1,
  "person": {
    "id": 1,
    "treeId": 1,
    "firstName": "George",
    "surname": "Worthington",
    "birthYear": 1850,
    "deathYear": 1920,
    "birthPlace": "Bolton, Lancashire"
  }
}
```

> **Note:** This person has no family connections yet. They're the starting point for building out the tree.

---

## Level 2: Family Relationships

Now we connect people together. These endpoints create a new person AND wire up the relationship in one call. The new person is created in the same tree as the target person.

### 2.1 Add a Spouse

Give George a wife.

```http
POST /person/1/spouse
```

```json
{
  "firstName": "Mary",
  "surname": "Smith",
  "birthYear": 1855,
  "deathYear": 1925,
  "birthPlace": "Wigan, Lancashire"
}
```

**Response: 201 Created**
```json
{
  "id": 2,
  "person": {
    "id": 2,
    "firstName": "Mary",
    "surname": "Smith",
    "birthYear": 1855
  }
}
```

> **What happened:** Created person id=2 in the same tree as person 1, created a partnership record linking them.

### 2.2 Add a Child

George and Mary have a son.

```http
POST /person/1/child
```

```json
{
  "parentGender": "M",
  "firstName": "James",
  "surname": "Worthington",
  "birthYear": 1880,
  "birthPlace": "Bolton, Lancashire"
}
```

**Response: 201 Created**
```json
{
  "id": 3,
  "person": {
    "id": 3,
    "firstName": "James",
    "surname": "Worthington",
    "birthYear": 1880
  }
}
```

> **What happened:** Created person id=3 with `parent_1_id` set to 1 (George). The `parentGender` tells us which parent slot to use.

### 2.3 Link the Other Parent

James needs Mary as his mother too. Add spouse as second parent.

```http
POST /person/3/parent
```

```json
{
  "gender": "F",
  "parentId": 2
}
```

**Response: 201 Created**
```json
{
  "id": 2,
  "person": {
    "id": 2,
    "firstName": "Mary",
    "surname": "Smith"
  }
}
```

> **What happened:** Linked existing person id=2 as James's `parent_2_id`. Note we used `parentId` to link an existing person rather than creating a new one.

### 2.4 Add a Parent (Creating New)

Add George's father - we don't have him in the system yet.

```http
POST /person/1/parent
```

```json
{
  "gender": "M",
  "firstName": "William",
  "surname": "Worthington",
  "birthYear": 1820,
  "deathYear": 1890
}
```

**Response: 201 Created**
```json
{
  "id": 4,
  "person": {
    "id": 4,
    "firstName": "William",
    "surname": "Worthington",
    "birthYear": 1820
  }
}
```

> **What happened:** Created person id=4 in the same tree, set as George's `parent_1_id`.

---

## Level 3: DNA Domain

DNA testers and their match relationships.

### 3.1 Create a DNA Tester

A DNA tester is someone who has taken a DNA test. They may or may not be linked to a person in the tree.

```http
POST /dna-tester
```

```json
{
  "dnaTestId": "e756de6c-0c8d-443b-8793-addb6f35fd6a",
  "name": "Chris Worthington",
  "hasTree": true,
  "treeSize": 500,
  "adminLevel": 0,
  "notes": "My own test",
  "personId": null
}
```

**Response: 201 Created**
```json
{
  "dna_test_id": "e756de6c-0c8d-443b-8793-addb6f35fd6a",
  "name": "Chris Worthington",
  "has_tree": true,
  "tree_size": 500
}
```

### 3.2 Create Another Tester (A Match)

Someone who shows up as a DNA match.

```http
POST /dna-tester
```

```json
{
  "dnaTestId": "abc-123-def-456",
  "name": "John Smith",
  "hasTree": true,
  "treeSize": 50,
  "adminLevel": 0,
  "notes": "Possible 2nd cousin, paternal side"
}
```

**Response: 201 Created**

### 3.3 Create a DNA Match Relationship

Link two testers as DNA matches with shared cM data.

```http
POST /dna-match
```

```json
{
  "tester1Id": "e756de6c-0c8d-443b-8793-addb6f35fd6a",
  "tester2Id": "abc-123-def-456",
  "sharedCm": 125.5,
  "sharedSegments": 8,
  "predictedRelationship": "2nd Cousin",
  "matchSide": "paternal"
}
```

**Response: 201 Created**
```json
{
  "tester_1_id": "e756de6c-0c8d-443b-8793-addb6f35fd6a",
  "tester_2_id": "abc-123-def-456",
  "shared_cm": 125.5,
  "shared_segments": 8,
  "predicted_relationship": "2nd Cousin",
  "match_side": "paternal"
}
```

---

## Level 4: Read Endpoints

Now we have data, we can test all the GET endpoints.

### 4.1 Get Person with Family Context

```http
GET /person/1
```

**Response: 200 OK**
```json
{
  "person": {
    "id": 1,
    "treeId": 1,
    "firstName": "George",
    "surname": "Worthington",
    "birthYear": 1850,
    "deathYear": 1920
  },
  "father": { "id": 4, "firstName": "William", "surname": "Worthington" },
  "mother": null,
  "spouses": [{ "id": 2, "firstName": "Mary", "surname": "Smith" }],
  "children": [{ "id": 3, "firstName": "James", "surname": "Worthington" }],
  "siblings": []
}
```

### 4.2 Get Ancestors

```http
GET /person/3/ancestors?generations=5
```

Returns flat list of all ancestors up the tree.

### 4.3 Get Descendants

```http
GET /person/4/descendants?generations=5
```

Returns flat list of all descendants down the tree.

### 4.4 Get Descendants Hierarchy

```http
GET /person/4/descendants/hierarchy?maxDepth=5
```

Returns nested JSON suitable for D3.js visualisation.

### 4.5 Get Tree Hierarchy

```http
GET /tree/{slug}/hierarchy
```

Returns the full tree as nested JSON for visualisation.

### 4.6 Get Dashboard Stats

```http
GET /stats
```

**Response: 200 OK**
```json
{
  "treeSize": 4,
  "dnaMatchCount": 1,
  "linkedMatches": 0,
  "unlinkedMatches": 1,
  "linkedPeopleCount": 0
}
```

### 4.7 Search Endpoints

```http
GET /person/search?name=Worthington&limit=50
GET /census/search?surname=Worthington&year=1881
GET /match?minCm=100&side=paternal
```

---

## Level 5: Updates and Deletes

### 5.1 Update a Person

```http
PUT /person/1
```

```json
{
  "firstName": "George",
  "surname": "Worthington",
  "birthYear": 1851,
  "birthPlace": "Manchester, Lancashire"
}
```

### 5.2 Remove a Spouse Relationship

```http
DELETE /person/1/spouse/2
```

Removes the partnership record. Does not delete the person.

### 5.3 Delete a Person

```http
DELETE /person/99
```

**Response: 204 No Content**

---

## Endpoint Dependency Order

Use this as the test execution order.

| Order | Endpoint | Depends On |
|-------|----------|------------|
| 1 | POST /tree | - |
| 2 | POST /tree/{treeId}/person | tree exists |
| 3 | POST /person/{id}/spouse | person exists |
| 4 | POST /person/{id}/child | person exists |
| 5 | POST /person/{id}/parent | person exists |
| 6 | POST /dna-tester | - |
| 7 | POST /dna-match | 2+ testers exist |
| 8 | GET /person/{id} | person with relationships |
| 9 | GET /person/{id}/ancestors | multi-generation data |
| 10 | GET /person/{id}/descendants | multi-generation data |
| 11 | GET /tree/{slug}/hierarchy | tree + people |
| 12 | GET /stats | all data |
