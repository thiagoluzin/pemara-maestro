package com.pemaratech.maestrostudio;

import android.content.Context;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.webkit.CookieManager;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.Executor;

final class SecureDownloader {
    private static final int MAX_REDIRECTS = 5;
    private static final int CONNECT_TIMEOUT_MS = 20_000;
    private static final int READ_TIMEOUT_MS = 180_000;

    interface Callback {
        void onFinished();
        void onFailed();
    }

    private SecureDownloader() {}

    static void download(Context context, Executor executor, Uri destination, String sourceUrl,
                         String userAgent, long listenerLength, Callback callback) {
        Handler mainHandler = new Handler(Looper.getMainLooper());
        executor.execute(() -> {
            boolean success = false;
            File staged = null;
            try {
                staged = StagedDownload.create(context);
                long expected;
                try (Response response = openTrustedStream(sourceUrl, userAgent, listenerLength);
                     OutputStream output = new FileOutputStream(staged)) {
                    expected = response.expected;
                    DownloadIntegrity.copy(response.input, output, expected);
                }
                StagedDownload.commit(context.getContentResolver(), destination, staged, expected);
                success = true;
            } catch (IOException | SecurityException ignored) {
                success = false;
            } finally {
                StagedDownload.discard(staged);
            }
            boolean completed = success;
            mainHandler.post(() -> {
                if (completed) {
                    callback.onFinished();
                } else {
                    callback.onFailed();
                }
            });
        });
    }

    private static Response openTrustedStream(String sourceUrl, String userAgent, long listenerLength)
            throws IOException {
        URL current = new URL(sourceUrl);
        for (int redirects = 0; redirects <= MAX_REDIRECTS; redirects++) {
            String currentUrl = current.toExternalForm();
            if (!TrustedUrlPolicy.isTrustedHttps(currentUrl)) {
                throw new IOException("Redirect left trusted origins");
            }
            HttpURLConnection connection = (HttpURLConnection) current.openConnection();
            boolean handedOff = false;
            try {
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
                connection.setReadTimeout(READ_TIMEOUT_MS);
                connection.setUseCaches(false);
                connection.setRequestProperty("Accept", "*/*");
                connection.setRequestProperty("Accept-Encoding", "identity");
                if (userAgent != null && !userAgent.isEmpty()) {
                    connection.setRequestProperty("User-Agent", userAgent);
                }
                String cookie = CookieManager.getInstance().getCookie(currentUrl);
                if (cookie != null && !cookie.isEmpty()) {
                    connection.setRequestProperty("Cookie", cookie);
                }
                int status = connection.getResponseCode();
                if (status >= 300 && status < 400) {
                    String location = connection.getHeaderField("Location");
                    if (location == null || location.trim().isEmpty() || redirects == MAX_REDIRECTS) {
                        throw new IOException("Invalid redirect");
                    }
                    current = new URL(current, location);
                    continue;
                }
                long expected = DownloadIntegrity.expectedHttpBytes(status,
                        connection.getHeaderField("Content-Range"), connection.getContentLengthLong(),
                        listenerLength, connection.getHeaderField("Content-Encoding"));
                Response response = new Response(connection, connection.getInputStream(), expected);
                handedOff = true;
                return response;
            } finally {
                if (!handedOff) {
                    connection.disconnect();
                }
            }
        }
        throw new IOException("Too many redirects");
    }

    private static final class Response implements AutoCloseable {
        final HttpURLConnection connection;
        final InputStream input;
        final long expected;

        Response(HttpURLConnection connection, InputStream input, long expected) {
            this.connection = connection;
            this.input = input;
            this.expected = expected;
        }

        @Override
        public void close() throws IOException {
            try {
                input.close();
            } finally {
                connection.disconnect();
            }
        }
    }
}
