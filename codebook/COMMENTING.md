# How to tag on a pull request

Use **PR review comments** on the Files tab (line or multi-line). Put codebook tags on their own lines at the top of the comment, then a short free-text note.

Full codebook: [codebook.yaml](codebook.yaml) (draft — not final).

## Copy-paste starter

```text
#stance/permissive-with-conditions
#disclosure/required

One or two sentences on what this passage shows.
```

More starters below. After you comment, someone runs `scripts/fetch_pr_comments.py` so tags show up on the site.

A GitHub Action watches review comments: if a tag looks malformed (e.g. `#Disclosure` with no `/value`), the bot replies on that comment. The same check runs on the PR as a status check before merge.

## Rules (short)

1. **Lowercase** hashtags.
2. Always **`#namespace/value`** — a slash is required.
3. **Scope** is special: `#scope/<type>:<position>` (colon between type and position).
4. Unknown values still show on the site (codebook is draft); bare `#Disclosure` with no `/value` will **not** parse.

## Common mistakes

| Don’t write | Write instead |
|-------------|----------------|
| `#Disclosure` | `#disclosure/required` |
| `#stance` or `#stance permissive` | `#stance/permissive-with-conditions` |
| `#scope/code` | `#scope/code:restricted` |
| Conversation comment on the PR | Review comment on the **Files** tab (needs a line) |

## Tag reference

| Dimension | Pattern | Examples |
|-----------|---------|----------|
| Stance | `#stance/<id>` | `#stance/gate-restrict` |
| Scope | `#scope/<type>:<position>` | `#scope/docs-and-text:allowed` |
| Rationale | `#rationale/<id>` | `#rationale/code-quality` |
| Guidance level | `#guidance-level/<id>` | `#guidance-level/some-guidance` |
| Guidance type | `#guidance/<id>` | `#guidance/evaluation` |
| Disclosure | `#disclosure/<id>` | `#disclosure/required` |
| Human responsibility | `#human-responsibility/<id>` | `#human-responsibility/yes` |
| Enforcement | `#enforcement/<id>` | `#enforcement/contributor-blocked` |

**Stance ids:** `ban`, `discouraged`, `gate-restrict`, `permissive-with-conditions`, `permissive`, `no-policy`

**Disclosure ids:** `none`, `recommended`, `required`

**Scope types:** `code`, `tests`, `docs-and-text`, `issues-and-pr-descriptions`, `review`, `autonomous-agents`, `contribution-types-not-defined`

**Scope positions:** `allowed`, `restricted`, `banned`, `not_addressed`

**Rationale ids:** `code-quality`, `maintainer-and-reviewer-burden`, `security`, `licensing-and-copyright`, `environmental`, `social-and-ethical`, `contributor-learning-and-skill-development`, `other`

## Project-level vs passage tags

- **`projects/<slug>/project.yaml`** — overall Stance, Accountability, Context, etc. for the whole policy.
- **PR line comments** — evidence on specific passages.

## Sample comments (pyOpenSci)

Leave on `projects/pyopensci/generative-ai-policy.md` (or checklist) while a PR is open:

1. Disclosure / human-review paragraph:
   ```text
   #stance/permissive-with-conditions
   #disclosure/required
   #human-responsibility/yes
   #guidance/evaluation

   Disclosure required; meaningful human review expected before submission.
   ```

2. Protect volunteer reviewers:
   ```text
   #rationale/maintainer-and-reviewer-burden
   #guidance-level/substantive-guidance

   Explicit goal: reviewers are not first-line QA for generated code.
   ```

3. Communication in review issues:
   ```text
   #scope/issues-and-pr-descriptions:restricted
   #enforcement/contributor-blocked

   Review communication should be human-written; spam/automated burden can lead to blocks.
   ```

4. Development history timeline:
   ```text
   #scope/code:restricted
   #guidance/scoping
   #guidance/iteration
   #rationale/code-quality

   Short-lived / rapid generation timelines face higher scrutiny; iterative public history required.
   ```

5. Package scope & design:
   ```text
   #guidance/design
   #guidance-level/substantive-guidance

   Asks for design tradeoffs and ecosystem situating — guidance beyond restriction.
   ```
