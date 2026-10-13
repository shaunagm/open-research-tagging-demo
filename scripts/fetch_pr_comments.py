#!/usr/bin/env python3
"""Fetch all pull request review comments for a GitHub repo (all PRs).

Usage:
  python scripts/fetch_pr_comments.py [--owner OWNER] [--repo REPO] [--out PATH]

Env:
  GITHUB_TOKEN  optional; raises rate limits for public repos
  GITHUB_REPOSITORY  owner/repo (used by Actions if --owner/--repo omitted)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "site" / "data" / "raw_comments.json"
API = "https://api.github.com"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner", help="GitHub org or user")
    p.add_argument("--repo", help="Repository name")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def resolve_owner_repo(args: argparse.Namespace) -> tuple[str, str]:
    if args.owner and args.repo:
        return args.owner, args.repo
    env_repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in env_repo:
        owner, repo = env_repo.split("/", 1)
        return owner, repo
    print(
        "Pass --owner and --repo, or set GITHUB_REPOSITORY=owner/repo",
        file=sys.stderr,
    )
    sys.exit(2)


def github_get(url: str, token: str | None) -> tuple[object, dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "open-research-tagging-demo",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.load(resp)
            return body, {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API error {e.code} for {url}: {detail}") from e


def next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        bit = part.strip()
        if 'rel="next"' in bit:
            return bit[bit.find("<") + 1 : bit.find(">")]
    return None


def fetch_all_review_comments(owner: str, repo: str, token: str | None) -> list[dict]:
    url = f"{API}/repos/{owner}/{repo}/pulls/comments?per_page=100"
    comments: list[dict] = []
    while url:
        page, headers = github_get(url, token)
        if not isinstance(page, list):
            raise SystemExit(f"Unexpected API payload: {type(page)}")
        comments.extend(page)
        url = next_link(headers.get("link"))
    return comments


def main() -> None:
    args = parse_args()
    owner, repo = resolve_owner_repo(args)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    comments = fetch_all_review_comments(owner, repo, token)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": f"{owner}/{repo}",
        "endpoint": f"{API}/repos/{owner}/{repo}/pulls/comments",
        "count": len(comments),
        "comments": comments,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(comments)} review comments → {args.out}")


if __name__ == "__main__":
    main()
