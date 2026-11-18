# Maestro Hybrid Take Workflow v1 tasks

## Task 1: Take-mode and continuity contract

**Acceptance criteria:**
- [x] `PRECISION`, `ACTION`, and `PAYOFF` validate and persist; legacy takes expose `UNSPECIFIED`.
- [x] Public take view exposes normalized continuity data.
- [x] Generation prompt contains the matching mandatory mode direction.

**Verification:**
- [x] RED then GREEN focused unit tests in `test_video_projects.py`.

**Dependencies:** None

**Files likely touched:** `services/studio/video_projects.py`, `services/studio/test_video_projects.py`, templates.

## Task 2: Approval readiness and staleness

**Acceptance criteria:**
- [x] Readiness lists exact blockers and ordered approved sources.
- [x] Required audio and pending FHD review block assembly.
- [x] Registered master reports stale after approved source state changes.

**Verification:**
- [x] Temporary-folder integration tests pass.

**Dependencies:** Task 1

**Files likely touched:** `services/studio/video_projects.py`, `services/studio/test_video_projects.py`.

## Task 3: Safe assembly job

**Acceptance criteria:**
- [x] API starts one asynchronous job only when readiness passes.
- [x] Compatible approved sources produce master, proxy, hashes, provenance, and technical QC.
- [x] Incompatible or path-escaping sources fail before registration.

**Verification:**
- [x] API contract and bounded synthetic-media smoke test pass.

**Dependencies:** Task 2

**Files likely touched:** `services/studio/main.py`, `services/studio/video_projects.py`, related tests.

## Task 4: Owner final review

**Acceptance criteria:**
- [x] Approve records owner approval and completes the project.
- [x] Reject requires reason and preserves master as rejected evidence.
- [x] A stale master cannot be approved.

**Verification:**
- [x] Unit and API contract tests pass.

**Dependencies:** Task 3

**Files likely touched:** `services/studio/video_projects.py`, `services/studio/main.py`, tests.

## Task 5: Cooperative GPU lease

**Acceptance criteria:**
- [x] Lease records owner/job/project/take and supports heartbeat/release.
- [x] Active or unknown conflicting work fails closed without process termination.
- [x] Studio status exposes the current lease.

**Verification:**
- [x] Deterministic lease unit tests and existing generation controls pass.

**Dependencies:** None

**Files likely touched:** `services/studio/gpu_lease.py`, `services/studio/main.py`, tests.

## Task 6: Accessible Studio workflow

**Acceptance criteria:**
- [x] Take mode and continuity are readable as text.
- [x] Readiness blockers and assembly progress use `aria-live`.
- [x] Assembly and final owner-review buttons call the new APIs safely.

**Verification:**
- [x] `test_maestro_ui_contracts.py` passes and live local assets/API expose the new flow.

**Dependencies:** Tasks 2-5

**Files likely touched:** `app/index.html`, `app/assets/maestro.js`, `app/assets/maestro.css`, UI tests.
