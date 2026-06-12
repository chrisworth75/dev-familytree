# Seed — family tree as code

Rebuilds the curated personal tree by POSTing it through the app's HTTP API.
No direct SQL inserts; the API is the only write path.

## The two kinds of file

- **`people/*.json`** — pure request bodies. Each file is *exactly* what you'd
  paste into Bruno/Postman as the POST body. No ids, no relationship info.
- **`manifest.json`** — the relationship layer. Lists the people in creation
  order and how they relate, using symbolic **refs** (not ids).

The database assigns ids; `seed.py` resolves `ref -> id` at run time. So nothing
ever hard-codes a misleading id.

### Refs

A ref is a stable, human-readable handle (`me`, `dad`, `UncleTony`, `WeirdTony`).
Genealogy is full of name collisions — refs are how *you* keep people straight.
Rules: **unique** and **stable** (don't rename — the manifest's `"of"` wiring
points at them).

### Relationship kinds (`create`)

| kind     | endpoint                          | notes |
|----------|-----------------------------------|-------|
| `root`   | `POST /api/tree/{treeId}/person`  | the first person; verified by birth_date |
| `parent` | `POST /api/person/{ofId}/parent`  | body `gender`: `M`=father, `F`=mother |
| `spouse` | `POST /api/person/{ofId}/spouse`  | |
| `child`  | `POST /api/person/{ofId}/child`   | manifest `parentGender` picks which slot `of` fills |

## Running

Assumes a **fresh, empty, Flyway-migrated** seed DB and an app instance pointing
at it (defaults: API on :3201, DB `familytree_seed` on :5432).

```sh
python3 seed.py
```

Override targets:

```sh
SEED_BASE_URL=http://localhost:3201 \
SEED_PG_DSN=postgresql://familytree:familytree@localhost:5432/familytree_seed \
python3 seed.py
```

The root's birth_date lookup must return **exactly one** row — that proves a
clean insert into an empty DB. Re-running against a non-empty DB fails by design;
rebuild the DB and re-seed.

## Editing for your family

`people/dad.json` and `people/mum.json` ship with PLACEHOLDER values. Replace the
names/dates with real details, then re-seed a fresh DB. Add more people by adding
a `people/*.json` body and a `manifest.json` step that references an existing ref.
