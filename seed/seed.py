#!/usr/bin/env python3
"""Seed the family tree through the app's HTTP API.

Design (see README.md):
  - Each person is a pure JSON file = the literal POST body (paste-able into Bruno).
  - Relationships live in manifest.json using symbolic *refs* (e.g. "me", "dad"),
    never database ids. Refs must be unique and stable.
  - The database assigns the real ids; this runner resolves ref -> id at run time
    and feeds the resolved id into the URL of the next request.
  - The root person is verified by a birth_date lookup that must return exactly
    one row, proving a clean insert.

Assumes a FRESH (empty, Flyway-migrated) seed database. Re-running against a
non-empty DB will fail the "exactly one" check by design — rebuild and re-seed.

Config via env:
  SEED_BASE_URL  default http://localhost:3201
  SEED_PG_DSN    default postgresql://familytree:familytree@localhost:5432/familytree_seed
"""
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# The create endpoint parses birthDate with this pattern and SILENTLY nulls
# anything else. Keep payload dates in this format; the runner validates it.
API_DATE_FMT = "%d %m %Y"  # e.g. "30 09 1975"

BASE_URL = os.environ.get("SEED_BASE_URL", "http://localhost:3201").rstrip("/")
PG_DSN = os.environ.get(
    "SEED_PG_DSN", "postgresql://familytree:familytree@localhost:5432/familytree_seed"
)
# The API secures /api/** — authenticate via HTTP Basic (the in-memory chris/chris
# user, same as the integration test's withBasicAuth). Set SEED_USER="" to disable.
SEED_USER = os.environ.get("SEED_USER", "chris")
SEED_PASSWORD = os.environ.get("SEED_PASSWORD", "chris")
_AUTH_HEADER = (
    "Basic " + base64.b64encode(f"{SEED_USER}:{SEED_PASSWORD}".encode()).decode()
    if SEED_USER else None
)
HERE = Path(__file__).resolve().parent


def post(path, body):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if _AUTH_HEADER:
        headers["Authorization"] = _AUTH_HEADER
    req = urllib.request.Request(
        BASE_URL + path, data=data, headers=headers, method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"POST {path} failed: {e.code} {e.read().decode()[:300]}")


def to_iso(api_date):
    """Convert the API's 'dd MM yyyy' to ISO, failing loudly on a bad format."""
    try:
        return datetime.strptime(api_date, API_DATE_FMT).date().isoformat()
    except (TypeError, ValueError):
        sys.exit(
            f"birthDate {api_date!r} must match API format 'dd MM yyyy' "
            f"(e.g. '30 09 1975') — otherwise the API silently stores null"
        )


def ids_by_birth_date(api_date):
    """Query the DB directly: which person ids have this birth_date?"""
    q = f"select id from person where birth_date = '{to_iso(api_date)}' order by id"
    out = subprocess.run(["psql", PG_DSN, "-tAc", q], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"DB query failed: {out.stderr.strip()}")
    return [int(x) for x in out.stdout.split()]


def load_body(rel):
    return json.loads((HERE / rel).read_text())


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    ids = {}  # ref -> real DB id

    tree = post("/api/tree", manifest["tree"])
    tree_id = tree["id"]
    print(f"tree '{manifest['tree']['name']}' -> id {tree_id}")

    for step in manifest["steps"]:
        ref, kind, body = step["ref"], step["create"], load_body(step["body"])
        if ref in ids:
            sys.exit(f"duplicate ref '{ref}' — refs must be unique")

        if kind == "root":
            post(f"/api/tree/{tree_id}/person", body)
            if step.get("verifyByBirthDate"):
                dob = body.get("birthDate")
                matches = ids_by_birth_date(dob)
                if len(matches) != 1:
                    sys.exit(
                        f"expected exactly 1 person with birth_date {dob}, "
                        f"found {len(matches)}: {matches} — is the DB fresh?"
                    )
                ids[ref] = matches[0]
                print(f"  {ref}: created + verified by DOB {dob} -> id {ids[ref]}")
            else:
                sys.exit("root step needs verifyByBirthDate (no other id source)")

        elif kind in ("parent", "spouse", "child"):
            of_id = ids.get(step.get("of"))
            if of_id is None:
                sys.exit(f"step '{ref}': 'of' ref '{step.get('of')}' not created yet")
            if kind == "child":
                body = {**body, "parentGender": step.get("parentGender")}
            resp = post(f"/api/person/{of_id}/{kind}", body)
            ids[ref] = resp["id"]
            slot = f" gender={body.get('gender')}" if kind == "parent" else ""
            print(f"  {ref}: {kind} of {step['of']}({of_id}){slot} -> id {ids[ref]}")

        else:
            sys.exit(f"unknown create kind: {kind}")

    print("\nref -> id:")
    for k, v in ids.items():
        print(f"  {k:10} {v}")
    print(f"\nDone. Verify: curl {BASE_URL}/api/person/{ids['me']}")


if __name__ == "__main__":
    main()
