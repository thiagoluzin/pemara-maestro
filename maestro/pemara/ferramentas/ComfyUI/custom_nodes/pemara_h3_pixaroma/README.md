# PEMARA Pixaroma / Spectrum bridge

Opt-in integration for the FFVI opera pilot. It does not change Spectrum source
files or enable Pixaroma on unrelated graphs.

## Pinned source

`vendor/` contains the required Python modules from
https://github.com/pixaroma/ComfyUI-Pixaroma at commit
`21a1f1510c9667410c59315e1aea54dfb1fb14a9` (1.4.229), with its license.
Audio Sync alone was updated on 2026-11-01 from upstream commit
`890c0b8efc917fbad02809cf07cfcaf143e170c5` (1.4.247). Long Video and shared
helpers retain the pinned 1.4.229 bridge. CPU checks preserve original audio sample
counts at 32/44.1/48 kHz and the incoming video noise mask; this is not a new
long-video GPU or lip-sync qualification.
Only Long Video and Audio Sync are exposed. The full Pixaroma UI/server package
is not imported.

## Model path

H3 BASE → sigma shift → SageAttention → four-head guard → Spectrum →
PemaraPixaromaSpectrumLongVideo → optional PixaromaH3AudioSync → sampler.
The qualified pilot uses res_multistep, 20 steps, Spectrum audio replay and
system-RAM history. No FirstBlockCache, FastH3, Continuum, Face Refine or video
DLSS is involved.

Pixaroma must wrap each model call before Spectrum. Each temporal window receives
a distinct Spectrum row label. The shared history topology retains the entire
ordered window plan and every native window topology. Native geometry is checked
on every call, so unexpected layout changes remain errors. Context-local hooks
leave normal Spectrum calls unchanged.

The outer audit requires actual calls, causal forecasts and offline replay before
returning a generated result. Its console receipt reports counts per window.
This validates execution, not acting, identity, lip sync or artistic quality.

## Optional local window direction

The bridge exposes up to four consecutive `window_direction_N` CONDITIONING
inputs. They must match the exact native window count. Only the text states and
their matching token tags change per window: references, correctly sliced native
guides, masks and source audio remain those of the main graph. Raw Qwen states
are refined once per window by the loaded native H3 text preprocessor. The
Spectrum topology includes each window's resulting text geometry and retains
separate history rows. Leaving these inputs disconnected preserves the original
route. This is an opt-in local integration, not an upstream Pixaroma update.

Motivation: the first FFVI P14 30-second candidate replayed its entire flower
release in each window. Its temporal QC rejected it before Maestro delivery.
Local directions encode approach, one release, empty-hand withdrawal and continued
departure as distinct current states. CPU text-routing and history tests do not
prove that a generated actor obeys the direction; real temporal QC is mandatory.

P14v2 still showed a double image and pose reset near9.4s. Both overlapping-window
variants are barred for that directed release. The local bridge therefore also
accepts an explicit Window up to30seconds as a single native full-context H3 call
when it covers the entire latent. The upstream window helper remains unchanged.
Sage4, Spectrum's history/forecast/replay audit and Pixaroma AudioSync remain in
the path; no temporal subdivision or blend is done. This needs a large card and
real capacity/temporal qualification. It is not the upstream4.5-minute benchmark
and is not automatically enabled on existing graphs.

## Verification

CPU history/replay tests live in the FFVI project under
`experiments/pixaroma/test_bridge.py`; synthetic tests exercise the installed
Spectrum runtime with four and seven windows, separate feature offsets and a
geometry-change rejection. The real GPU pilot and temporal QC have separate
receipts in that project's `experiments/pixaroma` and `qc/P01_pixaroma_v1` folders.

The native window blend and audio-lock calculations are upstream code. Output
audio comes from the original 48 kHz recording; the model receives the separately
encoded 32 kHz audio conditioning. Do not claim sample-exact PCM preservation
after an AAC export or lip-sync approval from a successful render.

## Optional native fixed-stage control

`PemaraH3StageLockedLatent` encodes an approved incoming stage frame across the
target duration using the native H3 VAE. A reviewed RGB region image controls the
native nested denoise mask: the actor region is sampled freely, the remaining
stage is fixed and the reference audio remains zero-masked. This is generation
control, not video restoration, DLSS, upscaling or a post-render camera repair.
Geometry mismatches fail before sampling. It is opt-in and intended only for a
directed locked camera and stationary stage; it is not a general moving-camera
solution. CPU mask/audio tests and real GPU receipts live in the FFVI project.

## Removal

After confirming the queue is idle through MCP, remove only this runtime junction
and restart through MCP to stop exposing these nodes. Preserve this source pack
and receipts for reproducibility. No global Spectrum rollback is needed.
