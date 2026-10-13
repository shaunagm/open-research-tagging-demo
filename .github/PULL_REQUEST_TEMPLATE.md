## Coding this change?

If this PR adds or updates files under `projects/`, leave **review comments on the Files tab** (not just conversation comments). Tags must look like this — lowercase, with a `/` and a value:

```text
#stance/permissive-with-conditions
#disclosure/required
#rationale/maintainer-and-reviewer-burden

Short free-text note about why this passage matters.
```

**Scope** needs a type and a position:

```text
#scope/code:restricted
```

Cheat sheet + full list: [`codebook/COMMENTING.md`](../codebook/COMMENTING.md)

### Common mistakes

| Don’t | Do |
|-------|-----|
| `#Disclosure` | `#disclosure/required` |
| `#stance permissive` | `#stance/permissive-with-conditions` |
| `#scope/code` | `#scope/code:restricted` |

---

## Summary

-

## Checklist

- [ ] Provenance filled in `projects/<slug>/project.yaml` (source URL + commit hash)
- [ ] Line comments use `#namespace/value` tags from the codebook
