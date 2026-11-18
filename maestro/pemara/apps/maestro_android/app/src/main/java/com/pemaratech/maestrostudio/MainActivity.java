package com.pemaratech.maestrostudio;

import android.annotation.SuppressLint;
import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.SystemClock;
import android.provider.MediaStore;
import android.provider.Settings;
import android.content.pm.PackageManager;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.window.OnBackInvokedDispatcher;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.GeolocationPermissions;
import android.webkit.HttpAuthHandler;
import android.webkit.PermissionRequest;
import android.webkit.SafeBrowsingResponse;
import android.webkit.SslErrorHandler;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.net.ssl.HttpsURLConnection;

public final class MainActivity extends Activity {
    private static final String APP_VERSION = "1.0.0-beta.10";
    private static final String HOME_URL =
            "https://maestro.pemaratech.com.br/?app=android&version=" + APP_VERSION;
    private static final String OPENCODE_URL =
            "https://pc-geral-thiago-1.tail14cf8c.ts.net/";
    private static final String OPENCODE_HOST =
            "pc-geral-thiago-1.tail14cf8c.ts.net";
    private static final String COMFYUI_URL =
            "https://pc-geral-thiago-1.tail14cf8c.ts.net:10000/";
    private static final String RELEASE_QWEN_URL =
            "https://pc-geral-thiago-1.tail14cf8c.ts.net:10443/api/actions/release-qwen";
    private static final String QWEN_STATUS_URL =
            "https://pc-geral-thiago-1.tail14cf8c.ts.net:10443/api/status";
    private static final String RELEASE_QWEN_ACTION = "release-qwen-v1";
    private static final String UNIFY_PASSWORD_URL =
            "https://pc-geral-thiago-1.tail14cf8c.ts.net:10443"
                    + "/api/actions/unify-opencode-password";
    private static final String UNIFY_PASSWORD_ACTION = "unify-opencode-password-v1";
    private static final int REQUEST_FILE_CHOOSER = 4101;
    private static final int REQUEST_DOWNLOAD_DESTINATION = 4102;
    private static final int REQUEST_RECORD_AUDIO = 4103;
    private static final String STATE_WEBVIEW = "maestro_webview_state";
    private static final String STATE_SAVED_AT = "maestro_webview_saved_at";
    private static final String PREFERENCES = "maestro_native_state";
    private static final String PREFERENCE_WEB_CACHE_BUILD = "web_cache_build";
    private static final String PREFERENCE_MICROPHONE_REQUESTED = "microphone_requested";

