#!/usr/bin/env python3
"""
Ancestry DNA Match Scraper - Event Emission Mode

Scrapes DNA matches from ancestry.co.uk and emits one JSON event per newly
discovered match to a session-scoped JSONL file. Does NOT write to SQLite.

Sessions are resumable. State lives under ~/.ancestry-scraper/sessions/.

Usage:
    python ancestry_batch.py             # start or resume
    python ancestry_batch.py --new       # force a new session
    python ancestry_batch.py --status    # show state, don't scrape
    python ancestry_batch.py --headless  # run browser headless
"""

import argparse
import json
import os
import re
import signal
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


SESSIONS_ROOT = Path.home() / ".ancestry-scraper" / "sessions"
ANCESTRY_BASE_URL = "https://www.ancestry.co.uk"
SOURCE = "ancestry.co.uk"
SCHEMA_VERSION = 1
EVENT_TYPE = "MatchDiscovered"

# After this many consecutive pages with zero new matches, treat the scrape as done.
MAX_CONSECUTIVE_EMPTY_PAGES = 10
# Hard safety stop in case pagination never terminates.
MAX_PAGES = 1500


# --------------------------------------------------------------------------- #
# SessionStore - owns checkpoint.json + events.jsonl for a single session.
# Pure I/O, no Playwright. Unit-testable in isolation.
# --------------------------------------------------------------------------- #


class SessionError(Exception):
    pass


class SessionStore:
    def __init__(self, session_dir):
        self.session_dir = Path(session_dir)
        self.checkpoint_path = self.session_dir / "checkpoint.json"
        self.events_path = self.session_dir / "events.jsonl"
        self.state = None
        self._seen_guids_set = None
        self._events_fh = None

    # --- factories --------------------------------------------------------- #

    @classmethod
    def new(cls, sessions_root=SESSIONS_ROOT, now=None):
        """Mint a new session, create dir + initial checkpoint."""
        now = now or datetime.now().astimezone()
        session_id = f"{now.date().isoformat()}-{uuid.uuid4().hex[:6]}"
        session_dir = Path(sessions_root) / session_id
        session_dir.mkdir(parents=True, exist_ok=False)
        store = cls(session_dir)
        store.state = {
            "session_id": session_id,
            "started_at": now.isoformat(timespec="seconds"),
            "test_guid": None,
            "total_pages": None,
            "last_page_completed": 0,
            "seen_guids": [],
            "status": "in_progress",
        }
        store._seen_guids_set = set()
        store._write_checkpoint()
        return store

    @classmethod
    def load(cls, session_dir):
        """Load an existing session from disk."""
        store = cls(session_dir)
        if not store.checkpoint_path.exists():
            raise SessionError(f"No checkpoint at {store.checkpoint_path}")
        store.state = json.loads(store.checkpoint_path.read_text())
        store._seen_guids_set = set(store.state.get("seen_guids", []))
        return store

    @classmethod
    def find_in_progress(cls, sessions_root=SESSIONS_ROOT):
        """Return paths of all session dirs whose checkpoint says in_progress."""
        root = Path(sessions_root)
        if not root.exists():
            return []
        found = []
        for child in sorted(root.iterdir()):
            cp = child / "checkpoint.json"
            if not cp.exists():
                continue
            try:
                state = json.loads(cp.read_text())
            except json.JSONDecodeError:
                continue
            if state.get("status") == "in_progress":
                found.append(child)
        return found

    # --- accessors --------------------------------------------------------- #

    @property
    def session_id(self):
        return self.state["session_id"]

    @property
    def last_page_completed(self):
        return self.state["last_page_completed"]

    @property
    def status(self):
        return self.state["status"]

    @property
    def test_guid(self):
        return self.state.get("test_guid")

    def has_seen(self, guid):
        return guid in self._seen_guids_set

    def event_count(self):
        if not self.events_path.exists():
            return 0
        with self.events_path.open("rb") as f:
            return sum(1 for _ in f)

    # --- mutators ---------------------------------------------------------- #

    def set_test_guid(self, guid):
        if self.state.get("test_guid") != guid:
            self.state["test_guid"] = guid
            self._write_checkpoint()

    def append_event(self, event):
        """Append one event to events.jsonl with flush + fsync."""
        if self._events_fh is None:
            self._events_fh = self.events_path.open("a", encoding="utf-8")
        self._events_fh.write(json.dumps(event, separators=(",", ":")) + "\n")
        self._events_fh.flush()
        os.fsync(self._events_fh.fileno())
        guid = event.get("match", {}).get("ancestry_id")
        if guid:
            self._seen_guids_set.add(guid)

    def complete_page(self, page_num, new_guids):
        """After a page is fully processed, atomically update checkpoint."""
        self.state["last_page_completed"] = page_num
        for g in new_guids:
            if g and g not in self._seen_guids_set:
                self.state["seen_guids"].append(g)
                self._seen_guids_set.add(g)
        # In case append_event added GUIDs but they were not in new_guids
        # (shouldn't happen, but be defensive).
        existing = set(self.state["seen_guids"])
        for g in self._seen_guids_set:
            if g not in existing:
                self.state["seen_guids"].append(g)
        self._write_checkpoint()

    def mark_complete(self):
        self.state["status"] = "complete"
        self.state["completed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        self._write_checkpoint()

    def mark_abandoned(self):
        self.state["status"] = "abandoned"
        self.state["abandoned_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        self._write_checkpoint()

    def close(self):
        if self._events_fh is not None:
            try:
                self._events_fh.flush()
                os.fsync(self._events_fh.fileno())
            finally:
                self._events_fh.close()
                self._events_fh = None

    # --- internals --------------------------------------------------------- #

    def _write_checkpoint(self):
        """Atomic write via tmp file + os.replace."""
        tmp = self.checkpoint_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, indent=2))
        os.replace(tmp, self.checkpoint_path)


