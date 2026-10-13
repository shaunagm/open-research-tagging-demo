#!/usr/bin/env python3
"""Validate codebook hashtags in PR review comments.

Used by CI to flag malformed tags (e.g. #Disclosure instead of
#disclosure/required) when a review comment is posted, and as a
pre-merge scan of all review comments on a PR.

Usage:
  # Local / CI: check one body
  python scripts/check_comment_tags.py --body '#Disclosure'

  # Scan every review comment on a PR
  python scripts/check_comment_tags.py --owner ORG --repo REPO --pr 1

  # GitHub Actions (pull_request_review_comment event): reads GITHUB_EVENT_PATH
  python scripts/check_comment_tags.py --from-event --reply
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
sys.path.insert(0, str(ROOT / "scripts"))

from process_comments import load_codebook, parse_tags, tag_warnings  # noqa: E402

API = "https://api.github.com"
GUIDE = "codebook/COMMENTING.md"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--body", help="Check a single comment body string")
    p.add_argument("--owner")
    p.add_argument("--repo")
    p.add_argument("--pr", type=int, help="PR number to scan")
    p.add_argument(
        "--from-event",
        action="store_true",
        help="Read pull_request_review_comment payload from GITHUB_EVENT_PATH",
    )
    p.add_argument(
        "--reply",
        action="store_true",
        help="Post a reply on the review comment when tags are malformed",
    )
    p.add_argument(
        "--soft",
        action="store_true",
        help="Print warnings but always exit 0 (don't fail the check)",
    )
    return p.parse_args()


def resolve_owner_repo(args: argparse.Namespace) -> tuple[str, str]:
    if args.owner and args.repo:
        return args.owner, args.repo
    env_repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in env_repo:
        return tuple(env_repo.split("/", 1))  # type: ignore[return-value]
    raise SystemExit("Pass --owner/--repo or set GITHUB_REPOSITORY")


def github_request(
    method: str, url: str, token: str | None, payload: dict | None = None
) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "open-research-tagging-demo",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
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


def fetch_pr_review_comments(
    owner: str, repo: str, pr: int, token: str | None
) -> list[dict]:
    url = f"{API}/repos/{owner}/{repo}/pulls/{pr}/comments?per_page=100"
    out: list[dict] = []
    while url:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "open-research-tagging-demo",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            page = json.load(resp)
            link = resp.headers.get("Link") or resp.headers.get("link")
        if not isinstance(page, list):
            raise SystemExit(f"Unexpected payload: {type(page)}")
        out.extend(page)
        url = next_link(link)
    return out


def check_body(body: str, codebook: dict) -> list[str]:
    tags = parse_tags(body, codebook)
    return tag_warnings(body, tags)


def format_reply(warnings: list[str]) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "shaunagm/open-research-tagging-demo")
    guide_url = f"https://github.com/{repo}/blob/main/{GUIDE}"
    lines = [
        "⚠️ **Tag format check** — this review comment has hashtags that "
        "won't be picked up by the research site.",
        "",
    ]
    for w in warnings:
        lines.append(f"- {w}")
    lines.extend(
        [
            "",
            "Expected shape:",
            "```",
            "#disclosure/required",
            "#stance/permissive-with-conditions",
            "",
            "Optional free-text note…",
            "```",
            "",
            f"Guide: {guide_url}",
        ]
    )
    return "\n".join(lines)


def reply_to_review_comment(
    owner: str, repo: str, comment_id: int, body: str, token: str
) -> None:
    url = f"{API}/repos/{owner}/{repo}/pulls/comments/{comment_id}/replies"
    github_request("POST", url, token, {"body": body})


def main() -> None:
    args = parse_args()
    codebook = load_codebook()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    problems: list[tuple[str, list[str], dict | None]] = []

    if args.body is not None:
        warns = check_body(args.body, codebook)
        if warns:
            problems.append(("stdin", warns, None))
    elif args.from_event:
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        if not event_path:
            raise SystemExit("GITHUB_EVENT_PATH not set")
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        comment = event.get("comment") or {}
        body = comment.get("body") or ""
        warns = check_body(body, codebook)
        if warns:
            problems.append((comment.get("html_url") or "event-comment", warns, comment))
            if args.reply and token and comment.get("id"):
                owner, repo = resolve_owner_repo(args)
                # Avoid replying to our own bot replies looping forever
                user = (comment.get("user") or {}).get("login") or ""
                if user.endswith("[bot]"):
                    print("Skipping reply to bot comment")
                else:
                    reply_to_review_comment(
                        owner, repo, int(comment["id"]), format_reply(warns), token
                    )
                    print(f"Replied on review comment {comment['id']}")
    elif args.pr is not None:
        owner, repo = resolve_owner_repo(args)
        comments = fetch_pr_review_comments(owner, repo, args.pr, token)
        for comment in comments:
            user = (comment.get("user") or {}).get("login") or ""
            if user.endswith("[bot]"):
                continue
            warns = check_body(comment.get("body") or "", codebook)
            if warns:
                problems.append(
                    (comment.get("html_url") or str(comment.get("id")), warns, comment)
                )
    else:
        raise SystemExit("Pass --body, --from-event, or --pr N")

    if not problems:
        print("OK — no malformed codebook tags found.")
        return

    print(f"Found {len(problems)} comment(s) with tag issues:\n")
    for loc, warns, _ in problems:
        print(f"• {loc}")
        for w in warns:
            print(f"  - {w}")
        print()

    if args.soft:
        print("(soft mode: exiting 0)")
        return
    sys.exit(1)


if __name__ == "__main__":
    main()
