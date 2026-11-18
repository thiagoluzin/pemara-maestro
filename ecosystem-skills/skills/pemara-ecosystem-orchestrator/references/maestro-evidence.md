# Evidência de acesso, artefato e runtime Maestro

Aplicar somente ao auditar essas capacidades; não iniciar runtime ou mídia por inventário.



- Do not claim Maestro access is fixed from a health endpoint or a synthetic POST alone. Validate
  the real browser form, CSRF, Origin/Fetch Metadata path and that a safe disposable credential
  reaches authentication; keep real passwords undisclosed.
- Do not claim a take, approval or final is visible from a manifest write alone. Query the live
  project API, confirm the resolved filename/hash and, when owner review is required, open or play
  that exact artifact.
- Keep only main takes visible during take review. When the owner requests one integral review,
  expose only that film and preserve anchors, microsegments, rejections and older versions as
  rollback rather than catalog clutter.
- Treat cached UI state and chat wording as signals, not authoritative identity. Reconcile project
  id, take id, request id, file path and SHA-256 before applying an approval.
- Before a GPU batch, verify queue, lease/VRAM, process ownership, required plugin/node load status
  and the selected acceleration backend. A running ComfyUI endpoint does not prove its workflow can
  execute, and backend/plugin errors must not trigger a silent CPU or alternate-engine fallback.

For ecosystem scouting, require license, maintainer activity, dependency/secret
scan, overlap analysis, sandbox smoke, and human approval before adoption.