# --------------------------------------------------------------------------- #
# Pure helpers - easy to unit test.
# --------------------------------------------------------------------------- #


_SIDE_MAP = {
    "both sides": "both",
    "paternal side": "paternal",
    "maternal side": "maternal",
    "mother's side": "maternal",
    "father's side": "paternal",
}


def normalize_side(text):
    """Map browser-rendered side text to the constrained enum."""
    if not text:
        return "unknown"
    t = text.strip().lower()
    # Trailing exclamation/icon glyphs sometimes appear; strip non-alpha tail.
    for key, value in _SIDE_MAP.items():
        if key in t:
            return value
    return "unknown"


def build_event(raw_match, session_id, now=None):
    """Construct a MatchDiscovered event from one extracted match dict."""
    now = now or datetime.now().astimezone()
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": EVENT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "discovered_at": now.isoformat(timespec="seconds"),
        "session_id": session_id,
        "source": SOURCE,
        "match": {
            "ancestry_id": raw_match.get("guid"),
            "name": raw_match.get("name"),
            "shared_cm": raw_match.get("sharedCm"),
            "predicted_relationship": raw_match.get("relationship"),
            "match_side": normalize_side(raw_match.get("matchSide")),
            "has_tree": bool(raw_match.get("hasTree", False)),
            "tree_size": raw_match.get("treeSize"),
            "linked_tree_id": raw_match.get("linkedTreeId"),
        },
    }


# --------------------------------------------------------------------------- #
# Playwright scrape.
#
# Deliberately not imported from ancestry_import.py so the two scripts stay
# decoupled - the next Ancestry UI change can be patched in one without
# disturbing the other. The JS extraction below is a copy of the version
# in ancestry_import.py at the time this was written.
# --------------------------------------------------------------------------- #