    private WebView webView;
    private ProgressBar pageProgress;
    private LinearLayout statePanel;
    private ProgressBar stateSpinner;
    private TextView stateTitle;
    private TextView stateMessage;
    private Button retryButton;
    private Button maestroNavigationButton;
    private Button openCodeNavigationButton;
    private Button comfyNavigationButton;
    private Button releaseGpuButton;
    private ValueCallback<Uri[]> fileCallback;
    private Uri pendingCameraUri;
    private File pendingCameraFile;
    private PendingDownload pendingDownload;
    private PermissionRequest pendingAudioPermissionRequest;
    private AlertDialog microphonePermissionDialog;
    private AlertDialog openCodeLoginDialog;
    private OpenCodeCredentialVault openCodeCredentialVault;
    private boolean openCodeAuthAttempted;
    private String pendingOpenCodePassword;
    private boolean mainFrameError;
    private boolean loadedOnce;
    private boolean firstResume = true;
    private boolean destroying;
    private boolean audioPermissionRequestInFlight;
    private boolean awaitingMicrophoneSettings;
    private long backgroundedAt;
    private String lastRequestedUrl = HOME_URL;
    private final ExecutorService downloadExecutor = Executors.newSingleThreadExecutor();
    private final ExecutorService controlExecutor = Executors.newSingleThreadExecutor();
    private BlobDownloadBridge blobBridge;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        openCodeCredentialVault = new OpenCodeCredentialVault(this);
        buildInterface();
        configureWebView();
        boolean appBuildChanged = invalidateWebCacheAfterAppUpdate();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                    this::handleBackNavigation
            );
        }

        Bundle webState = savedInstanceState == null ? null : savedInstanceState.getBundle(STATE_WEBVIEW);
        long savedAt = savedInstanceState == null ? 0L : savedInstanceState.getLong(STATE_SAVED_AT, 0L);
        boolean canRestore = webState != null
                && WebAppRefreshPolicy.shouldRestoreSavedState(
                        appBuildChanged,
                        savedAt,
                        System.currentTimeMillis()
                );
        if (!canRestore || webView.restoreState(webState) == null) {
            loadFreshHome();
        } else {
            String restoredUrl = webView.getUrl();
            if (TrustedUrlPolicy.isTrustedHttps(restoredUrl)) {
                lastRequestedUrl = restoredUrl;
                updateNavigationSelection(restoredUrl);
            }
        }
    }

    private boolean invalidateWebCacheAfterAppUpdate() {
        String previousBuild = getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .getString(PREFERENCE_WEB_CACHE_BUILD, "");
        if (APP_VERSION.equals(previousBuild)) {
            return false;
        }
        webView.clearCache(true);
        webView.clearHistory();
        getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .edit()
                .putString(PREFERENCE_WEB_CACHE_BUILD, APP_VERSION)
                .apply();
        return true;
    }

    private void loadFreshHome() {
        lastRequestedUrl = HOME_URL;
        showLoading();
        webView.loadUrl(HOME_URL + "&refresh=" + System.currentTimeMillis());
    }

    private void buildInterface() {
        LinearLayout appShell = new LinearLayout(this);
        appShell.setOrientation(LinearLayout.VERTICAL);
        appShell.setBackgroundColor(Color.rgb(244, 248, 252));
        appShell.setFitsSystemWindows(true);

        FrameLayout browserFrame = new FrameLayout(this);
        browserFrame.setBackgroundColor(Color.rgb(244, 248, 252));
        appShell.addView(browserFrame, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1f
        ));

        webView = new WebView(this);
        webView.setContentDescription(getString(R.string.webview_description));
        browserFrame.addView(webView, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        pageProgress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        pageProgress.setMax(100);
        pageProgress.setProgressTintList(android.content.res.ColorStateList.valueOf(
                Color.rgb(242, 138, 46)
        ));
        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(3)
        );
        progressParams.gravity = Gravity.TOP;
        browserFrame.addView(pageProgress, progressParams);

        statePanel = new LinearLayout(this);
        statePanel.setOrientation(LinearLayout.VERTICAL);
        statePanel.setGravity(Gravity.CENTER);
        statePanel.setPadding(dp(32), dp(32), dp(32), dp(32));
        statePanel.setBackgroundColor(Color.rgb(244, 248, 252));

        TextView brand = new TextView(this);
        brand.setText(R.string.brand_name);
        brand.setTextColor(Color.rgb(6, 102, 179));
        brand.setTextSize(28);
        brand.setTypeface(Typeface.create("sans", Typeface.BOLD));
        brand.setLetterSpacing(0.08f);
        statePanel.addView(brand, wrapCentered(dp(8)));

        TextView product = new TextView(this);
        product.setText(R.string.product_name);
        product.setTextColor(Color.rgb(7, 26, 47));
        product.setTextSize(13);
        product.setTypeface(Typeface.create("sans", Typeface.BOLD));
        product.setLetterSpacing(0.18f);
        statePanel.addView(product, wrapCentered(dp(30)));

        stateSpinner = new ProgressBar(this);
        stateSpinner.setIndeterminateTintList(android.content.res.ColorStateList.valueOf(
                Color.rgb(242, 138, 46)
        ));
        statePanel.addView(stateSpinner, wrapCentered(dp(24)));

        stateTitle = new TextView(this);
        stateTitle.setGravity(Gravity.CENTER);
        stateTitle.setTextColor(Color.rgb(7, 26, 47));
        stateTitle.setTextSize(21);
        stateTitle.setTypeface(Typeface.create("sans", Typeface.BOLD));
        statePanel.addView(stateTitle, wrapCentered(dp(10)));

        stateMessage = new TextView(this);
        stateMessage.setGravity(Gravity.CENTER);
        stateMessage.setTextColor(Color.rgb(63, 78, 94));
        stateMessage.setTextSize(15);
        stateMessage.setLineSpacing(0f, 1.15f);
        statePanel.addView(stateMessage, wrapCentered(dp(22)));

        retryButton = new Button(this);
        retryButton.setText(R.string.retry);
        retryButton.setAllCaps(false);
        retryButton.setTextColor(Color.WHITE);
        retryButton.setTextSize(15);
        retryButton.setTypeface(Typeface.create("sans", Typeface.BOLD));
        GradientDrawable buttonBackground = new GradientDrawable();
        buttonBackground.setColor(Color.rgb(6, 102, 179));
        buttonBackground.setCornerRadius(dp(12));
        retryButton.setBackground(buttonBackground);
        retryButton.setMinHeight(dp(48));
        retryButton.setPadding(dp(24), 0, dp(24), 0);
        retryButton.setOnClickListener(view -> retryCurrentDestination());
        statePanel.addView(retryButton, wrapCentered(0));

        browserFrame.addView(statePanel, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        appShell.addView(buildNavigationBar(), new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(62)
        ));
        setContentView(appShell);
    }

    private LinearLayout buildNavigationBar() {
        LinearLayout navigation = new LinearLayout(this);
        navigation.setOrientation(LinearLayout.HORIZONTAL);
        navigation.setGravity(Gravity.CENTER);
        navigation.setPadding(dp(4), dp(4), dp(4), dp(4));
        navigation.setBackgroundColor(Color.rgb(7, 26, 47));

        maestroNavigationButton = createNavigationButton(R.string.navigation_maestro);
        maestroNavigationButton.setOnClickListener(view -> loadFreshHome());
        navigation.addView(maestroNavigationButton);

        openCodeNavigationButton = createNavigationButton(R.string.navigation_opencode);
        openCodeNavigationButton.setOnClickListener(view -> loadPrivateService(OPENCODE_URL));
        navigation.addView(openCodeNavigationButton);

        comfyNavigationButton = createNavigationButton(R.string.navigation_comfyui);
        comfyNavigationButton.setOnClickListener(view -> loadPrivateService(COMFYUI_URL));
        navigation.addView(comfyNavigationButton);

        releaseGpuButton = createNavigationButton(R.string.navigation_release_gpu);
        releaseGpuButton.setTextColor(Color.rgb(255, 186, 113));
        releaseGpuButton.setTypeface(Typeface.create("sans", Typeface.BOLD));
        releaseGpuButton.setOnClickListener(view -> confirmReleaseQwen());
        navigation.addView(releaseGpuButton);

        updateNavigationSelection(HOME_URL);
        return navigation;
    }

    private Button createNavigationButton(int textResource) {
        Button button = new Button(this);
        button.setText(textResource);
        button.setAllCaps(false);
        button.setTextSize(12);
        button.setMinHeight(dp(48));
        button.setPadding(dp(6), 0, dp(6), 0);
        button.setBackgroundColor(Color.TRANSPARENT);
        button.setLayoutParams(new LinearLayout.LayoutParams(
                0,
                ViewGroup.LayoutParams.MATCH_PARENT,
                1f
        ));
        return button;
    }

    private void loadPrivateService(String url) {
        if (TrustedUrlPolicy.isOpenCodeUrl(url)) {
            openCodeAuthAttempted = false;
        }
        lastRequestedUrl = url;
        showLoading();
        webView.loadUrl(url);
    }

    private void retryCurrentDestination() {
        if (TrustedUrlPolicy.isMainHost(lastRequestedUrl)) {
            loadFreshHome();
        } else if (TrustedUrlPolicy.isTrustedHttps(lastRequestedUrl)) {
            loadPrivateService(lastRequestedUrl);
        } else {
            loadFreshHome();
        }
    }

    private void updateNavigationSelection(String url) {
        styleNavigationButton(maestroNavigationButton, TrustedUrlPolicy.isMainHost(url));
        styleNavigationButton(openCodeNavigationButton, TrustedUrlPolicy.isOpenCodeUrl(url));
        styleNavigationButton(comfyNavigationButton, url != null && url.startsWith(COMFYUI_URL));
    }

    private void styleNavigationButton(Button button, boolean selected) {
        if (button == null) {
            return;
        }
        button.setTextColor(selected ? Color.rgb(242, 138, 46) : Color.WHITE);
        button.setTypeface(Typeface.create("sans", selected ? Typeface.BOLD : Typeface.NORMAL));
    }

    private void confirmReleaseQwen() {
        releaseGpuButton.setEnabled(false);
        releaseGpuButton.setText(R.string.checking_qwen);
        controlExecutor.execute(() -> {
            QwenRuntimeStatus runtime = requestQwenRuntimeStatus();
            runOnUiThread(() -> {
                if (destroying) {
                    return;
                }
                releaseGpuButton.setEnabled(true);
                releaseGpuButton.setText(R.string.navigation_release_gpu);
                handleQwenRuntimeDecision(runtime);
            });
        });
    }

    private void handleQwenRuntimeDecision(QwenRuntimeStatus runtime) {
        QwenReleasePolicy.Decision decision =
                QwenReleasePolicy.decide(runtime.state, runtime.canRelease);
        if (decision == QwenReleasePolicy.Decision.RELEASE_ALLOWED) {
            showReleaseConfirmation();
            return;
        }
        if (decision == QwenReleasePolicy.Decision.ALREADY_FREE) {
            Toast.makeText(this, R.string.qwen_gpu_already_free, Toast.LENGTH_LONG).show();
            loadPrivateService(COMFYUI_URL);
            return;
        }

        int title = decision == QwenReleasePolicy.Decision.ACTIVE
                ? R.string.qwen_active_title
                : R.string.qwen_release_blocked_title;
        String message = runtime.describe();
        if (decision == QwenReleasePolicy.Decision.ACTIVE) {
            message += "\n\n" + getString(R.string.qwen_active_protection);
        }
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setMessage(message)
                .setPositiveButton(android.R.string.ok, null)
                .show();
    }

    private void showReleaseConfirmation() {
        new AlertDialog.Builder(this)
                .setTitle(R.string.release_gpu_title)
                .setMessage(R.string.release_gpu_message)
                .setPositiveButton(R.string.release_gpu_confirm, (dialog, which) -> releaseQwen())
                .setNegativeButton(R.string.cancel, null)
                .show();
    }

    private void releaseQwen() {
        releaseGpuButton.setEnabled(false);
        releaseGpuButton.setText(R.string.releasing_gpu);
        controlExecutor.execute(() -> {
            QwenReleaseResult result = requestQwenRelease();
            runOnUiThread(() -> {
                if (isFinishing() || (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1
                        && isDestroyed())) {
                    return;
                }
                releaseGpuButton.setEnabled(true);
                releaseGpuButton.setText(R.string.navigation_release_gpu);
                if (result.ok) {
                    Toast.makeText(this, result.message, Toast.LENGTH_LONG).show();
                    if (result.gpuFree) {
                        loadPrivateService(COMFYUI_URL);
                    } else {
                        loadFreshHome();
                    }
                } else {
                    new AlertDialog.Builder(this)
                            .setTitle(R.string.qwen_release_blocked_title)
                            .setMessage(result.message)
                            .setPositiveButton(android.R.string.ok, null)
                            .show();
                }
            });
        });
    }

    private QwenRuntimeStatus requestQwenRuntimeStatus() {
        HttpsURLConnection connection = null;
        try {
            connection = (HttpsURLConnection) new URL(QWEN_STATUS_URL).openConnection();
            connection.setRequestMethod("GET");
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(15000);
            connection.setUseCaches(false);
            connection.setRequestProperty("Accept", "application/json");
            int responseCode = connection.getResponseCode();
            if (responseCode != 200) {
                return QwenRuntimeStatus.unknown();
            }
            return QwenRuntimeStatus.fromPayload(readJsonResponse(connection, responseCode));
        } catch (Exception ignored) {
            return QwenRuntimeStatus.unknown();
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private QwenReleaseResult requestQwenRelease() {
        HttpsURLConnection connection = null;
        try {
            connection = (HttpsURLConnection) new URL(RELEASE_QWEN_URL).openConnection();
            connection.setRequestMethod("POST");
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(35000);
            connection.setUseCaches(false);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("X-Pemara-Action", RELEASE_QWEN_ACTION);
            int responseCode = connection.getResponseCode();
            JSONObject payload = readJsonResponse(connection, responseCode);
            boolean ok = responseCode == 200 && payload.optBoolean("ok", false);
            String message = payload.optString(
                    ok ? "message" : "error",
                    getString(ok ? R.string.release_gpu_success : R.string.release_gpu_failed)
            );
            QwenRuntimeStatus runtime =
                    QwenRuntimeStatus.fromPayload(payload.optJSONObject("status"));
            boolean gpuFree = QwenReleasePolicy.decide(runtime.state, runtime.canRelease)
                    == QwenReleasePolicy.Decision.ALREADY_FREE;
            return new QwenReleaseResult(ok, gpuFree, message);
        } catch (Exception ignored) {
            return new QwenReleaseResult(
                    false,
                    false,
                    getString(R.string.release_gpu_failed)
            );
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static JSONObject readJsonResponse(
            HttpsURLConnection connection,
            int responseCode
    ) throws Exception {
        InputStream stream = responseCode >= 400
                ? connection.getErrorStream()
                : connection.getInputStream();
        if (stream == null) {
            return new JSONObject();
        }
        try (InputStream input = stream;
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int total = 0;
            int read;
            while ((read = input.read(buffer)) != -1) {
                total += read;
                if (total > 256 * 1024) {
                    throw new IOException("Resposta de controle excedeu o limite.");
                }
                output.write(buffer, 0, read);
            }
            return new JSONObject(output.toString(StandardCharsets.UTF_8.name()));
        }
    }

    private static final class QwenRuntimeStatus {
        final String state;
        final String label;
        final String summary;
        final String task;
        final String directory;
        final boolean canRelease;

        QwenRuntimeStatus(
                String state,
                String label,
                String summary,
                String task,
                String directory,
                boolean canRelease
        ) {
            this.state = state;
            this.label = label;
            this.summary = summary;
            this.task = task;
            this.directory = directory;
            this.canRelease = canRelease;
        }

        static QwenRuntimeStatus fromPayload(JSONObject payload) {
            JSONObject qwen = payload == null ? null : payload.optJSONObject("qwen");
            if (qwen == null) {
                return unknown();
            }
            String task = "";
            String directory = "";
            org.json.JSONArray activeWork = qwen.optJSONArray("activeWork");
            if (activeWork != null && activeWork.length() > 0) {
                JSONObject first = activeWork.optJSONObject(0);
                if (first != null) {
                    task = first.optString("title", "");
                    directory = first.optString("directory", "");
                }
            }
            return new QwenRuntimeStatus(
                    qwen.optString("state", "unknown"),
                    qwen.optString("stateLabel", "ESTADO NÃO CONFIRMADO"),
                    qwen.optString(
                            "summary",
                            "Não foi possível confirmar o estado do Qwen."
                    ),
                    task,
                    directory,
                    qwen.optBoolean("canRelease", false)
            );
        }

        static QwenRuntimeStatus unknown() {
            return new QwenRuntimeStatus(
                    "unknown",
                    "ESTADO NÃO CONFIRMADO",
                    "Não foi possível consultar o OpenCode e o Ollama. "
                            + "Confirme o Tailscale e tente novamente.",
                    "",
                    "",
                    false
            );
        }

        String describe() {
            StringBuilder message = new StringBuilder();
            if (!label.isEmpty()) {
                message.append(label).append("\n\n");
            }
            message.append(summary);
            if (!task.isEmpty() || !directory.isEmpty()) {
                message.append("\n\nOnde:");
                if (!task.isEmpty()) {
                    message.append("\n").append(task);
                }
                if (!directory.isEmpty()) {
                    message.append("\n").append(directory);
                }
            }
            return message.toString();
        }
    }

    private static final class QwenReleaseResult {
        final boolean ok;
        final boolean gpuFree;
        final String message;

        QwenReleaseResult(boolean ok, boolean gpuFree, String message) {
            this.ok = ok;
            this.gpuFree = gpuFree;
            this.message = message;
        }
    }

    private LinearLayout.LayoutParams wrapCentered(int bottomMargin) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        params.gravity = Gravity.CENTER_HORIZONTAL;
        params.bottomMargin = bottomMargin;
        return params;
    }

    @SuppressLint({"SetJavaScriptEnabled", "JavascriptInterface"})
    private void configureWebView() {
        WebView.setWebContentsDebuggingEnabled(false);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(false);
        settings.setAllowUniversalAccessFromFileURLs(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSafeBrowsingEnabled(true);
        settings.setSupportMultipleWindows(false);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(false);
        settings.setTextZoom(100);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setUserAgentString(
                settings.getUserAgentString() + " MaestroStudioAndroid/" + APP_VERSION
        );

        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        cookies.setAcceptThirdPartyCookies(webView, false);

        blobBridge = new BlobDownloadBridge(getApplicationContext(), new BlobDownloadBridge.Listener() {
            @Override
            public void onBlobFinished() {
                Toast.makeText(MainActivity.this, R.string.download_finished, Toast.LENGTH_LONG).show();
                pendingDownload = null;
            }

            @Override
            public void onBlobFailed() {
                Toast.makeText(MainActivity.this, R.string.download_failed, Toast.LENGTH_LONG).show();
                pendingDownload = null;
            }
        });
        webView.addJavascriptInterface(blobBridge, "MaestroNativeBlob");
        webView.setWebViewClient(new StudioWebViewClient());
        webView.setWebChromeClient(new StudioWebChromeClient());
        webView.setDownloadListener(new StudioDownloadListener());
    }

    private void showLoading() {
        mainFrameError = false;
        stateSpinner.setVisibility(View.VISIBLE);
        stateTitle.setText(R.string.loading);
        stateMessage.setText("");
        retryButton.setVisibility(View.GONE);
        statePanel.setVisibility(View.VISIBLE);
        pageProgress.setVisibility(View.VISIBLE);
    }

    private void showError() {
        mainFrameError = true;
        stateSpinner.setVisibility(View.GONE);
        stateTitle.setText(R.string.offline_title);
        boolean privateService = TrustedUrlPolicy.isOpenCodeUrl(lastRequestedUrl)
                || (lastRequestedUrl != null && lastRequestedUrl.startsWith(COMFYUI_URL));
        stateMessage.setText(privateService
                ? R.string.private_service_offline_message
                : R.string.offline_message);
        retryButton.setVisibility(View.VISIBLE);
        statePanel.setVisibility(View.VISIBLE);
        pageProgress.setVisibility(View.GONE);
    }

    private void showContent() {
        statePanel.setVisibility(View.GONE);
        pageProgress.setVisibility(View.GONE);
        loadedOnce = true;
    }

    private void openExternal(Uri uri) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (ActivityNotFoundException ignored) {
            Toast.makeText(this, R.string.download_blocked, Toast.LENGTH_SHORT).show();
        }
    }

    private void showOpenCodeLogin(HttpAuthHandler handler) {
        if (isFinishing() || (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1
                && isDestroyed())) {
            handler.cancel();
            return;
        }
        if (openCodeLoginDialog != null && openCodeLoginDialog.isShowing()) {
            handler.cancel();
            return;
        }

        EditText password = new EditText(this);
        password.setHint(R.string.opencode_password_hint);
        password.setSingleLine(true);
        password.setInputType(
                InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
        );

        FrameLayout fieldContainer = new FrameLayout(this);
        fieldContainer.setPadding(dp(24), 0, dp(24), 0);
        fieldContainer.addView(password, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        boolean[] answered = {false};
        openCodeLoginDialog = new AlertDialog.Builder(this)
                .setTitle(R.string.opencode_login_title)
                .setMessage(R.string.opencode_login_message)
                .setView(fieldContainer)
                .setPositiveButton(R.string.enter, null)
                .setNegativeButton(R.string.cancel, null)
                .create();
        openCodeLoginDialog.setOnShowListener(dialog -> {
            openCodeLoginDialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
                String suppliedPassword = password.getText().toString();
                if (suppliedPassword.isEmpty()) {
                    password.setError(getString(R.string.opencode_password_required));
                    return;
                }
                configureUnifiedOpenCodePassword(
                        handler,
                        password,
                        suppliedPassword,
                        answered
                );
            });
            password.requestFocus();
        });
        openCodeLoginDialog.setOnDismissListener(dialog -> {
            if (!answered[0]) {
                handler.cancel();
                if (!destroying) {
                    webView.post(this::loadFreshHome);
                }
            }
            openCodeLoginDialog = null;
        });
        openCodeLoginDialog.show();
    }

    private void configureUnifiedOpenCodePassword(
            HttpAuthHandler handler,
            EditText passwordField,
            String suppliedPassword,
            boolean[] answered
    ) {
        AlertDialog dialog = openCodeLoginDialog;
        if (dialog == null) {
            handler.cancel();
            return;
        }
        Button enterButton = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
        Button cancelButton = dialog.getButton(AlertDialog.BUTTON_NEGATIVE);
        enterButton.setEnabled(false);
        enterButton.setText(R.string.configuring_opencode);
        cancelButton.setEnabled(false);
        passwordField.setEnabled(false);
        dialog.setCancelable(false);

        controlExecutor.execute(() -> {
            int status = requestOpenCodePasswordUnification(suppliedPassword);
            runOnUiThread(() -> {
                if (destroying || openCodeLoginDialog != dialog) {
                    return;
                }
                if (status == 200) {
                    boolean saved = openCodeCredentialVault.savePassword(suppliedPassword);
                    if (!saved) {
                        pendingOpenCodePassword = suppliedPassword;
                    }
                    answered[0] = true;
                    handler.cancel();
                    passwordField.getText().clear();
                    dialog.dismiss();
                    Toast.makeText(
                            this,
                            saved
                                    ? R.string.opencode_password_configured
                                    : R.string.opencode_password_not_saved,
                            Toast.LENGTH_LONG
                    ).show();
                    loadPrivateService(OPENCODE_URL);
                    return;
                }

                enterButton.setEnabled(true);
                enterButton.setText(R.string.enter);
                cancelButton.setEnabled(true);
                passwordField.setEnabled(true);
                dialog.setCancelable(true);
                int errorMessage = status == 401
                        ? R.string.opencode_maestro_password_invalid
                        : status == 429
                                ? R.string.opencode_password_rate_limited
                                : R.string.opencode_password_configuration_failed;
                passwordField.setError(getString(errorMessage));
                passwordField.requestFocus();
            });
        });
    }

    private int requestOpenCodePasswordUnification(String password) {
        HttpsURLConnection connection = null;
        try {
            byte[] body = new JSONObject()
                    .put("password", password)
                    .toString()
                    .getBytes(StandardCharsets.UTF_8);
            connection = (HttpsURLConnection) new URL(UNIFY_PASSWORD_URL).openConnection();
            connection.setRequestMethod("POST");
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(120000);
            connection.setUseCaches(false);
            connection.setDoOutput(true);
            connection.setFixedLengthStreamingMode(body.length);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("X-Pemara-Action", UNIFY_PASSWORD_ACTION);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            } finally {
                java.util.Arrays.fill(body, (byte) 0);
            }
            return connection.getResponseCode();
        } catch (Exception ignored) {
            return -1;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private boolean handleNavigation(String rawUrl) {
        if (TrustedUrlPolicy.isTrustedHttps(rawUrl)) {
            return false;
        }
        Uri uri = Uri.parse(rawUrl);
        String scheme = uri.getScheme();
        if ("https".equalsIgnoreCase(scheme)
                || "mailto".equalsIgnoreCase(scheme)
                || "tel".equalsIgnoreCase(scheme)) {
            openExternal(uri);
        }
        return true;
    }

    private final class StudioWebViewClient extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            return handleNavigation(request.getUrl().toString());
        }

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, String url) {
            return handleNavigation(url);
        }

        @Override
        public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
            mainFrameError = false;
            lastRequestedUrl = url;
            updateNavigationSelection(url);
            pageProgress.setVisibility(View.VISIBLE);
            if (!loadedOnce) {
                showLoading();
            }
        }

        @Override
        public void onPageFinished(WebView view, String url) {
            CookieManager.getInstance().flush();
            if (!mainFrameError && TrustedUrlPolicy.isTrustedHttps(url)) {
                showContent();
            }
        }

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
            if (request.isForMainFrame()) {
                showError();
            }
        }

        @Override
        public void onReceivedHttpError(
                WebView view,
                WebResourceRequest request,
                WebResourceResponse errorResponse
        ) {
            if (request.isForMainFrame() && errorResponse.getStatusCode() >= 500) {
                showError();
            }
        }

        @Override
        public void onReceivedHttpAuthRequest(
                WebView view,
                HttpAuthHandler handler,
                String host,
                String realm
        ) {
            if (!OPENCODE_HOST.equalsIgnoreCase(host)
                    || !TrustedUrlPolicy.isOpenCodeUrl(view.getUrl())) {
                handler.cancel();
                return;
            }
            if (!openCodeAuthAttempted) {
                String savedPassword = pendingOpenCodePassword;
                pendingOpenCodePassword = null;
                if (savedPassword == null) {
                    savedPassword = openCodeCredentialVault.loadPassword();
                }
                if (savedPassword != null && !savedPassword.isEmpty()) {
                    openCodeAuthAttempted = true;
                    handler.proceed("opencode", savedPassword);
                    savedPassword = null;
                    return;
                }
            } else {
                openCodeCredentialVault.clear();
            }
            showOpenCodeLogin(handler);
        }

        @Override
        public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
            handler.cancel();
            showError();
        }

        @Override
        public void onSafeBrowsingHit(
                WebView view,
                WebResourceRequest request,
                int threatType,
                SafeBrowsingResponse callback
        ) {
            callback.backToSafety(true);
        }
    }

    private final class StudioWebChromeClient extends WebChromeClient {
        @Override
        public void onProgressChanged(WebView view, int newProgress) {
            pageProgress.setProgress(newProgress);
            if (newProgress >= 100 && statePanel.getVisibility() != View.VISIBLE) {
                pageProgress.setVisibility(View.GONE);
            }
        }

        @Override
        public boolean onShowFileChooser(
                WebView webView,
                ValueCallback<Uri[]> callback,
                FileChooserParams params
        ) {
            if (fileCallback != null) {
                fileCallback.onReceiveValue(null);
            }
            fileCallback = callback;
            launchFileChooser(params);
            return true;
        }

        @Override
        public void onPermissionRequest(PermissionRequest request) {
            runOnUiThread(() -> handleWebPermissionRequest(request));
        }

        @Override
        public void onPermissionRequestCanceled(PermissionRequest request) {
            runOnUiThread(() -> {
                if (pendingAudioPermissionRequest == request) {
                    pendingAudioPermissionRequest = null;
                    awaitingMicrophoneSettings = false;
                    dismissMicrophonePermissionDialog();
                }
            });
        }

        @Override
        public void onGeolocationPermissionsShowPrompt(
                String origin,
                GeolocationPermissions.Callback callback
        ) {
            callback.invoke(origin, false, false);
        }
    }

    private void handleWebPermissionRequest(PermissionRequest request) {
        if (destroying || !WebAudioPermissionPolicy.canGrant(
                String.valueOf(request.getOrigin()),
                request.getResources()
        )) {
            request.deny();
            return;
        }
        if (pendingAudioPermissionRequest != null && pendingAudioPermissionRequest != request) {
            pendingAudioPermissionRequest.deny();
            dismissMicrophonePermissionDialog();
        }
        pendingAudioPermissionRequest = request;
        handleMicrophonePermissionAction();
    }

    private void handleMicrophonePermissionAction() {
        MicrophonePermissionPolicy.Action action = MicrophonePermissionPolicy.decide(
                hasMicrophonePermission(),
                wasMicrophonePermissionRequested(),
                shouldShowRequestPermissionRationale(Manifest.permission.RECORD_AUDIO)
        );
        switch (action) {
            case GRANT_WEB_REQUEST:
                resolveAudioPermissionRequest(true);
                break;
            case REQUEST_ANDROID_PERMISSION:
                requestAndroidMicrophonePermission();
                break;
            case EXPLAIN_AND_RETRY:
                showMicrophoneRationale();
                break;
            case OPEN_APP_SETTINGS:
                showMicrophoneSettingsRecovery();
                break;
        }
    }

    private boolean hasMicrophonePermission() {
        return checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                == PackageManager.PERMISSION_GRANTED;
    }

    private boolean wasMicrophonePermissionRequested() {
        return getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .getBoolean(PREFERENCE_MICROPHONE_REQUESTED, false);
    }

    private void requestAndroidMicrophonePermission() {
        if (destroying || pendingAudioPermissionRequest == null || audioPermissionRequestInFlight) {
            return;
        }
        getSharedPreferences(PREFERENCES, MODE_PRIVATE)
                .edit()
                .putBoolean(PREFERENCE_MICROPHONE_REQUESTED, true)
                .apply();
        audioPermissionRequestInFlight = true;
        requestPermissions(
                new String[]{Manifest.permission.RECORD_AUDIO},
                REQUEST_RECORD_AUDIO
        );
    }

    private void showMicrophoneRationale() {
        if (destroying || pendingAudioPermissionRequest == null) {
            return;
        }
        dismissMicrophonePermissionDialog();
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle(R.string.microphone_permission_title)
                .setMessage(R.string.microphone_permission_rationale)
                .setPositiveButton(
                        R.string.microphone_try_again,
                        (ignored, which) -> requestAndroidMicrophonePermission()
                )
                .setNegativeButton(
                        R.string.microphone_use_upload,
                        (ignored, which) -> resolveAudioPermissionRequest(false)
                )
                .create();
        microphonePermissionDialog = dialog;
        dialog.setOnCancelListener(ignored -> resolveAudioPermissionRequest(false));
        dialog.setOnDismissListener(ignored -> {
            if (microphonePermissionDialog == dialog) {
                microphonePermissionDialog = null;
            }
        });
        dialog.show();
    }

    private void showMicrophoneSettingsRecovery() {
        if (destroying || pendingAudioPermissionRequest == null) {
            return;
        }
        dismissMicrophonePermissionDialog();
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle(R.string.microphone_permission_blocked_title)
                .setMessage(R.string.microphone_permission_blocked_message)
                .setPositiveButton(
                        R.string.microphone_open_settings,
                        (ignored, which) -> openMicrophoneSettings()
                )
                .setNegativeButton(
                        R.string.microphone_use_upload,
                        (ignored, which) -> resolveAudioPermissionRequest(false)
                )
                .create();
        microphonePermissionDialog = dialog;
        dialog.setOnCancelListener(ignored -> resolveAudioPermissionRequest(false));
        dialog.setOnDismissListener(ignored -> {
            if (microphonePermissionDialog == dialog) {
                microphonePermissionDialog = null;
            }
        });
        dialog.show();
    }

    private void openMicrophoneSettings() {
        awaitingMicrophoneSettings = true;
        Intent intent = new Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.fromParts("package", getPackageName(), null)
        );
        try {
            startActivity(intent);
        } catch (ActivityNotFoundException ignored) {
            awaitingMicrophoneSettings = false;
            resolveAudioPermissionRequest(false);
        }
    }

    private void dismissMicrophonePermissionDialog() {
        if (microphonePermissionDialog != null) {
            microphonePermissionDialog.dismiss();
            microphonePermissionDialog = null;
        }
    }

    private void resolveAudioPermissionRequest(boolean granted) {
        PermissionRequest request = pendingAudioPermissionRequest;
        pendingAudioPermissionRequest = null;
        audioPermissionRequestInFlight = false;
        awaitingMicrophoneSettings = false;
        dismissMicrophonePermissionDialog();
        if (request == null) {
            return;
        }
        if (granted && hasMicrophonePermission() && WebAudioPermissionPolicy.canGrant(
                String.valueOf(request.getOrigin()),
                request.getResources()
        )) {
            request.grant(new String[]{PermissionRequest.RESOURCE_AUDIO_CAPTURE});
        } else {
            request.deny();
            Toast.makeText(this, R.string.microphone_permission_denied, Toast.LENGTH_LONG).show();
        }
    }

    private void launchFileChooser(WebChromeClient.FileChooserParams params) {
        Intent files = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        files.addCategory(Intent.CATEGORY_OPENABLE);
        String[] mimeTypes = normalizedMimeTypes(params.getAcceptTypes());
        if (mimeTypes.length == 1) {
            files.setType(mimeTypes[0]);
        } else {
            files.setType("*/*");
            if (mimeTypes.length > 0) {
                files.putExtra(Intent.EXTRA_MIME_TYPES, mimeTypes);
            }
        }
        files.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,
                params.getMode() == WebChromeClient.FileChooserParams.MODE_OPEN_MULTIPLE);
        files.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

        List<Intent> extras = new ArrayList<>();
        if (acceptsImages(mimeTypes)) {
            Intent camera = createCameraIntent();
            if (camera != null) {
                extras.add(camera);
            }
        }

        Intent chooser = Intent.createChooser(files, getString(R.string.camera_or_file));
        if (!extras.isEmpty()) {
            chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS, extras.toArray(new Intent[0]));
        }
        try {
            startActivityForResult(chooser, REQUEST_FILE_CHOOSER);
        } catch (ActivityNotFoundException ignored) {
            fileCallback.onReceiveValue(null);
            fileCallback = null;
        }
    }

    private String[] normalizedMimeTypes(String[] rawTypes) {
        Set<String> unique = new LinkedHashSet<>();
        if (rawTypes != null) {
            for (String entry : rawTypes) {
                if (entry == null) {
                    continue;
                }
                for (String item : entry.split(",")) {
                    String mime = item.trim().toLowerCase(Locale.ROOT);
                    if (!mime.isEmpty() && mime.contains("/")) {
                        unique.add(mime);
                    }
                }
            }
        }
        return unique.toArray(new String[0]);
    }

    private boolean acceptsImages(String[] mimeTypes) {
        if (mimeTypes.length == 0) {
            return true;
        }
        for (String type : mimeTypes) {
            if ("*/*".equals(type) || type.startsWith("image/")) {
                return true;
            }
        }
        return false;
    }

    private Intent createCameraIntent() {
        try {
            File cameraDir = new File(getCacheDir(), "camera");
            if (!cameraDir.exists() && !cameraDir.mkdirs()) {
                return null;
            }
            pendingCameraFile = File.createTempFile("maestro_", ".jpg", cameraDir);
            pendingCameraUri = FileProvider.getUriForFile(
                    this,
                    getPackageName() + ".files",
                    pendingCameraFile
            );
            Intent camera = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            camera.putExtra(MediaStore.EXTRA_OUTPUT, pendingCameraUri);
            camera.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            return camera.resolveActivity(getPackageManager()) == null ? null : camera;
        } catch (IOException | IllegalArgumentException ignored) {
            pendingCameraFile = null;
            pendingCameraUri = null;
            return null;
        }
    }

    private final class StudioDownloadListener implements DownloadListener {
        @Override
        public void onDownloadStart(
                String url,
                String userAgent,
                String contentDisposition,
                String mimeType,
                long contentLength
        ) {
            if (pendingDownload != null) {
                Toast.makeText(MainActivity.this, R.string.download_busy, Toast.LENGTH_LONG).show();
                return;
            }
            boolean blob = url != null && url.startsWith("blob:");
            if (blob && !TrustedUrlPolicy.isMainHost(webView.getUrl())) {
                Toast.makeText(MainActivity.this, R.string.download_blocked, Toast.LENGTH_LONG).show();
                return;
            }
            if (!blob && !TrustedUrlPolicy.isTrustedHttps(url)) {
                Toast.makeText(MainActivity.this, R.string.download_blocked, Toast.LENGTH_LONG).show();
                return;
            }
            String fileName = sanitizeFileName(URLUtil.guessFileName(url, contentDisposition, mimeType));
            pendingDownload = new PendingDownload(url, userAgent, normalizedDownloadMime(mimeType), fileName, blob, contentLength);

            Intent destination = new Intent(Intent.ACTION_CREATE_DOCUMENT);
            destination.addCategory(Intent.CATEGORY_OPENABLE);
            destination.setType(pendingDownload.mimeType);
            destination.putExtra(Intent.EXTRA_TITLE, pendingDownload.fileName);
            try {
                startActivityForResult(
                        Intent.createChooser(destination, getString(R.string.download_choose_location)),
                        REQUEST_DOWNLOAD_DESTINATION
                );
            } catch (ActivityNotFoundException ignored) {
                pendingDownload = null;
                Toast.makeText(MainActivity.this, R.string.download_failed, Toast.LENGTH_LONG).show();
            }
        }
    }

    private String normalizedDownloadMime(String mimeType) {
        if (mimeType == null || !mimeType.contains("/")) {
            return "application/octet-stream";
        }
        return mimeType.split(";", 2)[0].trim().toLowerCase(Locale.ROOT);
    }

    private String sanitizeFileName(String proposed) {
        String value = proposed == null ? "maestro-studio" : proposed;
        value = value.replaceAll("[\\\\/:*?\"<>|\\p{Cntrl}]", "_").trim();
        if (value.isEmpty()) {
            value = "maestro-studio";
        }
        if (value.length() > 120) {
            value = value.substring(0, 120);
        }
        return value;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQUEST_FILE_CHOOSER) {
            handleFileChooserResult(resultCode, data);
        } else if (requestCode == REQUEST_DOWNLOAD_DESTINATION) {
            handleDownloadDestination(resultCode, data);
        }
    }

    @Override
    public void onRequestPermissionsResult(
            int requestCode,
            String[] permissions,
            int[] grantResults
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_RECORD_AUDIO) {
            audioPermissionRequestInFlight = false;
            boolean granted = grantResults.length > 0
                    && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            if (granted) {
                resolveAudioPermissionRequest(true);
            } else if (pendingAudioPermissionRequest != null) {
                handleMicrophonePermissionAction();
            }
        }
    }

    private void handleFileChooserResult(int resultCode, Intent data) {
        if (fileCallback == null) {
            clearCameraCapture(false);
            return;
        }
        Uri[] result = null;
        if (resultCode == RESULT_OK) {
            if (data == null || (data.getData() == null && data.getClipData() == null)) {
                if (pendingCameraUri != null && pendingCameraFile != null && pendingCameraFile.length() > 0) {
                    result = new Uri[]{pendingCameraUri};
                }
            } else if (data.getClipData() != null) {
                ClipData clip = data.getClipData();
                result = new Uri[clip.getItemCount()];
                for (int i = 0; i < clip.getItemCount(); i++) {
                    result[i] = clip.getItemAt(i).getUri();
                }
            } else if (data.getData() != null) {
                result = new Uri[]{data.getData()};
            }
        }
        fileCallback.onReceiveValue(result);
        fileCallback = null;
        clearCameraCapture(result != null && result.length == 1 && pendingCameraUri != null
                && pendingCameraUri.equals(result[0]));
    }

    private void clearCameraCapture(boolean keepForUpload) {
        if (!keepForUpload && pendingCameraFile != null && pendingCameraFile.exists()) {
            // Cache-only cleanup; failure is harmless and Android will evict it later.
            pendingCameraFile.delete();
        }
        pendingCameraFile = null;
        pendingCameraUri = null;
    }

    private void handleDownloadDestination(int resultCode, Intent data) {
        PendingDownload request = pendingDownload;
        if (request == null) {
            return;
        }
        if (resultCode != RESULT_OK || data == null || data.getData() == null) {
            blobBridge.cancel();
            pendingDownload = null;
            return;
        }

        Uri destination = data.getData();
        Toast.makeText(this, R.string.download_started, Toast.LENGTH_SHORT).show();
        if (request.blob) {
            if (!blobBridge.prepare(destination)) {
                pendingDownload = null;
                Toast.makeText(this, R.string.download_failed, Toast.LENGTH_LONG).show();
                return;
            }
            streamBlobFromWebView(request.url);
            return;
        }

        SecureDownloader.download(
                getApplicationContext(),
                downloadExecutor,
                destination,
                request.url,
                request.userAgent,
                request.contentLength,
                new SecureDownloader.Callback() {
                    @Override
                    public void onFinished() {
                        pendingDownload = null;
                        Toast.makeText(MainActivity.this, R.string.download_finished, Toast.LENGTH_LONG).show();
                    }

                    @Override
                    public void onFailed() {
                        pendingDownload = null;
                        Toast.makeText(MainActivity.this, R.string.download_failed, Toast.LENGTH_LONG).show();
                    }
                }
        );
    }

    private void streamBlobFromWebView(String blobUrl) {
        if (!TrustedUrlPolicy.isMainHost(webView.getUrl())) {
            blobBridge.cancel();
            pendingDownload = null;
            Toast.makeText(this, R.string.download_blocked, Toast.LENGTH_LONG).show();
            return;
        }
        String script = "(async()=>{try{" +
                "const r=await fetch(" + JSONObject.quote(blobUrl) + ");" +
                "if(!r.ok)throw new Error('blob');" +
                "const h=r.headers.get('Content-Length');let size=h===null?-1:Number(h);let body=r.body;" +
                "if(!Number.isSafeInteger(size)||size<0){const b=await r.blob();size=b.size;body=b.stream();}" +
                "if(!MaestroNativeBlob.begin(size))throw new Error('size');const reader=body.getReader();" +
                "for(;;){const x=await reader.read();if(x.done)break;" +
                "const a=x.value;for(let i=0;i<a.length;i+=49152){" +
                "const p=a.subarray(i,Math.min(i+49152,a.length));let s='';" +
                "for(let j=0;j<p.length;j++)s+=String.fromCharCode(p[j]);" +
                "if(!MaestroNativeBlob.writeChunk(btoa(s)))throw new Error('chunk');}}" +
                "MaestroNativeBlob.complete();}catch(e){MaestroNativeBlob.fail();}})();";
        webView.evaluateJavascript(script, null);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        Bundle webState = new Bundle();
        webView.saveState(webState);
        outState.putBundle(STATE_WEBVIEW, webState);
        outState.putLong(STATE_SAVED_AT, System.currentTimeMillis());
        super.onSaveInstanceState(outState);
    }

    @Override
    protected void onPause() {
        backgroundedAt = SystemClock.elapsedRealtime();
        CookieManager.getInstance().flush();
        webView.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        webView.onResume();
        boolean returnedFromMicrophoneSettings = awaitingMicrophoneSettings;
        if (returnedFromMicrophoneSettings) {
            resolveAudioPermissionRequest(hasMicrophonePermission());
        }
        if (firstResume) {
            firstResume = false;
            return;
        }
        long now = SystemClock.elapsedRealtime();
        boolean nativeFlowInProgress = fileCallback != null
                || pendingDownload != null
                || audioPermissionRequestInFlight
                || returnedFromMicrophoneSettings;
        if (!nativeFlowInProgress
                && WebAppRefreshPolicy.shouldReloadAfterBackground(backgroundedAt, now)) {
            retryCurrentDestination();
        }
    }

    @SuppressLint("GestureBackNavigation")
    @Override
    public void onBackPressed() {
        handleBackNavigation();
    }

    private void handleBackNavigation() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            finish();
        }
    }

    @Override
    protected void onDestroy() {
        destroying = true;
        pendingOpenCodePassword = null;
        if (openCodeLoginDialog != null) {
            openCodeLoginDialog.dismiss();
            openCodeLoginDialog = null;
        }
        if (fileCallback != null) {
            fileCallback.onReceiveValue(null);
            fileCallback = null;
        }
        if (pendingAudioPermissionRequest != null) {
            pendingAudioPermissionRequest.deny();
            pendingAudioPermissionRequest = null;
        }
        dismissMicrophonePermissionDialog();
        blobBridge.cancel();
        downloadExecutor.shutdownNow();
        controlExecutor.shutdownNow();
        webView.removeJavascriptInterface("MaestroNativeBlob");
        webView.stopLoading();
        webView.destroy();
        super.onDestroy();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static final class PendingDownload {
        final String url;
        final String userAgent;
        final String mimeType;
        final String fileName;
        final boolean blob;
        final long contentLength;

        PendingDownload(String url, String userAgent, String mimeType, String fileName, boolean blob, long contentLength) {
            this.url = url;
            this.userAgent = userAgent;
            this.mimeType = mimeType;
            this.fileName = fileName;
            this.blob = blob;
            this.contentLength = contentLength;
        }
    }
}
