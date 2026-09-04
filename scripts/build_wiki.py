#!/usr/bin/env python3
"""Build the GitHub wiki tree from repository sources.

The wiki is generated, never hand-edited. Hand-written pages live in `wiki/`
and are copied verbatim; the gotcha pages are split out of `docs/gotchas.md`
so the catalogue has exactly one source of truth.

    python3 scripts/build_wiki.py            # build into build/wiki
    python3 scripts/build_wiki.py --check    # fail if the build is stale

`--check` is what CI runs. A wiki that silently diverges from the repository
is the documentation equivalent of a scanner that has stopped matching: it
still looks like an active source, and it is no longer one.
"""

from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOTCHAS = ROOT / "docs" / "gotchas.md"
WIKI_SRC = ROOT / "wiki"
BUILD = ROOT / "build" / "wiki"

# Grouping is editorial and lives here, not in gotchas.md, so that the
# catalogue file stays a flat numbered list that is cheap to append to.
# Every number in the source must appear in exactly one group; the build
# fails loudly if that stops being true.
GROUPS: list[tuple[str, str, list[int]]] = [
    (
        "Reachability and reporting",
        "Failures where a host disappears from the run and its absence reads as health.",
        [1, 2, 3],
    ),
    (
        "Variable precedence",
        "Inventory quietly outranking the play. No warning is emitted in any of these.",
        [4, 5, 14],
    ),
    (
        "Evaluation logic",
        "Checks that return PASS without having evaluated anything.",
        [6, 8, 16],
    ),
    (
        "Pattern matching",
        "Regexes that match what they should not, and fail to match what they should.",
        [7],
    ),
    (
        "Structure and plugin discovery",
        "Valid YAML in the wrong place, and plugins Ansible never looks for.",
        [15, 18],
    ),
    (
        "Setup and CI ordering",
        "Steps that each report success while the sequence as a whole is wrong.",
        [17, 11, 12],
    ),
    (
        "Secrets and environment",
        "Places where a secret, or the explanation of a failure, ends up somewhere unintended.",
        [9, 10, 13],
    ),
]

HEADING = re.compile(r"^##\s+(\d+)\.\s+(.*)$")


def slugify(text: str) -> str:
    """Turn a gotcha title into a wiki page name.

    GitHub wiki page names map to filenames with spaces as hyphens, so the
    slug is the filename. Backticks and punctuation from code spans in the
    title have to go, or the URL becomes unquotable.
    """
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = text.replace("$", "").replace("~", "")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-").lower()


def parse_gotchas(path: Path) -> list[dict]:
    """Split the catalogue into records. Sections are `## N. Title`."""
    if not path.exists():
        sys.exit(f"error: {path} not found")

    lines = path.read_text(encoding="utf-8").splitlines()
    entries: list[dict] = []
    current: dict | None = None

    for line in lines:
        m = HEADING.match(line)
        if m:
            if current:
                entries.append(current)
            current = {
                "number": int(m.group(1)),
                "title_md": m.group(2).strip(),
                "body": [],
            }
            continue
        if current is not None:
            current["body"].append(line)

    if current:
        entries.append(current)

    if not entries:
        sys.exit("error: no `## N. Title` sections found in docs/gotchas.md")

    for e in entries:
        # Trim the trailing `---` separator and surrounding blank lines.
        body = e["body"]
        while body and (body[-1].strip() == "" or body[-1].strip() == "---"):
            body.pop()
        e["body"] = "\n".join(body).strip()
        e["title_plain"] = re.sub(r"`", "", e["title_md"])
        e["page"] = f"Gotcha-{e['number']:02d}-{slugify(e['title_md'])}"

    return sorted(entries, key=lambda e: e["number"])


def check_groups(entries: list[dict]) -> None:
    grouped = [n for _, _, nums in GROUPS for n in nums]
    found = {e["number"] for e in entries}
    missing = found - set(grouped)
    unknown = set(grouped) - found
    dupes = {n for n in grouped if grouped.count(n) > 1}
    problems = []
    if missing:
        problems.append(f"gotchas not assigned to a group: {sorted(missing)}")
    if unknown:
        problems.append(f"groups reference nonexistent gotchas: {sorted(unknown)}")
    if dupes:
        problems.append(f"gotchas in more than one group: {sorted(dupes)}")
    if problems:
        sys.exit("error: " + "; ".join(problems) + "\n  fix GROUPS in scripts/build_wiki.py")


