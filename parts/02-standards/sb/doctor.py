# -*- coding: utf-8 -*-
"""doctor.py - reads your second brain and reports what is no longer true.

It never changes a note. It only ever counts and reports.

Six things in here exist because they were got wrong first, on a real vault of nearly five
thousand notes. Each is marked WHY so you can see the reasoning rather than trust it:

  1. A file may start with an invisible marker before its first line. Checking for the first
     line without allowing for that reported 290 perfectly good notes as broken.
  2. A link is read up to the first ']]', not "up to the first ]". Hundreds of notes have a
     square bracket in the filename, and the naive reading called every link to them broken.
  3. Links to things that live outside your notes on purpose are not broken links.
  4. A link written with a stray '.md' on the end, where the note plainly exists, is counted
     separately from a link to something that was never written.
  5. A link that names a folder as well as a note is not ambiguous, even if the note's name is
     used twice elsewhere.
  6. Where the same subject deliberately has two notes that reference each other, that is a
     pattern, not a fault.

Every one of those, uncorrected, makes the report say a healthy system is broken. A report that
cries wolf gets ignored, and then nothing is being checked at all.
"""

import collections
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

HERE = Path(__file__).resolve().parent
VAULT = HERE.parent
SCHEMA_PATH = HERE / "_schema" / "note-types.json"
EXPECT_PATH = HERE / "_schema" / "expectations.json"
REPORT_DIR = HERE / "reports"   # beside the engine, not in a room Layer 1 never made

# WHY 2: non-greedy to the first ']]'. A pattern that excluded ']' from the middle of a link is
# blind to every note whose filename contains a square bracket.
WIKILINK = re.compile(r"\[\[(.+?)\]\]")
FM_KEY = re.compile(r"^([A-Za-z0-9_-]+):", re.M)
FM_TYPE = re.compile(r"^type:\s*(.+)$", re.M)


def link_target(raw):
    """What a link actually resolves to, once any alias, heading and folder are removed."""
    t = raw.split("|")[0].split("#")[0].strip()
    return re.split(r"[\\/]", t)[-1].lower()


def read_text(path):
    """WHY 1: strip the invisible byte-order marker some editors put at the start of a file,
    otherwise a note that begins '---' looks as though it does not."""
    try:
        s = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        s = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return s.lstrip("﻿")


