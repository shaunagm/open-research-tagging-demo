# Open research tagging demo

Quick demo of using **GitHub PR review comments** as a collaborative coding layer for research files, then querying those comments in a static site.

Use case: evaluate AI contribution policies of open-source projects. Each project gets a folder of copied policy files (with source commit hash). Coders leave tagged line comments on PRs. A script pulls **all** PR review comments in the repo (merged across PRs) into a filterable table.

Inspired by [FOSSRIT/mismatches](https://github.com/FOSSRIT/mismatches) + [shaunagm/mismatches-comments](https://github.com/shaunagm/mismatches-comments) (which used commit comments; this demo uses PR review comments for better UX).

## Layout

```text
codebook/           Draft codebook + how to write comment tags
projects/           One folder per studied project (+ _template)
scripts/            Fetch + process GitHub PR review comments / project.yaml
site/               Static site (projects overview + comment browser)
```

## View the site (offline)

Two pages:

- **`projects.html`** — one row per project; overall codes from `project.yaml`. Hover a code for evidence links (all comments for that dimension, or only matching that value) into the comment browser.
- **`index.html`** — comment browser; accepts URL filters from the projects page (`?project=…&dimension=stance` or `?filter=stance:permissive-with-conditions`).

`site/data/comments.json` currently comes from **fixture** sample comments so the UI works before any live tagging.

```bash
pip install -r requirements.txt   # PyYAML for project.yaml

# regenerate from fixture
python3 scripts/process_comments.py \
  --in site/data/raw_comments.fixture.json \
  --out site/data/comments.json
python3 scripts/process_projects.py

# serve locally (needed for fetch() of JSON in some browsers)
python3 -m http.server -d site 8000
# open http://localhost:8000/projects.html
```

Comment browser: filter by text, project, PR number, and tag chips. Fixture banner shows until you replace data with a live fetch.

## Add a project

1. Copy `projects/_template/` to `projects/<slug>/`.
2. Copy relevant policy files into that folder.
3. Fill `project.yaml`: provenance (`source_repo`, `source_path`, `source_commit`, `retrieved_at`, …) and project-level codes (Stance, Accountability, Context, …).
4. Open a **pull request** that adds those files (this is the tagging surface).

Demo corpus: [`projects/pyopensci/`](projects/pyopensci/) — pyOpenSci generative AI policy + checklist, pinned to commit `499a7e2bedf55f78a39ab77edcb1ed36c04ecbd7`.

## Tag on a PR

On the PR **Files** tab, leave review comments on specific lines. Use hashtags from the codebook, then a short note:

```text
#stance/permissive-with-conditions
#disclosure/required
#guidance/evaluation

Disclosure required; human review expected before submission.
```

Full tag list and sample comments: [`codebook/COMMENTING.md`](codebook/COMMENTING.md). Draft codebook: [`codebook/codebook.yaml`](codebook/codebook.yaml).

- **`project.yaml`** = overall codes for the policy.
- **Line comments** = passage-level evidence (often Scope / rationale / guidance).

A second PR for the same project is fine — the site pools comments from every PR.

## Refresh from GitHub (after push + real comments)

```bash
export GITHUB_TOKEN=...   # optional but recommended
python3 scripts/fetch_pr_comments.py --owner YOUR_USER --repo YOUR_REPO
python3 scripts/process_comments.py
python3 scripts/process_projects.py   # refresh overall↔comment link counts
# then re-open site/ (or python3 -m http.server -d site 8000)
```

Optional workflows:

- [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml) — publishes `site/` to GitHub Pages on push to `main` (and manual dispatch)
- [`.github/workflows/check-comment-tags.yml`](.github/workflows/check-comment-tags.yml) — replies when a review comment has malformed tags; fails a PR check if any bad tags remain
- [`.github/workflows/update-comments.yml`](.github/workflows/update-comments.yml) — refreshes `site/data/` **daily** (14:00 UTC) and on **manual** “Run workflow” (push then triggers Pages deploy)

For a live demo right after tagging, use Actions → Update comment data → Run workflow (or the local commands above).

### Enable GitHub Pages (one-time)

1. Push this workflow to `main`.
2. Repo **Settings → Pages → Build and deployment → Source → GitHub Actions** (not “Deploy from a branch”).
3. Run **Actions → Deploy Pages → Run workflow**, or push any change under `site/`.
4. Site URL will be `https://<user>.github.io/open-research-tagging-demo/` (see Settings → Pages).

## Demo prep checklist (do this after first push)

You are here when the repo exists on GitHub and coworkers can open it.

1. Push this repo and open a PR that adds `projects/pyopensci/` (or keep the import PR open).
2. Leave the sample review comments from [`codebook/COMMENTING.md`](codebook/COMMENTING.md) on the policy / checklist lines.
3. Optional: second small PR with 1–2 more comments to show multi-PR merge in the table.
4. Run fetch + process (or the Update comment data workflow); commit/push updated `site/data/comments.json` and `projects.json` if you ran locally.
5. Live beat: add one new tagged comment on a call → run the workflow → filter to that tag.

## Later

- Tighten codebook as the real study design settles
