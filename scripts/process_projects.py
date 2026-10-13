#!/usr/bin/env python3
"""Build site/data/projects.json from projects/*/project.yaml + comments.json.

Overall codes come from each project's project.yaml. Comment counts / link
targets are joined from the processed comments file so the projects table can
link to filtered views of the comment browser.

Usage:
  python scripts/process_projects.py
  python scripts/process_projects.py --comments site/data/comments.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = ROOT / "projects"
DEFAULT_COMMENTS = ROOT / "site" / "data" / "comments.json"
DEFAULT_OUT = ROOT / "site" / "data" / "projects.json"
CODEBOOK_PATH = ROOT / "site" / "data" / "codebook.json"

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--comments", type=Path, default=DEFAULT_COMMENTS)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "PyYAML is required to read project.yaml files.\n"
            "  pip install pyyaml\n"
            f"Then re-run. (Tried to load {path})"
        ) from e
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected mapping in {path}")
    return data


def load_codebook() -> dict:
    if not CODEBOOK_PATH.exists():
        return {}
    return json.loads(CODEBOOK_PATH.read_text(encoding="utf-8"))


def label_for(codebook: dict, dimension: str, value: str) -> str:
    values = (codebook.get("values") or {}).get(dimension) or {}
    if value in values:
        return values[value]
    scope = codebook.get("scope") or {}
    if dimension == "scope_type":
        return (scope.get("contribution_types") or {}).get(value, value)
    if dimension == "scope_position":
        return (scope.get("positions") or {}).get(value, value)
    return str(value).replace("-", " ").replace("_", " ")


def normalize_scope_key(key: str) -> str:
    """docs_and_text -> docs-and-text (comment tag form)."""
    return key.replace("_", "-")


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def comment_index(comments: list[dict]) -> dict:
    """project -> { by_dimension: {dim: [ids]}, by_filter_key: {key: [ids]} }"""
    idx: dict = {}
    for row in comments:
        project = row.get("project")
        if not project:
            continue
        bucket = idx.setdefault(
            project, {"by_dimension": {}, "by_filter_key": {}, "all_ids": []}
        )
        cid = row.get("id")
        bucket["all_ids"].append(cid)
        for tag in row.get("tags") or []:
            dim = tag.get("dimension")
            key = tag.get("filter_key")
            if dim:
                bucket["by_dimension"].setdefault(dim, []).append(cid)
            if key:
                bucket["by_filter_key"].setdefault(key, []).append(cid)
    # unique preserve order
    for project, bucket in idx.items():
        bucket["all_ids"] = list(dict.fromkeys(bucket["all_ids"]))
        for d, ids in bucket["by_dimension"].items():
            bucket["by_dimension"][d] = list(dict.fromkeys(ids))
        for k, ids in bucket["by_filter_key"].items():
            bucket["by_filter_key"][k] = list(dict.fromkeys(ids))
    return idx


def link_payload(
    project: str,
    dimension: str,
    value: str | None,
    codebook: dict,
    cidx: dict,
) -> dict:
    """Build hover-link targets: all comments for dimension, and matching value."""
    pb = cidx.get(project) or {"by_dimension": {}, "by_filter_key": {}}
    all_ids = pb["by_dimension"].get(dimension, [])
    result = {
        "dimension": dimension,
        "dimension_label": next(
            (
                m["label"]
                for m in (codebook.get("namespaces") or {}).values()
                if m.get("dimension") == dimension
            ),
            dimension,
        ),
        "all": {
            "label": f"All {dimension.replace('_', ' ')} comments",
            "count": len(all_ids),
            "comment_ids": all_ids,
            "href": f"index.html?project={project}&dimension={dimension}",
        },
    }
    if value is not None:
        filter_key = f"{dimension}:{value}"
        match_ids = pb["by_filter_key"].get(filter_key, [])
        result["value"] = value
        result["value_label"] = label_for(codebook, dimension, value)
        result["matching"] = {
            "label": label_for(codebook, dimension, value),
            "count": len(match_ids),
            "comment_ids": match_ids,
            "href": f"index.html?project={project}&filter={filter_key}",
        }
    return result


def build_overall(coding: dict, project: str, codebook: dict, cidx: dict) -> dict:
    overall: dict = {}

    stance = coding.get("stance")
    if stance:
        overall["stance"] = {
            "values": [
                {
                    "id": stance,
                    "label": label_for(codebook, "stance", stance),
                    "links": link_payload(project, "stance", stance, codebook, cidx),
                }
            ]
        }

    rationales = as_list(coding.get("stated_rationale"))
    if rationales:
        overall["stated_rationale"] = {
            "values": [
                {
                    "id": r,
                    "label": label_for(codebook, "stated_rationale", r),
                    "links": link_payload(
                        project, "stated_rationale", r, codebook, cidx
                    ),
                }
                for r in rationales
            ]
        }

    guidance = coding.get("guidance_on_use") or {}
    level = guidance.get("level")
    if level:
        overall["guidance_level"] = {
            "values": [
                {
                    "id": level,
                    "label": label_for(codebook, "guidance_level", level),
                    "links": link_payload(
                        project, "guidance_level", level, codebook, cidx
                    ),
                }
            ]
        }
    gtypes = as_list(guidance.get("types"))
    if gtypes:
        overall["guidance_type"] = {
            "values": [
                {
                    "id": t,
                    "label": label_for(codebook, "guidance_type", t),
                    "links": link_payload(
                        project, "guidance_type", t, codebook, cidx
                    ),
                }
                for t in gtypes
            ]
        }

    acct = coding.get("accountability") or {}
    for field, dim in (
        ("human_responsibility", "human_responsibility"),
        ("disclosure", "disclosure"),
    ):
        val = acct.get(field)
        if val is not None:
            overall[dim] = {
                "values": [
                    {
                        "id": val,
                        "label": label_for(codebook, dim, str(val)),
                        "links": link_payload(
                            project, dim, str(val), codebook, cidx
                        ),
                    }
                ]
            }
    enforcement = as_list(acct.get("enforcement"))
    if enforcement:
        overall["enforcement"] = {
            "values": [
                {
                    "id": e,
                    "label": label_for(codebook, "enforcement", e),
                    "links": link_payload(
                        project, "enforcement", e, codebook, cidx
                    ),
                }
                for e in enforcement
            ]
        }

    # Scope: map of contribution_type -> position (skip not_addressed for display denseness)
    scope = coding.get("scope") or {}
    scope_values = []
    for raw_type, position in scope.items():
        if position in (None, "not_addressed"):
            continue
        ctype = normalize_scope_key(raw_type)
        filter_key = f"scope:{ctype}:{position}"
        pb = cidx.get(project) or {"by_dimension": {}, "by_filter_key": {}}
        all_scope = pb["by_dimension"].get("scope", [])
        match_ids = pb["by_filter_key"].get(filter_key, [])
        type_label = label_for(codebook, "scope_type", ctype)
        pos_label = label_for(codebook, "scope_position", position)
        scope_values.append(
            {
                "id": f"{ctype}:{position}",
                "contribution_type": ctype,
                "position": position,
                "label": f"{type_label} → {pos_label}",
                "links": {
                    "dimension": "scope",
                    "dimension_label": "Scope",
                    "all": {
                        "label": "All scope comments",
                        "count": len(all_scope),
                        "comment_ids": all_scope,
                        "href": f"index.html?project={project}&dimension=scope",
                    },
                    "matching": {
                        "label": f"{type_label} → {pos_label}",
                        "count": len(match_ids),
                        "comment_ids": match_ids,
                        "href": (
                            f"index.html?project={project}"
                            f"&scope_type={ctype}&scope_position={position}"
                        ),
                    },
                },
            }
        )
    if scope_values:
        overall["scope"] = {"values": scope_values}

    return overall


def build_project(path: Path, codebook: dict, cidx: dict) -> dict | None:
    data = load_yaml(path)
    slug = data.get("slug") or path.parent.name
    if slug.startswith("_"):
        return None
    coding = data.get("coding") or {}
    provenance = data.get("provenance") or {}
    context = (coding.get("context") or {}) if isinstance(coding, dict) else {}
    pb = cidx.get(slug) or {"all_ids": []}
    return {
        "slug": slug,
        "display_name": data.get("display_name") or slug,
        "provenance": {
            "source_repo": provenance.get("source_repo"),
            "source_commit": provenance.get("source_commit"),
            "source_url": provenance.get("source_url"),
            "policy_location": provenance.get("policy_location"),
            "retrieved_at": jsonable(provenance.get("retrieved_at")),
        },
        "context": {
            "governance": context.get("governance"),
            "domain": context.get("domain"),
        },
        "overall": build_overall(coding, slug, codebook, cidx),
        "comment_count": len(pb.get("all_ids") or []),
        "comments_href": f"index.html?project={slug}",
        "yaml_path": str(path.relative_to(ROOT)),
    }


def main() -> None:
    args = parse_args()
    codebook = load_codebook()
    comments = []
    if args.comments.exists():
        payload = json.loads(args.comments.read_text(encoding="utf-8"))
        comments = payload.get("data") or []
    else:
        print(f"Warning: no comments file at {args.comments}; counts will be 0")

    cidx = comment_index(comments)
    projects = []
    for yaml_path in sorted(PROJECTS_DIR.glob("*/project.yaml")):
        if yaml_path.parent.name.startswith("_"):
            continue
        row = build_project(yaml_path, codebook, cidx)
        if row:
            projects.append(row)

    comments_path = args.comments.resolve()
    try:
        comments_rel = str(comments_path.relative_to(ROOT))
    except ValueError:
        comments_rel = str(comments_path)
    out = {
        "meta": {
            "count": len(projects),
            "comments_source": comments_rel,
            "codebook_version": codebook.get("version"),
        },
        "data": projects,
    }
    def _default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, default=_default) + "\n", encoding="utf-8")
    print(f"Wrote {len(projects)} projects → {args.out}")


if __name__ == "__main__":
    main()
