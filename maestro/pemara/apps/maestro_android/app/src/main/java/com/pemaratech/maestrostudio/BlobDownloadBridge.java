package com.pemaratech.maestrostudio;

import android.content.Context;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.webkit.JavascriptInterface;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;

public final class BlobDownloadBridge {
    private static final int MAX_ENCODED_CHUNK = 512 * 1024;

    interface Listener {
        void onBlobFinished();
        void onBlobFailed();
    }

    private final Context context;
    private final Listener listener;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private OutputStream output;
    private File staged;
    private Uri destination;
    private long bytesWritten;
    private long expectedBytes = -1;

    BlobDownloadBridge(Context context, Listener listener) {
        this.context = context.getApplicationContext();
        this.listener = listener;
    }

    synchronized boolean prepare(Uri target) {
        cancelLocked();
        try {
            staged = StagedDownload.create(context);
            output = new FileOutputStream(staged);
            destination = target;
            return true;
        } catch (IOException | SecurityException ignored) {
            cancelLocked();
            return false;
        }
    }

    @JavascriptInterface
    public synchronized boolean begin(long expected) {
        if (output == null) {
            return false;
        }
        try {
            DownloadIntegrity.requireSize(expected);
            if (expectedBytes != -1 || bytesWritten != 0) {
                throw new IOException("Blob already started");
            }
            expectedBytes = expected;
            return true;
        } catch (IOException ignored) {
            failLocked();
            return false;
        }
    }

    @JavascriptInterface
    public synchronized boolean writeChunk(String encoded) {
        if (output == null) {
            return false;
        }
        try {
            if (expectedBytes < 0 || encoded == null || encoded.length() > MAX_ENCODED_CHUNK) {
                throw new IOException("Invalid blob chunk");
            }
            byte[] decoded = Base64.decode(encoded, Base64.DEFAULT);
            if (decoded.length > expectedBytes - bytesWritten) {
                throw new IOException("Blob exceeds expected size");
            }
            output.write(decoded);
            bytesWritten += decoded.length;
            return true;
        } catch (IOException | IllegalArgumentException ignored) {
            failLocked();
            return false;
        }
    }

    @JavascriptInterface
    public synchronized void complete() {
        if (output == null) {
            return;
        }
        try {
            DownloadIntegrity.requireComplete(bytesWritten, expectedBytes);
            output.flush();
            output.close();
            output = null;
            StagedDownload.commit(context.getContentResolver(), destination, staged, expectedBytes);
            cancelLocked();
            mainHandler.post(listener::onBlobFinished);
        } catch (IOException | SecurityException ignored) {
            failLocked();
        }
    }

    @JavascriptInterface
    public synchronized void fail() {
        if (output != null || staged != null) {
            failLocked();
        }
    }

    synchronized void cancel() {
        cancelLocked();
    }

    private void failLocked() {
        cancelLocked();
        mainHandler.post(listener::onBlobFailed);
    }

    private void cancelLocked() {
        if (output != null) {
            try {
                output.close();
            } catch (IOException ignored) {
                // Best-effort close.
            }
        }
        output = null;
        StagedDownload.discard(staged);
        staged = null;
        destination = null;
        bytesWritten = 0;
        expectedBytes = -1;
    }
}
