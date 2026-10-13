#!/usr/bin/env python3
"""Normalize PR review comments and parse codebook hashtags.

Reads site/data/raw_comments.json (from fetch_pr_comments.py) or a fixture
shaped the same way, writes site/data/comments.json for the static site.

Tags are enriched with dimension labels from site/data/codebook.json so the
UI can filter by rationale option, scope type/position, etc.

Usage:
  python scripts/process_comments.py [--in PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "site" / "data" / "raw_comments.json"
DEFAULT_OUT = ROOT / "site" / "data" / "comments.json"
CODEBOOK_PATH = ROOT / "site" / "data" / "codebook.json"

# #stance/gate-restrict  or  #scope/code:restricted
# Also accept #disclosure:required (colon instead of slash) as a common slip.
TAG_RE = re.compile(
    r"#(?P<ns>[a-z0-9-]+)[/:](?P<val>[a-z0-9-]+)(?::(?P<qual>[a-z0-9-]+))?",
    re.IGNORECASE,
)
# Any #Word token — used to flag malformed tags like #Disclosure with no /value
HASH_TOKEN_RE = re.compile(r"#([A-Za-z][\w-]*)")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="infile", type=Path, default=DEFAULT_IN)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def load_codebook() -> dict:
    if not CODEBOOK_PATH.exists():
        return {"namespaces": {}, "values": {}, "scope": {}, "filter_order": []}
    return json.loads(CODEBOOK_PATH.read_text(encoding="utf-8"))


def humanize(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").strip().capitalize()


def enrich_tag(raw_tag: dict, codebook: dict) -> dict:
    """Attach dimension, labels, and filter keys to a parsed tag."""
    ns = raw_tag["namespace"]
    val = raw_tag["value"]
    qual = raw_tag.get("qualifier")
    ns_meta = (codebook.get("namespaces") or {}).get(ns, {})
    dimension = ns_meta.get("dimension") or ns.replace("-", "_")
    dim_label = ns_meta.get("label") or humanize(dimension)
    kind = ns_meta.get("kind") or "value"

    tag = {
        **raw_tag,
        "dimension": dimension,
        "dimension_label": dim_label,
        "kind": kind,
    }

    if kind == "scope":
        # #scope/<contribution-type>:<position>
        contrib = val
        position = qual or "not_addressed"
        scope = codebook.get("scope") or {}
        contrib_label = (scope.get("contribution_types") or {}).get(
            contrib, humanize(contrib)
        )
        pos_label = (scope.get("positions") or {}).get(position, humanize(position))
        tag["contribution_type"] = contrib
        tag["contribution_type_label"] = contrib_label
        tag["position"] = position
        tag["position_label"] = pos_label
        tag["value_label"] = f"{contrib_label}: {pos_label}"
        tag["display"] = f"{dim_label}: {contrib_label} → {pos_label}"
        tag["filter_key"] = f"scope:{contrib}:{position}"
    else:
        value_labels = (codebook.get("values") or {}).get(dimension) or {}
        value_label = value_labels.get(val, humanize(val))
        tag["value_label"] = value_label
        tag["display"] = f"{dim_label}: {value_label}"
        tag["filter_key"] = f"{dimension}:{val}"

    return tag


def parse_tags(body: str, codebook: dict) -> list[dict]:
    tags = []
    for m in TAG_RE.finditer(body or ""):
        raw = {
            "raw": m.group(0).lower(),
            "namespace": m.group("ns").lower(),
            "value": m.group("val").lower(),
        }
        if m.group("qual"):
            raw["qualifier"] = m.group("qual").lower()
        tags.append(enrich_tag(raw, codebook))
    return tags


def tag_warnings(body: str, tags: list[dict]) -> list[str]:
    """Flag hashtags that look intentional but did not parse as codebook tags."""
    text = body or ""
    covered = set()
    for m in TAG_RE.finditer(text):
        covered.update(range(m.start(), m.end()))

    warnings: list[str] = []
    for m in HASH_TOKEN_RE.finditer(text):
        if any(i in covered for i in range(m.start(), m.end())):
            continue
        token = m.group(0)
        warnings.append(
            f"{token} looks like a tag but needs #namespace/value "
            f"(e.g. #disclosure/required). See codebook/COMMENTING.md"
        )

    if not tags and not warnings and text.strip().startswith("#"):
        warnings.append(
            "Comment starts with # but no tags parsed. "
            "Use #namespace/value — see codebook/COMMENTING.md"
        )
    return warnings


def codes_by_dimension(tags: list[dict]) -> dict:
    """Group enriched tags for easy filtering: dimension -> list of entries."""
    out: dict[str, list] = {}
    for t in tags:
        dim = t["dimension"]
        entry: dict
        if t.get("kind") == "scope":
            entry = {
                "contribution_type": t["contribution_type"],
                "position": t["position"],
                "filter_key": t["filter_key"],
                "display": t["display"],
            }
        else:
            entry = {
                "value": t["value"],
                "filter_key": t["filter_key"],
                "display": t["display"],
            }
        out.setdefault(dim, []).append(entry)
    return out


def project_from_path(path: str | None) -> str | None:
    if not path:
        return None
    parts = path.replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "projects" and parts[1] != "_template":
        return parts[1]
    return None


def pr_number_from_comment(comment: dict) -> int | None:
    pr_url = comment.get("pull_request_url") or ""
    if pr_url.rstrip("/").split("/")[-1].isdigit():
        return int(pr_url.rstrip("/").split("/")[-1])
    html = comment.get("html_url") or ""
    m = re.search(r"/pull/(\d+)", html)
    return int(m.group(1)) if m else None


def line_range(comment: dict) -> tuple[int | None, int | None]:
    """Return (start_line, end_line) 1-based inclusive, if known."""
    end = comment.get("line") or comment.get("original_line")
    start = comment.get("start_line") or comment.get("original_start_line") or end
    try:
        end_i = int(end) if end is not None else None
        start_i = int(start) if start is not None else None
    except (TypeError, ValueError):
        return None, None
    if start_i is not None and end_i is not None and start_i > end_i:
        start_i, end_i = end_i, start_i
    return start_i, end_i


def quote_from_diff_hunk(diff_hunk: str | None) -> str | None:
    """GitHub includes diff_hunk on PR review comments (the selected lines' context)."""
    if not diff_hunk:
        return None
    lines = []
    for raw in diff_hunk.splitlines():
        if raw.startswith("@@"):
            continue
        if raw.startswith(("+", "-", " ")):
            # Keep additions and context; skip pure deletions for readability
            if raw.startswith("-"):
                continue
            lines.append(raw[1:])
        else:
            lines.append(raw)
    text = "\n".join(lines).strip()
    return text or None


def quote_from_local_file(
    path: str | None, start: int | None, end: int | None
) -> tuple[str | None, str | None]:
    """
    Read the commented span from the workspace copy of the file.
    Multi-line selection → exact lines. Single line → surrounding paragraph.
    Returns (quote, mode) where mode is 'selection' or 'paragraph'.
    """
    if not path or end is None:
        return None, None
    file_path = ROOT / path
    if not file_path.is_file():
        return None, None
    try:
        file_lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None, None
    if not file_lines:
        return None, None

    start_i = start or end
    # clamp to file
    start_i = max(1, min(start_i, len(file_lines)))
    end_i = max(1, min(end, len(file_lines)))

    if start_i != end_i:
        chunk = file_lines[start_i - 1 : end_i]
        return "\n".join(chunk).strip(), "selection"

    # Expand single line to blank-line-bounded paragraph
    idx = end_i - 1
    lo = idx
    while lo > 0 and file_lines[lo - 1].strip() != "":
        lo -= 1
    hi = idx
    while hi + 1 < len(file_lines) and file_lines[hi + 1].strip() != "":
        hi += 1
    chunk = file_lines[lo : hi + 1]
    return "\n".join(chunk).strip(), "paragraph"


def resolve_quote(comment: dict) -> dict:
    """
    Build a readable source quote for the UI.

    GitHub PR review comments include `diff_hunk`, and multi-line comments
    also set `start_line`..`line` (a selection). When the commented file is
    in this repo we prefer the local text (exact selection, or paragraph for
    a single line). Fall back to cleaning `diff_hunk` when the file is absent.
    """
    start, end = line_range(comment)
    hunk = comment.get("diff_hunk")
    path = comment.get("path")

    file_quote, mode = quote_from_local_file(path, start, end)
    if file_quote:
        return {
            "quote": file_quote,
            "quote_source": mode or "paragraph",
            "start_line": start,
            "line": end,
            "diff_hunk": hunk,
        }

    hunk_quote = quote_from_diff_hunk(hunk)
    if hunk_quote:
        return {
            "quote": hunk_quote,
            "quote_source": "diff_hunk",
            "start_line": start,
            "line": end,
            "diff_hunk": hunk,
        }

    return {
        "quote": None,
        "quote_source": None,
        "start_line": start,
        "line": end,
        "diff_hunk": hunk,
    }


def normalize(comment: dict, codebook: dict) -> dict:
    body = comment.get("body") or ""
    path = comment.get("path")
    user = (comment.get("user") or {}).get("login")
    tags = parse_tags(body, codebook)
    warnings = tag_warnings(body, tags)
    quoted = resolve_quote(comment)
    return {
        "id": comment.get("id"),
        "body": body,
        "quote": quoted["quote"],
        "quote_source": quoted["quote_source"],
        "diff_hunk": quoted["diff_hunk"],
        "tags": tags,
        "tag_strings": [t["raw"] for t in tags],
        "displays": [t["display"] for t in tags],
        "filter_keys": [t["filter_key"] for t in tags],
        "parse_warnings": warnings,
        "codes": codes_by_dimension(tags),
        "path": path,
        "project": project_from_path(path),
        "start_line": quoted["start_line"],
        "line": quoted["line"],
        "side": comment.get("side"),
        "user": user,
        "pr_number": pr_number_from_comment(comment),
        "html_url": comment.get("html_url"),
        "commit_id": comment.get("commit_id"),
        "created_at": comment.get("created_at"),
        "updated_at": comment.get("updated_at"),
    }


def load_comments(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "comments" in data:
        return data["comments"]
    if isinstance(data, dict) and "data" in data:
        raise SystemExit(f"{path} looks processed already; pass raw_comments.json")
    if isinstance(data, list):
        return data
    raise SystemExit(f"Unrecognized JSON shape in {path}")


def main() -> None:
    args = parse_args()
    if not args.infile.exists():
        raise SystemExit(f"Missing input: {args.infile}")
    codebook = load_codebook()
    raw = load_comments(args.infile)
    rows = [normalize(c, codebook) for c in raw]
    infile = args.infile.resolve()
    try:
        relative = str(infile.relative_to(ROOT))
    except ValueError:
        relative = str(infile)
    out = {
        "meta": {
            "source_file": relative,
            "count": len(rows),
            "is_fixture": "fixture" in args.infile.name,
            "codebook_version": codebook.get("version"),
        },
        "data": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} comments → {args.out}")


if __name__ == "__main__":
    main()