EXTRACT_MATCHES_JS = r"""
() => {
    const matches = [];
    const entries = document.querySelectorAll('.matchEntry');
    entries.forEach((entry) => {
        try {
            const nameLink = entry.querySelector('a.matchInfoName[aria-label]');
            let matchGuid = null;
            let name = null;
            if (nameLink) {
                name = nameLink.textContent.trim();
                const guidMatch = nameLink.href.match(/with\/([A-F0-9-]+)/i);
                if (guidMatch) matchGuid = guidMatch[1].toUpperCase();
            }
            if (!matchGuid) return;

            let sharedCm = null;
            const cmEl = entry.querySelector('[data-testid="sharedDNA"]');
            const cmText = cmEl ? cmEl.textContent : entry.textContent;
            const cmMatch = cmText.match(/([\d,]+)\s*cM/i);
            if (cmMatch) sharedCm = parseFloat(cmMatch[1].replace(/,/g, ''));

            const relEl = entry.querySelector('.relationshipLabel');
            const relationship = relEl ? relEl.textContent.trim() : null;

            const sideEl = entry.querySelector('.familySideInfo');
            const matchSide = sideEl ? sideEl.textContent.trim() : null;

            let hasTree = false;
            let treeSize = null;
            let linkedTreeId = null;
            const treeInfo = entry.querySelector('.matchTreeInfo');
            if (treeInfo) {
                const treeLink = treeInfo.querySelector('a[href*="family-tree"]');
                if (treeLink) {
                    hasTree = true;
                    const sizeMatch = treeLink.textContent.match(/(\d[\d,]*)\s*pe/i);
                    if (sizeMatch) treeSize = parseInt(sizeMatch[1].replace(/,/g, ''));
                    const treeIdMatch = treeLink.href.match(/tree\/(\d+)/);
                    if (treeIdMatch) linkedTreeId = treeIdMatch[1];
                } else if (
                    treeInfo.textContent.includes('Unlinked tree') ||
                    treeInfo.textContent.includes('Public linked tree') ||
                    treeInfo.textContent.includes('Private linked tree')
                ) {
                    hasTree = true;
                    const sizeMatch = treeInfo.textContent.match(/(\d[\d,]*)\s*pe/i);
                    if (sizeMatch) treeSize = parseInt(sizeMatch[1].replace(/,/g, ''));
                }
            }

            matches.push({
                guid: matchGuid,
                name: name,
                sharedCm: sharedCm,
                relationship: relationship,
                matchSide: matchSide,
                hasTree: hasTree,
                treeSize: treeSize,
                linkedTreeId: linkedTreeId,
            });
        } catch (e) {}
    });
    return matches;
}
"""


def _get_chrome_cookies():
    import browser_cookie3

    cookies = []
    for domain in (".ancestry.co.uk", ".ancestry.com"):
        try:
            for c in browser_cookie3.chrome(domain_name=domain):
                cookies.append(
                    {
                        "name": c.name,
                        "value": c.value,
                        "domain": c.domain,
                        "path": c.path,
                        "secure": bool(c.secure),
                    }
                )
        except Exception as exc:
            print(f"  (skipping {domain}: {exc})", flush=True)
    return cookies


def _resolve_test_guid(page):
    page.goto(f"{ANCESTRY_BASE_URL}/dna", wait_until="domcontentloaded", timeout=60000)
    time.sleep(2)
    match = re.search(
        r"/([A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12})",
        page.url,
        re.IGNORECASE,
    )
    if not match:
        raise SessionError(
            "Could not detect DNA test GUID from /dna redirect. "
            f"Landed on: {page.url}"
        )
    return match.group(1).upper()


