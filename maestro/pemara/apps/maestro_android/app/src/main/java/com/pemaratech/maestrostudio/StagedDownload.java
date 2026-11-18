package com.pemaratech.maestrostudio;

import android.content.ContentResolver;
import android.content.Context;
import android.net.Uri;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/** Receive into private cache, then save only the complete body. */
final class StagedDownload {
    private StagedDownload() {}

    static File create(Context context) throws IOException {
        return File.createTempFile("maestro-download-", ".part", context.getCacheDir());
    }

    static void commit(ContentResolver resolver, Uri destination, File staged, long expected)
            throws IOException {
        DownloadIntegrity.requireComplete(staged.length(), expected);
        try (InputStream input = new FileInputStream(staged);
             OutputStream output = resolver.openOutputStream(destination, "wt")) {
            if (output == null) {
                throw new IOException("Destination unavailable");
            }
            DownloadIntegrity.copy(input, output, expected);
        }
    }

    static void discard(File staged) {
        if (staged != null) {
            // Only our own new private cache file; Android can evict it if deletion fails.
            staged.delete();
        }
    }
}
