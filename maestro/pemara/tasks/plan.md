# Implementation Plan: Maestro Hybrid Take Workflow v1

## Overview

Deliver the approved hybrid take workflow as small vertical slices while preserving the existing project schema and all prior media. Contract/readiness logic lands first, then safe assembly and final review, followed by cooperative GPU coordination and the accessible Studio controls.

## Architecture decisions

- Treat new contracts as optional additive fields; never bulk-migrate existing projects.
- Compute readiness from real files and approval state instead of trusting counters.
- Preserve old masters and expose staleness; never delete or replace silently.
- Keep media execution in the API job layer and domain persistence in `video_projects.py`.
- Use a cooperative file-backed GPU lease; no arbitrary process termination.

## Dependency graph

```text
take mode + continuity validation
        -> API views + prompt contract
        -> assembly readiness + fingerprints
        -> assembly job + final review
        -> accessible Studio controls

cooperative GPU lease
        -> generation/foley preflight adapters
        -> visible queue/lease status
```

## Task list

### Phase 1: Contracts and gates

- [x] Task 1: Take-mode and continuity contract slice.
- [x] Task 2: Approval-readiness and stale-master slice.

### Checkpoint: Domain foundation

- [x] Focused `test_video_projects.py` tests pass.
- [x] Existing projects return backward-compatible views.

### Phase 2: Safe finalization

- [x] Task 3: Assembly job and technical QC slice.
- [x] Task 4: Owner final-review slice.

### Checkpoint: Finalization

- [x] Synthetic approved sequence assembles locally.
- [x] Unapproved or incompatible sources fail before media mutation.

### Phase 3: Resource and interface

- [x] Task 5: Cooperative GPU lease slice.
- [x] Task 6: Accessible Studio workflow slice.

### Checkpoint: Complete

- [x] Focused backend, API, and UI contract suites pass.
- [x] Python compile and `git diff --check` pass.
- [x] Real local API reports readiness and master-review state.
- [x] No existing project artifact was deleted or auto-approved.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Dirty worktree overlaps relevant files | High | Inspect exact hunks, make narrow additive patches, preserve unrelated changes. |
| Mixed codecs make stream-copy assembly unsafe | High | Probe every source and fail closed with an actionable blocker. |
| Old masters look current after a take changes | High | Save and compare an ordered source fingerprint. |
| GPU lease goes stale after crash | Medium | PID/heartbeat validation and bounded stale recovery; never terminate external work. |
| UI implies technical pass is approval | High | Separate technical status from explicit owner final review. |

## Open questions

None. The owner approved the stated defaults and human gates.