def scrape(store, headless=False, max_pages=MAX_PAGES):
    """Run the resumable scrape into the given SessionStore.

    Ctrl-C handling: Playwright's sync API replaces Python's default SIGINT
    handler so KeyboardInterrupt won't propagate cleanly. We install our own
    handler that sets a flag, then check it after every page; the loop breaks
    out by raising KeyboardInterrupt at a known-safe point.
    """
    from playwright.sync_api import sync_playwright

    cookies = _get_chrome_cookies()
    print(f"  Found {len(cookies)} Ancestry cookies", flush=True)
    if not cookies:
        raise SessionError("No Ancestry cookies in Chrome. Log in via Chrome, then close Chrome.")

    stop_flag = {"set": False}

    def _on_sigint(signum, frame):
        if not stop_flag["set"]:
            stop_flag["set"] = True
            print(
                "\n[SIGINT received - will stop after current page completes]",
                flush=True,
            )
        else:
            # Second Ctrl-C - force exit without further cleanup.
            print("\n[Second SIGINT - exiting immediately]", flush=True)
            os._exit(130)

    with sync_playwright() as pw:
        # Install our handler AFTER sync_playwright enters so it wins over
        # Playwright's internal handler.
        previous_handler = signal.signal(signal.SIGINT, _on_sigint)

        browser = pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        context.add_cookies(cookies)
        page = context.new_page()

        try:
            if not store.test_guid:
                print("Resolving test GUID...", flush=True)
                store.set_test_guid(_resolve_test_guid(page))
            test_guid = store.test_guid
            print(f"Test GUID: {test_guid}", flush=True)

            base_url = (
                f"{ANCESTRY_BASE_URL}/discoveryui-matches/list/{test_guid}"
                "?sharedDna=allMatches"
            )

            # Warm-up navigation - establishes the matches UI before paginating.
            print("Warming match-list page...", flush=True)
            page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_selector(".matchEntry", timeout=30000)
            except Exception:
                print("  Warning: .matchEntry never appeared on warm-up", flush=True)
            time.sleep(3)

            start_page = store.last_page_completed + 1
            if start_page > 1:
                print(
                    f"Resuming session {store.session_id} from page {start_page} "
                    f"(seen so far: {len(store._seen_guids_set)} matches, "
                    f"{store.event_count()} events on disk)",
                    flush=True,
                )

            consecutive_empty = 0
            page_num = start_page

            while consecutive_empty < MAX_CONSECUTIVE_EMPTY_PAGES and page_num <= max_pages:
                page_url = f"{base_url}&currentPage={page_num}"

                loaded = False
                for attempt in range(3):
                    try:
                        page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
                        time.sleep(3)
                        loaded = True
                        break
                    except Exception as exc:
                        print(f"  Page {page_num}: retry {attempt + 1}/3 after error: {exc}", flush=True)
                        time.sleep(5)
                if not loaded:
                    print(f"  Page {page_num}: failed after 3 attempts, skipping", flush=True)
                    # Don't mark this page complete - resume will retry it.
                    page_num += 1
                    continue

                raw_matches = page.evaluate(EXTRACT_MATCHES_JS)
                new_guids = []
                events_this_page = 0
                for m in raw_matches:
                    guid = m.get("guid")
                    if not guid or store.has_seen(guid):
                        continue
                    event = build_event(m, store.session_id)
                    store.append_event(event)
                    new_guids.append(guid)
                    events_this_page += 1

                store.complete_page(page_num, new_guids)

                if events_this_page == 0:
                    consecutive_empty += 1
                else:
                    consecutive_empty = 0

                if page_num % 10 == 0 or page_num <= 5:
                    total = store.event_count()
                    print(
                        f"  Page {page_num}: +{events_this_page} new, "
                        f"{total} events total this session",
                        flush=True,
                    )

                page_num += 1

                if stop_flag["set"]:
                    raise KeyboardInterrupt

            if consecutive_empty >= MAX_CONSECUTIVE_EMPTY_PAGES:
                print(
                    f"\nReached {MAX_CONSECUTIVE_EMPTY_PAGES} consecutive empty pages — "
                    f"treating scrape as complete.",
                    flush=True,
                )
            else:
                print(f"\nReached safety max of {max_pages} pages.", flush=True)

            store.mark_complete()

        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
            signal.signal(signal.SIGINT, previous_handler)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _print_status(store):
    print(f"Session:           {store.session_id}")
    print(f"Status:            {store.status}")
    print(f"Started:           {store.state.get('started_at')}")
    if store.state.get("completed_at"):
        print(f"Completed:         {store.state['completed_at']}")
    if store.state.get("abandoned_at"):
        print(f"Abandoned:         {store.state['abandoned_at']}")
    print(f"Test GUID:         {store.test_guid}")
    print(f"Last page done:    {store.last_page_completed}")
    print(f"Seen GUIDs:        {len(store._seen_guids_set)}")
    print(f"Events on disk:    {store.event_count()}")
    print(f"Folder:            {store.session_dir}")


