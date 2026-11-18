package com.pemaratech.maestrostudio;

import java.io.IOException;
import java.io.InputStream;
import java.io.InterruptedIOException;
import java.io.OutputStream;

/** Byte-level checks shared by HTTP and WebView blob downloads. */
final class DownloadIntegrity {
    static final long MAX_BYTES = 8L * 1024 * 1024 * 1024;

    private DownloadIntegrity() {}

    static long expectedHttpBytes(int status, String contentRange, long headerLength,
                                  long listenerLength, String encoding) throws IOException {
        if (status != 200 || contentRange != null) {
            throw new IOException("A complete HTTP response is required");
        }
        if (encoding != null && !encoding.isEmpty() && !"identity".equalsIgnoreCase(encoding)) {
            throw new IOException("Unexpected content encoding");
        }
        if (headerLength >= 0 && listenerLength > 0 && headerLength != listenerLength) {
            throw new IOException("Download size changed");
        }
        long expected = headerLength >= 0 ? headerLength : listenerLength;
        requireSize(expected);
        return expected;
    }

    static void requireSize(long expected) throws IOException {
        if (expected < 0 || expected > MAX_BYTES) {
            throw new IOException("Download size unavailable or exceeds limit");
        }
    }

    static void requireComplete(long actual, long expected) throws IOException {
        requireSize(expected);
        if (actual != expected) {
            throw new IOException("Incomplete download");
        }
    }

    static long copy(InputStream input, OutputStream output, long expected) throws IOException {
        requireSize(expected);
        byte[] buffer = new byte[64 * 1024];
        long written = 0;
        for (;;) {
            if (Thread.currentThread().isInterrupted()) {
                throw new InterruptedIOException("Download cancelled");
            }
            int count = input.read(buffer);
            if (count == -1) {
                break;
            }
            if (count == 0) {
                continue;
            }
            if (count > expected - written) {
                throw new IOException("Download exceeds expected size");
            }
            output.write(buffer, 0, count);
            written += count;
        }
        requireComplete(written, expected);
        output.flush();
        return written;
    }
}
