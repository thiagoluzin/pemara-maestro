import unittest
from pathlib import Path


class MaestroDirectorQueueUiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (
            Path(__file__).resolve().parents[2] / "app" / "assets" / "maestro.js"
        ).read_text(encoding="utf-8")

    def test_video_correction_registers_request_then_starts_job(self):
        start = self.source.index("async function submitFilmDirectorRequest")
        end = self.source.index("async function reviewFilmAnchor", start)
        function_source = self.source[start:end]

        request_patch = function_source.index('method: anchorReviewMode ? "POST" : "PATCH"')
        correction_branch = function_source.index('if (mode === "correction" && updated.canGenerate)')
        job_route = function_source.index("/jobs", correction_branch)

        self.assertLess(request_patch, correction_branch)
        self.assertLess(function_source.index('closeFilmDirectorDialog();', request_patch), correction_branch)
        self.assertIn('await fetchFilmDirectorRequest(endpoint', function_source)
        self.assertLess(correction_branch, job_route)
        self.assertIn("pedido registrado e correção enfileirada", function_source)
        self.assertIn("pedido salvo; não foi possível confirmar a entrada da correção na fila", function_source)

    def test_anchor_request_registers_before_explicit_gpu_executor(self):
        start = self.source.index("async function submitFilmDirectorRequest")
        end = self.source.index("async function reviewFilmAnchor", start)
        function_source = self.source[start:end]

        request_patch = function_source.index('method: anchorReviewMode ? "POST" : "PATCH"')
        anchor_branch = function_source.index('if (mode === "anchor" || anchorReviewMode)')
        executor_route = function_source.index("/anchor-jobs", anchor_branch)

        self.assertLess(request_patch, anchor_branch)
        self.assertLess(anchor_branch, executor_route)
        self.assertIn('if (mode === "correction" && updated.canGenerate) {', function_source)
        self.assertIn("Registrar e gerar foto-base com GPU (2/2)", self.source)
        self.assertIn("usa a GPU", self.source)

    def test_anchor_approval_sends_the_visually_confirmed_cast(self):
        start = self.source.index("async function reviewFilmAnchor")
        end = self.source.index("async function requestFilmAnchorBatch", start)
        function_source = self.source[start:end]

        self.assertIn("anchorExpectedVisibleCharacters", function_source)
        self.assertIn("actualVisibleCharacters", function_source)
        self.assertIn("humanConfirmed: true", function_source)
        self.assertNotIn("window.prompt", function_source)
        self.assertNotIn("humanConfirmationPhrase", function_source)

    def test_end_anchor_candidate_can_be_opened_without_a_start_anchor(self):
        registered_start = self.source.index("function filmTakeHasRegisteredAnchor")
        registered_end = self.source.index("function filmAnchorReviewRequestId", registered_start)
        registered_source = self.source[registered_start:registered_end]
        render_start = self.source.index("function renderFilmTakes")
        render_end = self.source.index("function renderFilmPlayerReview", render_start)
        render_source = self.source[render_start:render_end]
        preview_start = self.source.index("function openFilmTakePreview")
        preview_end = self.source.index("async function loadVideoSoundProviders", preview_start)
        preview_source = self.source[preview_start:preview_end]

        self.assertIn("take?.hasKeyframe || take?.hasEndKeyframeCandidate", registered_source)
        self.assertIn('filmTakeHasRegisteredAnchor(take) ? "anchor-image" : "thumbnail"', render_source)
        self.assertIn("take.hasKeyframe || take.hasEndKeyframeCandidate", render_source)
        self.assertIn("take.hasKeyframe || take.hasEndKeyframeCandidate", preview_source)

    def test_pending_end_anchor_is_reviewed_before_requesting_a_start_anchor(self):
        pending_start = self.source.index("function filmTakeAnchorPending")
        pending_end = self.source.index("function filmTakeAnchorReviewPending", pending_start)
        pending_source = self.source[pending_start:pending_end]

        self.assertIn("take?.hasEndKeyframeCandidate", pending_source)
        self.assertIn('anchor_delivered_pending_user_approval', pending_source)
        self.assertIn("return false", pending_source)

    def test_preanalysis_gallery_is_visible_without_implying_human_approval(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        render_start = self.source.index("function renderFilmTakes")
        render_end = self.source.index("function renderFilmPlayerReview", render_start)
        render_source = self.source[render_start:render_end]

        self.assertIn('id="film-preanalysis-dialog"', html)
        self.assertIn("take.hasPreanalysisGallery", render_source)
        self.assertIn("Abrir sequência de âncoras", render_source)
        self.assertIn("aprovação humana ainda pendente", render_source)
        self.assertIn("/preanalysis-gallery", self.source)
        self.assertIn("nenhuma aprovação humana é inferida", self.source)

    def test_pending_preanalysis_gallery_is_visible_in_review_view(self):
        review_start = self.source.index("function filmTakeNeedsReview")
        review_end = self.source.index("function filmTakeMatchesView", review_start)
        review_source = self.source[review_start:review_end]

        self.assertIn("take?.hasPreanalysisGallery", review_source)
        self.assertIn("take?.preanalysisGallery?.humanApproval", review_source)
        self.assertIn('=== "PENDING"', review_source)
        self.assertIn("film-preanalysis-gallery-preview", self.source)

    def test_rejected_takes_have_a_dedicated_history_view(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('data-film-view="rejected"', html)
        self.assertIn('id="film-view-rejected-count"', html)
        self.assertIn('"rejected"', self.source)
        self.assertIn('status || "").trim().toUpperCase() === "REJECTED"', self.source)
        self.assertIn("bloqueados para a montagem", self.source)


    def test_batch_failure_toast_identifies_take_and_server_reason(self):
        start = self.source.index("async function startFilmBatch")
        end = self.source.index("function bindEvents", start + 1)
        function_source = self.source[start:end]

        self.assertIn('`${item.takeId || "take"}: ${item.message || "erro desconhecido"}`', function_source)
        self.assertIn(".slice(0, 2)", function_source)
        self.assertIn("failureSummary", function_source)

    def test_production_button_reserves_three_but_releases_isolated_corrections(self):
        plan_start = self.source.index("function filmProductionBatchPlan")
        plan_end = self.source.index("function filmTakeAnchorPending", plan_start)
        plan_source = self.source[plan_start:plan_end]
        sync_start = self.source.index("function syncFilmBatchActions")
        sync_end = self.source.index("function filmStatusLabel", sync_start)
        sync_source = self.source[sync_start:sync_end]
        start = self.source.index("async function startFilmBatch")
        end = self.source.index("function bindEvents", start)
        batch_source = self.source[start:end]

        self.assertIn("policy.requireFullBatch === true", plan_source)
        self.assertIn("selected.length !== batchSize", plan_source)
        self.assertIn("policy.allowIncompleteCorrectionBatch === true", plan_source)
        self.assertIn("incompleteCorrectionBatch", plan_source)
        self.assertIn("!productionReady || activeProjectJobs > 0", sync_source)
        self.assertIn("`Produzir ${productionCount} take${productionCount === 1 ? \"\" : \"s\"}", sync_source)
        self.assertNotIn("Produzir 3 takes", sync_source)
        self.assertIn("O botão libera sozinho quando a produção atual terminar", sync_source)
        self.assertIn("liberada sem esperar fotos-base de takes futuros", sync_source)
        self.assertIn('productionPlan.ready !== true', batch_source)
        self.assertIn("Os três jobs entram agora", batch_source)
        self.assertIn("Gerar a correção", batch_source)
        self.assertIn("Trinca reservada", batch_source)
        self.assertIn("Correção iniciada", batch_source)

    def test_film_actions_use_the_selected_take_engine_readiness(self):
        helper_start = self.source.index("function filmTakeEngineKey")
        helper_end = self.source.index("function filmTakeProductionEligible", helper_start)
        helper_source = self.source[helper_start:helper_end]
        sync_start = self.source.index("function syncFilmBatchActions")
        sync_end = self.source.index("function filmStatusLabel", sync_start)
        sync_source = self.source[sync_start:sync_end]
        render_start = self.source.index("function renderFilmTakes")
        render_end = self.source.index("function renderFilmPlayerReview", render_start)
        render_source = self.source[render_start:render_end]

        self.assertIn('return "minimax_h3"', helper_source)
        self.assertIn('return "ltx_2_5"', helper_source)
        self.assertIn("engine_readiness", helper_source)
        self.assertIn("if (readiness && !engineKey) return false", helper_source)
        self.assertIn("productionPlan.selected.every(filmTakeEngineReady)", sync_source)
        self.assertIn("const engineReady = filmTakeEngineReady(take)", render_source)

    def test_batch_authorization_waits_for_real_project_data(self):
        state_start = self.source.index("films: {")
        state_end = self.source.index("assets: {", state_start)
        state_source = self.source[state_start:state_end]
        sync_start = self.source.index("function syncFilmBatchActions")
        sync_end = self.source.index("function filmStatusLabel", sync_start)
        sync_source = self.source[sync_start:sync_end]
        load_start = self.source.index("async function loadFilmProject")
        load_end = self.source.index("async function loadFilmProjects", load_start)
        load_source = self.source[load_start:load_end]

        self.assertIn("projectDataLoading: false", state_source)
        self.assertIn("projectDataError", state_source)
        self.assertIn("projectLoadSequence", state_source)
        self.assertIn('"Carregando takes..."', sync_source)
        self.assertIn("projectDataLoading || Boolean(projectDataError)", sync_source)
        self.assertIn("state.films.projectLoadSequence !== loadSequence", load_source)
        self.assertIn("syncFilmBatchActions();", load_source)

    def test_studio_startup_uses_the_instantiated_anchor_manager(self):
        backend = (Path(__file__).resolve().parent / "main.py").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "target=_ANCHOR_EXECUTOR_MANAGER.resume_authorized",
            backend,
        )

    def test_studio_requests_use_the_authenticated_same_origin_proxy(self):
        self.assertIn('return "/api/studio";', self.source)
        self.assertNotIn("https://api-studio.pemaratech.com.br", self.source)
        self.assertNotIn(":8027", self.source)

    def test_take_player_keeps_its_buffer_and_reports_loading_state(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        backend = (Path(__file__).resolve().parent / "main.py").read_text(
            encoding="utf-8"
        )
        projects = (Path(__file__).resolve().parent / "video_projects.py").read_text(
            encoding="utf-8"
        )
        preview_start = self.source.index("function openFilmTakePreview")
        preview_end = self.source.index("async function loadVideoSoundProviders", preview_start)
        preview_source = self.source[preview_start:preview_end]

        self.assertIn('id="film-preview-video" controls playsinline preload="auto"', html)
        self.assertIn('id="film-preview-buffer-progress"', html)
        self.assertIn("video.dataset.previewUrl !== previewUrl", preview_source)
        self.assertIn("playFilmPreviewWhenReady(video, previewUrl)", preview_source)
        self.assertIn('addEventListener("waiting"', self.source)
        self.assertIn('addEventListener("progress"', self.source)
        self.assertIn('"previewVersion"', projects)
        self.assertIn('"private, max-age=86400, immutable"', backend)
        self.assertIn('response.headers.setdefault("Cache-Control", "no-store")', backend)
        self.assertIn("response.chunk_size = 512 * 1024", backend)

    def test_hybrid_take_modes_and_continuity_are_visible_as_text(self):
        render_start = self.source.index("function renderFilmTakes")
        render_end = self.source.index("function renderFilmPlayerReview", render_start)
        render_source = self.source[render_start:render_end]

        self.assertIn("take.takeMode", render_source)
        self.assertIn("continuityContract", render_source)
        self.assertIn("Precisão", render_source)
        self.assertIn("Ação", render_source)
        self.assertIn("Clímax", render_source)

    def test_approved_sequence_assembly_and_owner_final_review_are_explicit(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="film-assembly-start"', html)
        self.assertIn('id="film-assembly-status"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('id="film-final-approve"', html)
        self.assertIn('id="film-final-reject"', html)
        self.assertIn('id="film-final-rejection-reason"', html)
        self.assertIn("/assembly-jobs", self.source)
        self.assertIn("/final-review", self.source)
        self.assertIn("assemblyReadiness", self.source)
        self.assertIn("PENDING_OWNER_REVIEW", self.source)

    def test_h3_live_preview_is_visible_but_explicitly_opt_in(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )

        preview = html[html.index('id="gen-minimax-live-preview"') :]
        preview_tag = preview.split(">", 1)[0]
        self.assertNotIn("checked", preview_tag)
        self.assertIn("Preview ao vivo do H3", preview)
        self.assertIn("N&atilde;o altera sampler, encoder, passos nem o MP4 final", preview)
        self.assertIn('$("#gen-minimax-live-preview-field")', self.source)
        self.assertIn(
            'fd.append("enable_minimax_h3_live_preview"',
            self.source,
        )

    def test_prompt_and_rejection_fields_expose_local_audio_dictation(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        for field_id in (
            "gen-prompt",
            "gen-negative",
            "film-director-reason",
        ):
            field = html[html.index(f'id="{field_id}"'):]
            self.assertIn("data-voice-input", field.split("></textarea>", 1)[0])
        self.assertIn("data-film-prompt-input", self.source)
        self.assertIn("data-voice-input data-voice-label=\"prompt do take", self.source)

    def test_dictation_ui_is_accessible_private_and_same_origin(self):
        self.assertIn("function enhanceVoiceInputs", self.source)
        self.assertIn('recordButton.type = "button"', self.source)
        self.assertIn('status.setAttribute("role", "status")', self.source)
        self.assertIn('status.setAttribute("aria-live", "polite")', self.source)
        self.assertIn("/api/dictation/transcriptions?language=pt", self.source)
        self.assertIn("O áudio não foi guardado", self.source)
        self.assertIn("DICTATION_MAX_RECORDING_MS = 120000", self.source)

    def test_opening_takes_loads_projects_without_the_hidden_mobile_button(self):
        start = self.source.index("function switchSection")
        end = self.source.index("async function openTool", start)
        function_source = self.source[start:end]

        self.assertIn('if (name === "films") loadFilmProjects();', function_source)

    def test_global_refresh_reloads_projects_while_takes_is_visible(self):
        start = self.source.index("function refreshAll")
        end = self.source.index("function tickClock", start)
        function_source = self.source[start:end]

        self.assertIn(
            'if ($("#section-films")?.classList.contains("active")) loadFilmProjects();',
            function_source,
        )

    def test_take_progress_distinguishes_active_heartbeat_from_a_stall(self):
        start = self.source.index("function formatFilmTakeJobProgress")
        end = self.source.index("async function pollFilmTakeJob", start)
        function_source = self.source[start:end]

        self.assertIn('"motor ativo"', function_source)
        self.assertIn('"sem resposta recente"', function_source)
        self.assertIn("% estimado", function_source)
        self.assertIn("heartbeatAge <= 15", function_source)
        self.assertIn("formatFilmTakeJobProgress(job)", self.source)

    def test_take_error_is_visible_without_reopening_the_command(self):
        self.assertIn('["ERROR", "Erro — veja o motivo"]', self.source)
        self.assertIn('class="film-command-error" role="alert"', self.source)
        self.assertIn("O comando não foi executado", self.source)

    def test_terminal_video_errors_do_not_remain_as_fake_active_progress(self):
        take_start = self.source.index("function filmTakeProgress")
        take_end = self.source.index("function filmProjectProgress", take_start)
        take_source = self.source[take_start:take_end]
        project_start = take_end
        project_end = self.source.index("function syncFilmProjectProgress", project_start)
        project_source = self.source[project_start:project_end]

        self.assertIn('status === "ERROR" && !queueItem', take_source)
        self.assertIn('heading: "Produção interrompida"', take_source)
        self.assertIn('new Set(["READY", "APPROVED", "FINAL"])', project_source)
        self.assertIn('"jobs falharam"', project_source)

    def test_audio_candidates_are_visible_in_human_review_with_a_player(self):
        self.assertIn("audioCandidateNeedsReview", self.source)
        self.assertIn("/audio-candidate", self.source)
        self.assertIn('<audio controls preload="none"', self.source)
        self.assertIn("Áudio candidato — escuta humana obrigatória", self.source)
        review_start = self.source.index("function filmTakeNeedsReview")
        review_end = self.source.index("function filmTakeMatchesView", review_start)
        self.assertIn("take?.audioCandidateNeedsReview", self.source[review_start:review_end])
        self.assertIn("/audio-candidates/", self.source)

    def test_rejected_video_needs_a_new_review_artifact_to_return_to_review(self):
        review_start = self.source.index("function filmTakeNeedsReview")
        review_end = self.source.index("function filmTakeMatchesView", review_start)
        review_source = self.source[review_start:review_end]

        self.assertIn("take?.hasPreview", review_source)
        self.assertIn('=== "READY"', review_source)
        self.assertIn("take?.hasPreanalysisGallery", review_source)
        self.assertNotIn('["READY", "REJECTED"].includes', review_source)

    def test_take_exposes_model_independent_video_to_sound_controls(self):
        self.assertIn("Gerar som pelo v", self.source)
        self.assertIn("/video-sound/providers", self.source)
        self.assertIn("/video-sound-jobs", self.source)
        self.assertIn("videoSoundProviderId", self.source)
        self.assertIn("data-voice-label=\"dire", self.source)
        self.assertIn("Escuta humana obrigat", self.source)

    def test_visual_approval_is_not_blocked_by_pending_audio(self):
        review_start = self.source.index("function renderFilmPlayerReview")
        review_end = self.source.index("function filmPreviewMeta", review_start)
        review_source = self.source[review_start:review_end]

        self.assertIn("take.audioReady", review_source)
        self.assertIn("take.audioHumanReviewRequired", review_source)
        self.assertIn(
            "Imagem aprovada. A faixa de ambiente/efeitos e voz continua pendente",
            review_source,
        )
        self.assertIn(
            "Escute a faixa anexada e confirme novamente para aprovar o audio",
            review_source,
        )
        self.assertIn("audioVariants.map", self.source)

    def test_mova_and_wan_are_absent_from_active_generation(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        backend = (Path(__file__).resolve().parent / "main.py").read_text(encoding="utf-8")
        self.assertNotIn('id="gen-mova-status"', html)
        self.assertNotIn('id="gen-mova-producer"', html)
        self.assertIn('id="gen-prompt"', html)
        self.assertNotIn('model: "MOVA-720p"', self.source)
        self.assertNotIn("MOVA_PERMANENT_NEGATIVE", self.source)
        self.assertIn('DEFAULT_VIDEO_MODEL = MINIMAX_H3_MODEL_NAME', backend)
        self.assertIn('"policy": "removed_by_owner_20260815"', backend)
        self.assertIn('"reserve_engines": []', backend)

    def test_video_authorization_keeps_only_h3(self):
        backend = (Path(__file__).resolve().parent / "main.py").read_text(
            encoding="utf-8"
        )
        start = backend.index("def _video_engine_authorized")
        end = backend.index("def _require_authorized_video_engine", start)
        function_source = backend[start:end]
        self.assertIn("_is_minimax_h3_model(selected)", function_source)
        self.assertNotIn("selected == _LTX25_MODEL_NAME", function_source)
        self.assertNotIn("WAN22_ANIMATE_MODEL_NAME", function_source)
        self.assertNotIn("STUDIO_ENABLE_WAN_RESERVE", function_source)
        self.assertNotIn("MOVA_MODEL_NAME", function_source)

    def test_ltx_profiles_are_absent_from_the_active_generator(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        presets = self.source[
            self.source.index("const GEN_PRESETS"):self.source.index("function serviceState")
        ]
        self.assertNotIn('id="gen-ltx-status"', html)
        self.assertNotIn('value="ltx23_', html)
        self.assertNotIn("LTX-2.3", presets)
        self.assertIn('value="minimax_h3_720p_take_6s"', html)
        self.assertIn('value="minimax_h3_720p_take_10s"', html)
        self.assertIn('model: "minimax_h3_fl2va_pruned_int8_convrot.safetensors"', presets)
        self.assertIn("width: 1280", self.source)
        self.assertIn("height: 720", self.source)
        self.assertIn("frames: 141", presets)
        self.assertIn("frames: 243", presets)
        self.assertIn("steps: 20", presets)

    def test_visible_video_presets_are_h3_only(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('value="mova_', html)
        self.assertNotIn('value="intro_ritmos_60s"', html)
        self.assertNotIn('value="ltx23_', html)
        self.assertIn('value="minimax_h3_720p_take_6s"', html)
        self.assertIn('value="minimax_h3_720p_take_10s"', html)
        self.assertIn("frames: 141", self.source)
        self.assertIn("PENDING_PT_BR_VOICE_REVIEW", self.source)
        self.assertNotIn("Generate native synchronized dialogue", self.source)

    def test_video_timing_only_exposes_duration_and_fps(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        video_fields = html[
            html.index('id="gen-video-fields"'):html.index('id="gen-video-timing-help"')
        ]

        self.assertIn('id="gen-video-duration"', video_fields)
        self.assertIn(
            'id="gen-video-duration" type="number" value="6" min="0.1" max="30" step="any"',
            video_fields,
        )
        self.assertIn('id="gen-fps"', video_fields)
        self.assertIn('id="gen-frames" type="hidden"', video_fields)
        self.assertNotIn("<label>Frames", video_fields)
        self.assertIn('data-gen-duration="5.13">5 s</button>', video_fields)
        self.assertIn('data-gen-duration="15">15 s</button>', video_fields)
        self.assertIn("function syncGenVideoTiming", self.source)
        self.assertIn('fd.append("video_duration"', self.source)
        self.assertIn('label: "grade H3 17k+5"', self.source)
        self.assertIn("if (isH3) fpsField.value = 24", self.source)
        self.assertIn("fpsField.disabled = isH3", self.source)
        self.assertIn("minimax_h3_max_duration || 15", self.source)
        self.assertIn("24 FPS nativos automaticos", self.source)
        self.assertNotIn('label: "grade LTX 2.5 8n+1"', self.source)

    def test_minimax_h3_text_to_video_is_a_dedicated_mode_without_upload(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('data-gen-mode="text_video"', html)
        self.assertIn('value="text_video"', html)
        self.assertIn("Texto para v&iacute;deo", html)
        self.assertIn('const isVideoMode = mode === "video" || mode === "text_video";', self.source)
        self.assertIn('const isTextVideoMode = mode === "text_video";', self.source)
        self.assertIn('state.selectedVideoEngineId', self.source)
        self.assertIn('videoEngineTechnicalModel(engine.id)', self.source)
        self.assertIn('fd.append("engine_id", engineId)', self.source)
        self.assertIn('fd.set("mode", "video")', self.source)
        self.assertIn('fd.append("prompt", textVideoPrompt)', self.source)
        self.assertIn('Escolha MiniMax H3', self.source)

    def test_minimax_h3_native_audio_is_opt_in_and_submitted(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('id="gen-minimax-native-audio-field"', html)
        self.assertIn(
            'id="gen-minimax-native-audio" type="checkbox"',
            html,
        )
        self.assertIn("function syncGenMinimaxAudio", self.source)
        self.assertIn(
            'fd.append("enable_minimax_h3_native_audio",',
            self.source,
        )
        self.assertIn(
            'profile?.audio === false',
            self.source,
        )

    def test_h3_production_is_the_default_profile(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="gen-h3-quality-profile"', html)
        self.assertIn('value="h3_production" selected', html)
        self.assertIn('h3_production: { width: 1088, height: 608, steps: 10', self.source)
        self.assertIn('fd.append("h3_quality_profile"', self.source)

    def test_minimax_h3_workflow_is_visible_and_uses_backend_inventory(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="gen-h3-workflow"', html)
        self.assertIn('id="gen-h3-workflow-stages"', html)
        self.assertIn("function renderGenH3Workflow", self.source)
        self.assertIn("renderGenH3Workflow(data.h3Workflow)", self.source)
        self.assertIn('state.selectedVideoEngineId !== "minimax_h3"', self.source)

    def test_video_engine_selection_has_no_external_anchor_analysis(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="gen-video-engine-picker"', html)
        self.assertIn('id="gen-engine-id"', html)
        self.assertNotIn('id="gen-anchor-intelligence"', html)
        self.assertNotIn('id="gen-anchor-external-consent"', html)
        self.assertIn("function selectVideoEngine", self.source)
        self.assertNotIn("function analyzeAnchorIntelligence", self.source)
        self.assertNotIn("function applyCompiledAnchorPrompt", self.source)
        self.assertNotIn('/api/generative/anchor-intelligence/analyze', self.source)
        self.assertIn('production_ready !== true', self.source)

    def test_generative_job_poll_recovers_from_transient_connection_failure(self):
        start = self.source.index("async function runGen")
        end = self.source.index("function assetDate", start)
        run_gen = self.source[start:end]

        self.assertIn("let pollFailureStartedAt = null", run_gen)
        self.assertIn("pollFailureStartedAt = null", run_gen)
        self.assertIn("now - pollFailureStartedAt >= 90000", run_gen)
        self.assertIn("Conexao oscilou; reconectando automaticamente", run_gen)
        self.assertIn("continua em Trabalhos recentes", run_gen)
        self.assertIn(
            'if ($("#section-gen")?.classList.contains("active")) loadGenJobs();',
            self.source,
        )

    def test_full_movie_has_a_dedicated_player_and_master_download(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="film-final-output"', html)
        self.assertIn('id="film-final-watch"', html)
        self.assertIn('id="film-final-download"', html)
        self.assertIn('id="film-final-video"', html)
        self.assertIn('id="film-final-player-status"', html)
        self.assertIn("function renderFilmFinalOutput", self.source)
        self.assertIn("function openFilmFinalPreview", self.source)
        self.assertIn("function markFilmFinalPlaybackVisible", self.source)
        self.assertIn("/final-preview", self.source)
        self.assertIn("download=true", self.source)
        self.assertIn(
            'encodeURIComponent(output.reviewFile || output.sha256 || output.masterFile || "final")',
            self.source,
        )
        self.assertIn('video.offsetParent === null', self.source)
        self.assertIn('$("#film-final-video")?.addEventListener("playing"', self.source)
        self.assertIn('stickyActions.getBoundingClientRect().height + 24', self.source)

    def test_levo2_music_pilot_is_accessible_and_never_auto_approved(self):
        html = (Path(__file__).resolve().parents[2] / "app" / "index.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('value="levo2_local"', html)
        self.assertIn('data-gen-mode="music"', html)
        self.assertIn('data-gen-mode="sfx"', html)
        self.assertIn('id="gen-provider-help" role="status" aria-live="polite"', html)
        self.assertIn('aria-describedby="gen-provider-help"', html)
        self.assertIn("function syncGenAudioProviderOptions", self.source)
        self.assertIn('providerId === "levo2_local" ? "Gerar piloto neural"', self.source)
        self.assertIn("nenhuma aprova&ccedil;&atilde;o &eacute; autom&aacute;tica", self.source)
        self.assertIn("Baixar &aacute;udio", self.source)


if __name__ == "__main__":
    unittest.main()