def _confirm(prompt):
    try:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ancestry DNA match scraper (event mode)")
    parser.add_argument("--new", action="store_true", help="Force a new session")
    parser.add_argument("--status", action="store_true", help="Show current session state and exit")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    args = parser.parse_args(argv)

    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)
    in_progress = SessionStore.find_in_progress()

    # --status mode: read-only inspection.
    if args.status:
        if not in_progress:
            sessions = sorted([p for p in SESSIONS_ROOT.iterdir() if p.is_dir()])
            if not sessions:
                print("No sessions yet.")
                return 0
            store = SessionStore.load(sessions[-1])
            print("(no in-progress session; showing most recent)\n")
        elif len(in_progress) > 1:
            print(f"ERROR: {len(in_progress)} in-progress sessions found:", file=sys.stderr)
            for p in in_progress:
                print(f"  {p}", file=sys.stderr)
            print("Resolve manually (delete or mark abandoned) before continuing.", file=sys.stderr)
            return 2
        else:
            store = SessionStore.load(in_progress[0])
        _print_status(store)
        return 0

    # --new mode: optionally abandon existing.
    if args.new:
        if in_progress:
            if len(in_progress) > 1:
                print(f"ERROR: {len(in_progress)} in-progress sessions found; resolve manually first.", file=sys.stderr)
                return 2
            existing = SessionStore.load(in_progress[0])
            print(f"An in-progress session already exists: {existing.session_id}")
            print(f"  Last page done: {existing.last_page_completed}, events: {existing.event_count()}")
            if not _confirm("Abandon it and start a new session?"):
                print("Aborted. No changes made.")
                return 1
            existing.mark_abandoned()
            print(f"Marked {existing.session_id} as abandoned.")
        store = SessionStore.new()
        print(f"Started new session: {store.session_id}")
    else:
        if not in_progress:
            store = SessionStore.new()
            print(f"No in-progress session found. Started new: {store.session_id}")
        elif len(in_progress) > 1:
            print(f"ERROR: {len(in_progress)} in-progress sessions found:", file=sys.stderr)
            for p in in_progress:
                print(f"  {p}", file=sys.stderr)
            print(
                "Pick one to keep with --status, mark the others abandoned, or use --new "
                "to start fresh.",
                file=sys.stderr,
            )
            return 2
        else:
            store = SessionStore.load(in_progress[0])
            print(f"Resuming session {store.session_id} (last page done: {store.last_page_completed})")

    # Run the scrape, handling Ctrl-C cleanly.
    started = time.time()
    interrupted = False
    try:
        scrape(store, headless=args.headless)
    except KeyboardInterrupt:
        interrupted = True
        print("\nInterrupted by user. Flushing checkpoint and events file...", flush=True)
    finally:
        store.close()

    duration = time.time() - started
    print()
    if interrupted:
        print(f"Session paused: {store.session_id}")
        print(f"  Last page done: {store.last_page_completed}")
        print(f"  Events written: {store.event_count()}")
        print(f"  Folder:         {store.session_dir}")
        print("Run `python ancestry_batch.py` again to resume.")
        return 130
    else:
        print(f"Session complete: {store.session_id}")
        print(f"  Total events:   {store.event_count()}")
        print(f"  Duration:       {duration:.1f}s")
        print(f"  Folder:         {store.session_dir}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