def render_gotcha_page(e: dict, entries: list[dict]) -> str:
    by_number = {x["number"]: x for x in entries}
    body = e["body"]

    # Cross-references in the prose are written as "gotcha N" / "entry N".
    # Turn them into wiki links so a reader who lands on one page can walk
    # the chain without going back to the index.
    def link_ref(m: re.Match) -> str:
        n = int(m.group(2))
        target = by_number.get(n)
        if not target:
            return m.group(0)
        return f"[{m.group(1)} {n}]({target['page']})"

    body = re.sub(r"\b(gotcha|entry|entries)\s+(\d+)\b", link_ref, body, flags=re.I)

    group_name = next((g for g, _, nums in GROUPS if e["number"] in nums), "")
    prev_e = by_number.get(e["number"] - 1)
    next_e = by_number.get(e["number"] + 1)

    nav = []
    if prev_e:
        nav.append(f"← [{prev_e['number']:02d}. {prev_e['title_plain']}]({prev_e['page']})")
    nav.append("[All gotchas](Gotchas)")
    if next_e:
        nav.append(f"[{next_e['number']:02d}. {next_e['title_plain']}]({next_e['page']}) →")

    return "\n".join(
        [
            f"# {e['number']:02d}. {e['title_md']}",
            "",
            f"> **Category:** {group_name} · "
            f"Source: [`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)",
            "",
            body,
            "",
            "---",
            "",
            " · ".join(nav),
            "",
        ]
    )


def render_index(entries: list[dict]) -> str:
    by_number = {e["number"]: e for e in entries}
    out = [
        "# Gotchas",
        "",
        f"**{len(entries)} failure modes that produce a passing result.**",
        "",
        "Ordinary errors are not interesting; they announce themselves. Everything",
        "catalogued here ran, exited zero, and reported success while being wrong.",
        "",
        "Each entry is its own page so it can be linked from a code review, a ticket,",
        "or a playbook comment. The canonical source is",
        "[`docs/gotchas.md`](https://github.com/Shawn-Falconbury/ansible-library/blob/main/docs/gotchas.md)",
        "in the repository — these pages are generated from it.",
        "",
    ]
    for name, blurb, numbers in GROUPS:
        out += [f"## {name}", "", blurb, ""]
        for n in numbers:
            e = by_number[n]
            out.append(f"- **{n:02d}.** [{e['title_plain']}]({e['page']})")
        out.append("")

    out += [
        "---",
        "",
        "## Adding one",
        "",
        "Append a `## N. Title` section to `docs/gotchas.md`, assign the number to a",
        "group in `scripts/build_wiki.py`, and rebuild. The build refuses to complete",
        "if a gotcha is ungrouped, so a new entry cannot quietly fail to appear here.",
        "",
    ]
    return "\n".join(out)


def render_sidebar(entries: list[dict]) -> str:
    by_number = {e["number"]: e for e in entries}
    out = [
        "### [Home](Home)",
        "",
        "**Using it**",
        "- [Getting started](Getting-Started)",
        "- [Playbook catalogue](Playbook-Catalogue)",
        "- [Conventions](Conventions)",
        "",
        "**Why it is built this way**",
        "- [Testing philosophy](Testing-Philosophy)",
        "- [Security model](Security-Model)",
        "",
        f"**[Gotchas](Gotchas)** ({len(entries)})",
    ]
    for name, _, numbers in GROUPS:
        out.append(f"<details><summary>{name}</summary>")
        out.append("")
        for n in numbers:
            e = by_number[n]
            out.append(f"- [{n:02d}. {e['title_plain']}]({e['page']})")
        out.append("")
        out.append("</details>")
    out.append("")
    return "\n".join(out)


def render_footer(entries: list[dict]) -> str:
    return (
        "---\n"
        "Generated from [`Shawn-Falconbury/ansible-library`]"
        "(https://github.com/Shawn-Falconbury/ansible-library) by "
        "`scripts/build_wiki.py`. Edit the repository, not the wiki.\n"
    )


def build(dest: Path) -> None:
    entries = parse_gotchas(GOTCHAS)
    check_groups(entries)

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    if WIKI_SRC.exists():
        for src in sorted(WIKI_SRC.glob("*.md")):
            shutil.copy2(src, dest / src.name)

    for e in entries:
        (dest / f"{e['page']}.md").write_text(render_gotcha_page(e, entries), encoding="utf-8")

    (dest / "Gotchas.md").write_text(render_index(entries), encoding="utf-8")
    (dest / "_Sidebar.md").write_text(render_sidebar(entries), encoding="utf-8")
    (dest / "_Footer.md").write_text(render_footer(entries), encoding="utf-8")

    # dest may be a temp dir under --check, which is not below ROOT.
    try:
        shown = dest.relative_to(ROOT)
    except ValueError:
        shown = dest
    print(f"built {len(list(dest.glob('*.md')))} pages into {shown}")
    print(f"  {len(entries)} gotcha pages, {len(GROUPS)} groups")


def check(dest: Path) -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "wiki"
        build(fresh)
        if not dest.exists():
            print(f"\nFAIL: {dest} does not exist. Run: python3 scripts/build_wiki.py")
            return 1
        cmp = filecmp.dircmp(str(fresh), str(dest))
        stale = sorted(cmp.diff_files + cmp.left_only + cmp.right_only)
        if stale:
            print("\nFAIL: wiki build is stale. Differing or missing pages:")
            for f in stale:
                print(f"  {f}")
            print("\nRun: python3 scripts/build_wiki.py")
            return 1
    print("\nOK: wiki build is current")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail if the committed build is stale")
    ap.add_argument("--out", type=Path, default=BUILD, help="output directory")
    args = ap.parse_args()
    return check(args.out) if args.check else (build(args.out) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
