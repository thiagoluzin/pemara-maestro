# Maestro Hybrid Take Workflow v1

## Objective

Turn the lessons from the Vejito versus Super Boo project into a reusable Studio workflow. Every take declares whether it is a precision, action, or payoff take; carries explicit character and motion-continuity contracts; exposes approval dependencies; and can only enter the final assembly when its picture and required audio have been explicitly approved by the owner.

## Product contract

### Take modes

- `PRECISION`: choreography whose sequence must be followed literally. Prompts must prioritize ordered micro-beats, hand/object ownership, body separation, anatomy, and a readable final state.
- `ACTION`: sustained combat or movement. Prompts must prioritize forceful contact, reaction, recoil, displacement, cloth/debris response, non-soft impacts, and useful motion through the cut.
- `PAYOFF`: transformation, finishing move, reveal, or consequence. Prompts must prioritize escalation, a readable decisive event, environmental response, and a moving or naturally dissipating ending without a frozen tail.

Projects without an explicit mode remain compatible and expose `UNSPECIFIED`; they are not rewritten automatically.

### Continuity contract

Each take may persist a `continuity_contract` with these public fields:

- `character_topology`: expected visible characters and forbidden additions, removals, fusion errors, duplicated limbs, or anatomy changes.
- `wardrobe_lock`: immutable costume/accessory requirements.
- `power_state`: state entering and leaving the take.
- `entry_motion` and `exit_motion`: body, object, camera direction, and velocity handed across the cut.
- `impact_language`: contact, recoil, displacement, cloth, dust, debris, and environmental reaction requirements.
- `forbidden_transitions`: at minimum freeze, static tail, crossfade, and reset when continuous action is required.

The contract is additive and project-local. Existing `shot_contract`, `screen_continuity_contract`, and identity-bible fields remain authoritative and are not migrated destructively.

### Approval and assembly readiness

The API computes readiness from current project artifacts every time it is requested. A take is eligible only when:

1. its visual state is `APPROVED` or `FINAL`;
2. a project-local active video exists;
3. no FHD candidate is awaiting human review;
4. required audio exists and has completed explicit human listening;
5. no take is currently rejected, generating, or awaiting a required decision.

Readiness returns a stable list of blocking reasons and the ordered source records. A previously registered master is marked `stale` in the API view when its saved source fingerprint differs from the current approved sequence. The old file remains preserved and downloadable; nothing is deleted automatically.

### Safe assembly

`POST /api/video-projects/{projectId}/assembly-jobs` starts one local asynchronous job only when readiness passes. The job:

1. resolves only project-local approved sources;
2. concatenates hard cuts with no freeze insertion or crossfade;
3. preserves video streams when all sources are compatible, otherwise fails closed instead of silently reducing quality;
4. concatenates approved audio in editorial order;
5. produces a review proxy separately from the untouched master;
6. performs full decode, duration/frame-count, freeze/static-tail, audio-presence, and boundary-contact checks;
7. registers provenance, hashes, source fingerprint, and `TECHNICAL_PASS_PENDING_OWNER_FINAL_VIEWING` in `project_manifest.json`.

`POST /api/video-projects/{projectId}/final-review` records `approve` or `reject`. Rejection requires a reason. Technical success never equals owner approval.

### GPU coordination

GPU jobs use a local cooperative lease containing owner, operation, project, take, job, acquisition time, and heartbeat. A lease never terminates arbitrary processes. Registered adapters may release only their own confirmed-idle resources; active or unknown third-party work causes a clear fail-closed response. Lease state is visible in the Studio status API.

### Accessible Studio surface

The project page exposes:

- a text badge for the take mode;
- the continuity summary without relying on color alone;
- a single readiness message listing exact blockers;
- `Montar sequência aprovada` only when safe;
- progress and errors through `aria-live` status;
- explicit `Aprovar master` and `Reprovar master` actions after final viewing.

## Technology and structure

- Backend: Python 3, FastAPI, project-local JSON persistence, existing atomic writers and job store.
- Media: bundled FFmpeg/FFprobe path already used by Studio; no new dependency.
- Frontend: existing vanilla JavaScript, HTML, and CSS assets.
- Domain owner: `services/studio/video_projects.py` owns contracts, readiness, provenance, and review persistence.
- API/job owner: `services/studio/main.py` owns asynchronous job lifecycle and media execution.
- GPU owner: `services/studio/gpu_lease.py` owns cooperative lease state only.

## Commands

Run from `E:\Pemara\maestro\pemara\services\studio`:

```powershell
python -m unittest test_video_projects.py
python -m unittest test_maestro_ui_contracts.py
python -m unittest test_generative_control.py
```

Static checks from the repository root:

```powershell
python -m py_compile services\studio\video_projects.py services\studio\gpu_lease.py services\studio\main.py
git diff --check
```

## Code style

Follow the existing direct, function-oriented Python and vanilla JavaScript style. Keep persistence atomic and validation fail-closed.

```python
def assembly_readiness(root: Path, project_id: str) -> dict[str, Any]:
    project_dir = _project_path(root, project_id)
    blockers: list[dict[str, str]] = []
    # Resolve real project-local artifacts, then return state rather than guesses.
    return {"ready": not blockers, "blockers": blockers, "sources": sources}
```

## Testing strategy

- Unit tests first for mode validation, prompt injection, readiness blockers, stale-master detection, and final-review rules.
- Integration tests against temporary real project folders for source resolution and atomic manifest updates.
- API contract tests for job start, progress, error shape, and human final review.
- UI contract tests for accessible controls, Portuguese labels, and event wiring.
- A bounded real assembly smoke test uses synthetic local clips; no heavy model inference is required.

## Boundaries

- Preserve all current project files and existing approvals.
- Never auto-approve image, audio, or master.
- Never use pending, rejected, missing, external, or path-escaping sources.
- Never interrupt active or unknown GPU work.
- Never lower resolution, frame rate, encoder quality, or model settings to make a job pass.
- Never insert crossfades, frozen bridges, or static padding to hide continuity failures.
- No network access and no new dependency.
- No broad refactor of the existing generation pipelines.

## Success criteria

- New and existing projects load without migration.
- All three take modes are validated, persisted, exposed, and influence generation prompts.
- Readiness explains every missing approval and detects a stale registered master.
- Assembly cannot start with an unapproved visual, pending FHD candidate, or unapproved required audio.
- Successful assembly remains pending owner final viewing until explicit approval.
- GPU contention produces a safe, actionable status without killing another workload.
- Focused and regression tests pass, and the real API surface reports the new fields.

## Decisions already approved

The owner approved implementation after reviewing the workflow lessons. Defaults are reusable across projects, local and reversible, human-gated, approved-source-only, and cooperative with existing GPU workloads. No open product question blocks v1.
