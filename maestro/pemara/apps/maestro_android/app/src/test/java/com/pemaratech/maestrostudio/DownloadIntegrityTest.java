package com.pemaratech.maestrostudio;

import static org.junit.Assert.*;
import org.junit.Test;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Random;

public class DownloadIntegrityTest {
    @Test public void completeLargeFileKeepsEveryByte() throws Exception {
        byte[] data = new byte[3 * 1024 * 1024 + 137];
        new Random(421).nextBytes(data);
        ByteArrayOutputStream saved = new ByteArrayOutputStream();
        assertEquals(data.length, DownloadIntegrity.copy(new ByteArrayInputStream(data), saved, data.length));
        assertArrayEquals(MessageDigest.getInstance("SHA-256").digest(data),
                MessageDigest.getInstance("SHA-256").digest(saved.toByteArray()));
    }

    @Test public void cleanEarlyEofIsFailure() {
        assertThrows(IOException.class, () -> DownloadIntegrity.copy(
                new ByteArrayInputStream(new byte[37]), new ByteArrayOutputStream(), 100));
    }

    @Test public void excessiveBodyIsFailure() {
        assertThrows(IOException.class, () -> DownloadIntegrity.copy(
                new ByteArrayInputStream(new byte[101]), new ByteArrayOutputStream(), 100));
    }

    @Test public void interruptedReadIsFailure() {
        InputStream broken = new InputStream() {
            @Override public int read() throws IOException { throw new IOException("connection lost"); }
        };
        assertThrows(IOException.class, () -> DownloadIntegrity.copy(broken, new ByteArrayOutputStream(), 100));
    }

    @Test public void cancellationIsNotCompletion() {
        Thread.currentThread().interrupt();
        try {
            assertThrows(InterruptedIOException.class, () -> DownloadIntegrity.copy(
                    new ByteArrayInputStream(new byte[100]), new ByteArrayOutputStream(), 100));
        } finally { Thread.interrupted(); }
    }

    @Test public void fullHttpResponseUsesHeaderLength() throws Exception {
        assertEquals(100, DownloadIntegrity.expectedHttpBytes(200, null, 100, -1, null));
    }

    @Test public void listenerSizeIsUsedWhenHeaderIsAbsent() throws Exception {
        assertEquals(100, DownloadIntegrity.expectedHttpBytes(200, null, -1, 100, "identity"));
    }

    @Test public void partial206ResponseIsNeverAFullDownload() {
        assertThrows(IOException.class, () -> DownloadIntegrity.expectedHttpBytes(
                206, "bytes 0-99/1000", 100, 1000, null));
    }

    @Test public void rangeHeaderOn200IsRejected() {
        assertThrows(IOException.class, () -> DownloadIntegrity.expectedHttpBytes(
                200, "bytes 0-99/1000", 100, -1, null));
    }

    @Test public void missingBodyAndErrorStatusAreRejected() {
        for (int status : new int[]{204, 302, 401, 403, 404, 500}) {
            assertThrows(IOException.class, () -> DownloadIntegrity.expectedHttpBytes(status, null, 0, -1, null));
        }
    }

    @Test public void inconsistentAndUnknownSizesAreRejected() {
        assertThrows(IOException.class, () -> DownloadIntegrity.expectedHttpBytes(200, null, 100, 1000, null));
        assertThrows(IOException.class, () -> DownloadIntegrity.expectedHttpBytes(200, null, -1, -1, null));
    }

    @Test public void compressedTransferCannotBypassByteCheck() {
        assertThrows(IOException.class, () -> DownloadIntegrity.expectedHttpBytes(200, null, 100, -1, "gzip"));
    }

    @Test public void blobCompletionRequiresExactSize() throws Exception {
        DownloadIntegrity.requireComplete(100, 100);
        assertThrows(IOException.class, () -> DownloadIntegrity.requireComplete(99, 100));
        assertThrows(IOException.class, () -> DownloadIntegrity.requireComplete(101, 100));
        assertThrows(IOException.class, () -> DownloadIntegrity.requireComplete(0, -1));
    }

    @Test public void maximumSizeAndEmptyFilesAreExplicit() throws Exception {
        DownloadIntegrity.requireSize(DownloadIntegrity.MAX_BYTES);
        assertThrows(IOException.class, () -> DownloadIntegrity.requireSize(DownloadIntegrity.MAX_BYTES + 1));
        assertEquals(0, DownloadIntegrity.copy(new ByteArrayInputStream(new byte[0]), new ByteArrayOutputStream(), 0));
    }

    @Test public void actualHttpConnectionEndingEarlyCannotReachSave() throws Exception {
        try (ServerSocket server = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            Thread sender = new Thread(() -> {
                try (Socket client = server.accept()) {
                    client.setSoTimeout(5000);
                    BufferedReader request = new BufferedReader(new InputStreamReader(client.getInputStream(),
                            StandardCharsets.US_ASCII));
                    String line;
                    while ((line = request.readLine()) != null && !line.isEmpty()) {}
                    OutputStream out = client.getOutputStream();
                    out.write(("HTTP/1.1 200 OK\r\nContent-Length: 100000\r\n"
                            + "Connection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
                    out.write(new byte[1024]);
                    out.flush();
                } catch (IOException failure) { throw new UncheckedIOException(failure); }
            });
            sender.start();
            HttpURLConnection connection = (HttpURLConnection) new URL(
                    "http://127.0.0.1:" + server.getLocalPort() + "/video.mp4").openConnection();
            connection.setConnectTimeout(5000);
            connection.setReadTimeout(5000);
            ByteArrayOutputStream privateStage = new ByteArrayOutputStream();
            ByteArrayOutputStream userFile = new ByteArrayOutputStream();
            try (InputStream input = connection.getInputStream()) {
                long expected = DownloadIntegrity.expectedHttpBytes(connection.getResponseCode(), null,
                        connection.getContentLengthLong(), -1, null);
                assertThrows(IOException.class, () -> {
                    DownloadIntegrity.copy(input, privateStage, expected);
                    privateStage.writeTo(userFile);
                });
                assertEquals(0, userFile.size());
            } finally {
                connection.disconnect();
                sender.join(5000);
            }
        }
    }
}
