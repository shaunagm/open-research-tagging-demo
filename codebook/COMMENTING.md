# How to tag on a pull request

Use **PR review comments** on the Files tab (line or multi-line comments). Tags are hashtags in the comment body so the fetch script can parse them. Free-text notes after the tags are encouraged.

Codebook: [codebook.yaml](codebook.yaml) (draft — not final).

## Comment shape

```text
#stance/permissive-with-conditions
#scope/code:restricted
#rationale/maintainer-and-reviewer-burden
#guidance-level/substantive-guidance
#guidance/evaluation
#disclosure/required
#human-responsibility/yes

Authors must disclose AI use; reviewers are not first-line QA for generated code.
```

## Tag reference

| Dimension | Pattern | Examples |
|-----------|---------|----------|
| Stance | `#stance/<id>` | `#stance/gate-restrict` |
| Scope | `#scope/<type>:<position>` | `#scope/docs-and-text:allowed` |
| Rationale | `#rationale/<id>` | `#rationale/code-quality` |
| Guidance level | `#guidance-level/<id>` | `#guidance-level/some-guidance` |
| Guidance type | `#guidance/<id>` | `#guidance/scoping` |
| Disclosure | `#disclosure/<id>` | `#disclosure/required` |
| Human responsibility | `#human-responsibility/<id>` | `#human-responsibility/yes` |
| Enforcement | `#enforcement/<id>` | `#enforcement/contributor-blocked` |

Scope positions: `allowed`, `restricted`, `banned`, `not_addressed`.

Unknown tags still appear in the site table — fine while the codebook is in draft.

## Project-level vs passage tags

- **`projects/<slug>/project.yaml`** — overall Stance, Accountability, Context, and other codes for the whole policy.
- **PR line comments** — evidence on specific passages (Scope, rationale, guidance quotes).

## Sample comments for demo prep (pyOpenSci)

Leave these on `projects/pyopensci/generative-ai-policy.md` after the first PR is open:

1. On the disclosure / human-review paragraph:
   ```text
   #stance/permissive-with-conditions
   #disclosure/required
   #human-responsibility/yes
   #guidance/evaluation

   Disclosure required; meaningful human review expected before submission.
   ```

2. On “Protect volunteer reviewers” / equitable balance of effort:
   ```text
   #rationale/maintainer-and-reviewer-burden
   #guidance-level/substantive-guidance

   Explicit goal: reviewers are not first-line QA for generated code.
   ```

3. On communication in review issues (human-written; block spam accounts):
   ```text
   #scope/issues-and-pr-descriptions:restricted
   #enforcement/contributor-blocked

   Review communication should be human-written; spam/automated burden can lead to blocks.
   ```

4. On development history timeline (3–6 months public history):
   ```text
   #scope/code:restricted
   #guidance/scoping
   #guidance/iteration
   #rationale/code-quality

   Short-lived / rapid generation timelines face higher scrutiny; iterative public history required.
   ```

5. On package scope & design / situating in the ecosystem:
   ```text
   #guidance/design
   #guidance-level/substantive-guidance

   Asks for design tradeoffs and ecosystem situating — guidance beyond restriction.
   ```