def atomic_write(path, text):
    """Write via a temporary file and swap it in, so a failure halfway cannot leave a half file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


class Scan(object):
    def __init__(self, schema):
        self.schema = schema
        excl = set(schema.get("scope", {}).get("exclude_path_parts", []))
        excl_files = set(schema.get("scope", {}).get("exclude_files", []))
        self.notes = collections.defaultdict(list)
        self.files = []
        self.no_frontmatter = []
        self.missing_type = []
        self.missing_date = []
        self.types = collections.Counter()
        self.type_in_folder = collections.Counter()
        self.links_total = 0
        self.link_misses = collections.Counter()
        self.link_targets = collections.Counter()

        for p in VAULT.rglob("*.md"):
            if set(p.parts) & excl or p.name in excl_files:
                continue
            self.files.append(p)
            self.notes[p.stem.lower()].append(p)

        for p in self.files:
            s = read_text(p)
            end = s.find("\n---", 3) if s.startswith("---") else -1
            if not s.startswith("---") or end == -1:
                self.no_frontmatter.append(p)
            else:
                fm = s[3:end]
                keys = set(m.group(1) for m in FM_KEY.finditer(fm))
                if "type" not in keys:
                    self.missing_type.append(p)
                if "date" not in keys:
                    self.missing_date.append(p)
                m = FM_TYPE.search(fm)
                if m:
                    t = m.group(1).strip().strip("\"'")
                    self.types[t] += 1
                    top = p.relative_to(VAULT).parts[0]
                    self.type_in_folder[(t, top)] += 1
            for m in WIKILINK.finditer(s):
                target = link_target(m.group(1))
                if not target:
                    continue
                self.links_total += 1
                self.link_targets[target] += 1
                if target not in self.notes:
                    self.link_misses[target] += 1

        # WHY 3: things that live outside your notes on purpose. A link to one is correct.
        self.external = set()
        for d in schema.get("scope", {}).get("external_name_sources", []):
            p = Path(os.path.expanduser(d))
            if p.exists():
                self.external |= set(q.stem.lower() for q in p.rglob("*.md"))

    def classify_links(self):
        typo, real, external = {}, {}, {}
        for target, n in self.link_misses.items():
            base = target[:-3] if target.endswith(".md") else target
            if target in self.external or base in self.external:
                external[target] = n                       # WHY 3
            elif target.endswith(".md") and base in self.notes:
                typo[target] = n                           # WHY 4
            else:
                real[target] = n
        hubs = dict((t, n) for t, n in real.items() if n >= 3)
        return {
            "total": self.links_total,
            "external_refs": sum(external.values()),
            "typo_refs": sum(typo.values()),
            "typo_targets": typo,
            "real_refs": sum(real.values()),
            "real_targets": len(real),
            "hub_refs": sum(hubs.values()),
            "hub_targets": hubs,
            "single_refs": sum(n for n in real.values() if n == 1),
        }

    def classify_names(self):
        scaffold_stems = set(self.schema.get("naming", {}).get("scaffold_stems", []))
        coll = dict((k, v) for k, v in self.notes.items() if len(v) > 1)
        scaffold = dict((k, v) for k, v in coll.items() if k in scaffold_stems)
        content = dict((k, v) for k, v in coll.items() if k not in scaffold_stems)

        pairs, orphaned = [], 0
        for stem, paths in content.items():
            if len(paths) != 2:
                continue
            a, b = sorted(paths, key=lambda p: p.stat().st_size, reverse=True)
            ta, tb = read_text(a), read_text(b)
            # WHY 6: a deliberate pair references itself across. Only a pair where neither note
            # knows the other exists is a duplicate.
            ra = a.relative_to(VAULT).as_posix()[:-3].lower()
            rb = b.relative_to(VAULT).as_posix()[:-3].lower()
            paired = ra in tb.lower().replace("\\", "/") or rb in ta.lower().replace("\\", "/")
            tomb = bool(re.search(r"^type:\s*redirect", tb, re.M))
            if not (paired or tomb):
                orphaned += 1
            pairs.append({"stem": stem, "links": self.link_targets.get(stem, 0),
                          "big": str(a.relative_to(VAULT)), "big_bytes": a.stat().st_size,
                          "small": str(b.relative_to(VAULT)), "small_bytes": b.stat().st_size,
                          "deliberate": paired or tomb})

        # WHY 5: a link is only ambiguous when it is BARE. One that names the folder resolves.
        bare_recoverable = bare_ambiguous = 0
        for p in self.files:
            for m in WIKILINK.finditer(read_text(p)):
                raw = m.group(1).split("|")[0].split("#")[0].strip()
                leaf = link_target(m.group(1))
                if leaf not in coll or re.search(r"[\\/]", raw):
                    continue
                if len([c for c in coll[leaf] if c.parent == p.parent]) == 1:
                    bare_recoverable += 1
                else:
                    bare_ambiguous += 1

        return {"scaffold": scaffold, "content": content, "pairs": pairs,
                "orphaned": orphaned, "bare_recoverable": bare_recoverable,
                "bare_ambiguous": bare_ambiguous}


def tracked_secrets():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=str(VAULT), capture_output=True,
                             text=True, creationflags=NO_WINDOW, timeout=90)
    except Exception:
        return []
    pat = re.compile(r"\.(key|pem|crt|cer|p12|pfx|env)$", re.I)
    return [ln for ln in out.stdout.splitlines() if pat.search(ln)]


def build_checks(scan, schema):
    canon = set(schema.get("canonical_types", {}))
    aliases = dict((k, v) for k, v in schema.get("aliases", {}).items() if not k.startswith("$"))
    domain = dict((k, set(v)) for k, v in schema.get("domain_types", {}).items()
                  if not k.startswith("$"))
    links = scan.classify_links()
    names = scan.classify_names()

    unknown = collections.Counter()
    for (t, f), n in scan.type_in_folder.items():
        if t not in canon and t not in aliases and t not in domain.get(f, set()):
            unknown[t] += n

    return [
        dict(id="empty-notes", did=len([p for p in scan.files if p.stat().st_size == 0]),
             unit="notes with nothing in them",
             examples=[str(p.relative_to(VAULT)) for p in scan.files if p.stat().st_size == 0][:6]),
        dict(id="frontmatter-present", did=len(scan.no_frontmatter),
             unit="notes that do not say what they are",
             examples=[str(p.relative_to(VAULT)) for p in scan.no_frontmatter[:6]]),
        dict(id="type-declared", did=len(scan.missing_type), unit="notes with no kind", examples=[]),
        dict(id="date-declared", did=len(scan.missing_date), unit="notes with no date", examples=[]),
        dict(id="type-known", did=len(unknown), unit="kinds of note outside your list",
             examples=["%s (%d)" % (t, n) for t, n in unknown.most_common(6)]),
        dict(id="names-used-twice", did=len(names["content"]),
             unit="subjects living under one name",
             examples=["%s (%d links)" % (p["stem"], p["links"]) for p in names["pairs"][:6]]),
        dict(id="duplicate-pairs", did=names["orphaned"],
             unit="same-name pairs where neither note knows the other exists", examples=[]),
        dict(id="bare-ambiguous-links", did=names["bare_ambiguous"],
             unit="links that could mean either of two notes", examples=[]),
        dict(id="links-resolve", did=links["real_refs"],
             unit="links pointing at a note that was never written", examples=[]),
        dict(id="link-typos", did=links["typo_refs"], unit="links with a stray .md on the end",
             examples=["%s (%d)" % (t, n) for t, n in
                       sorted(links["typo_targets"].items(), key=lambda x: -x[1])[:6]]),
        dict(id="no-secrets-tracked", did=len(tracked_secrets()),
             unit="passwords or keys saved into your history", examples=tracked_secrets()[:4]),
    ], links, names


def apply_expectations(checks, expect):
    ceilings = expect.get("ceilings", {})
    for c in checks:
        ceil = ceilings.get(c["id"])
        c["ceiling"] = ceil
        if ceil is None:
            c["status"] = "new"
        elif c["did"] > ceil:
            c["status"] = "WORSE"
        elif c["did"] < ceil:
            c["status"] = "better"
        else:
            c["status"] = "ok"
    return checks


def report(checks, scan, links, expect):
    L = ["", "  YOUR SECOND BRAIN - CHECK", "  %s" % VAULT,
         "  %d notes, %d links" % (len(scan.files), links["total"]), ""]
    if not expect:
        L.append("  First run. These numbers become the ceiling: from now on each one may fall")
        L.append("  and may not rise. Nothing has to be fixed today.")
        L.append("")
    w = max(len(c["id"]) for c in checks)
    order = {"WORSE": 0, "new": 1, "better": 2, "ok": 3}
    for c in sorted(checks, key=lambda x: (order[x["status"]], -x["did"])):
        ceil = "-" if c["ceiling"] is None else str(c["ceiling"])
        L.append("  %-7s %-*s %6d   was %-6s  %s"
                 % (c["status"], w, c["id"], c["did"], ceil, c["unit"]))
        if c["status"] in ("WORSE", "new") and c["examples"]:
            for e in c["examples"][:4]:
                L.append("              %s" % e)
    worse = [c for c in checks if c["status"] == "WORSE"]
    L.append("")
    L.append("  %s" % ("SOMETHING GOT WORSE - the lines marked WORSE are the only ones to look at."
                       if worse else "Nothing got worse."))
    L.append("")
    return "\n".join(L)


def main(argv):
    schema = load_json(SCHEMA_PATH)
    if not schema:
        print("No rules file at %s - is this layer installed?" % SCHEMA_PATH)
        return 2
    expect = load_json(EXPECT_PATH)
    scan = Scan(schema)
    checks, links, names = build_checks(scan, schema)
    checks = apply_expectations(checks, expect)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write(REPORT_DIR / "latest.json", json.dumps(
        {"run": date.today().isoformat(), "notes": len(scan.files), "links": links["total"],
         "checks": [dict((k, v) for k, v in c.items() if k != "examples") for c in checks]},
        indent=2))

    if "--set-ceiling" in argv or not expect:
        old = expect.get("ceilings", {})
        new = {}
        for c in checks:
            prev = old.get(c["id"])
            new[c["id"]] = c["did"] if prev is None or c["did"] < prev else prev
        atomic_write(EXPECT_PATH, json.dumps(
            {"$comment": "What your system looked like when measured. A ceiling may fall, never "
                         "rise. Yours to edit; the check never raises one on its own.",
             "first_run": expect.get("first_run", date.today().isoformat()),
             "updated": date.today().isoformat(), "ceilings": new}, indent=2))
        checks = apply_expectations(checks, load_json(EXPECT_PATH))

    print(report(checks, scan, links, expect))
    return 1 if any(c["status"] == "WORSE" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
