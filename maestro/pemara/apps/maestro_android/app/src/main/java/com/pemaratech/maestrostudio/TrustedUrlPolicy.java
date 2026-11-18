package com.pemaratech.maestrostudio;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

public final class TrustedUrlPolicy {
    private static final String PRIVATE_MACHINE_HOST =
            "pc-geral-thiago-1.tail14cf8c.ts.net";
    private static final Set<String> TRUSTED_HOSTS;

    static {
        Set<String> hosts = new HashSet<>();
        hosts.add("maestro.pemaratech.com.br");
        hosts.add("comfy.pemaratech.com.br");
        hosts.add("sprunki.pemaratech.com.br");
        hosts.add("perplexica.pemaratech.com.br");
        TRUSTED_HOSTS = Collections.unmodifiableSet(hosts);
    }

    private TrustedUrlPolicy() {}

    public static boolean isTrustedHttps(String rawUrl) {
        URI uri = parseHttps(rawUrl);
        if (uri == null) {
            return false;
        }
        String host = uri.getHost().toLowerCase(Locale.ROOT);
        int port = uri.getPort();
        if (TRUSTED_HOSTS.contains(host)) {
            return port == -1 || port == 443;
        }
        return PRIVATE_MACHINE_HOST.equals(host)
                && (port == -1 || port == 443 || port == 8443 || port == 10000);
    }

    public static boolean isOpenCodeUrl(String rawUrl) {
        URI uri = parseHttps(rawUrl);
        if (uri == null) {
            return false;
        }
        int port = uri.getPort();
        return PRIVATE_MACHINE_HOST.equalsIgnoreCase(uri.getHost())
                && (port == -1 || port == 443);
    }

    private static URI parseHttps(String rawUrl) {
        if (rawUrl == null || rawUrl.trim().isEmpty()) {
            return null;
        }
        try {
            URI uri = new URI(rawUrl);
            String scheme = uri.getScheme();
            String host = uri.getHost();
            boolean valid = "https".equalsIgnoreCase(scheme)
                    && host != null
                    && uri.getRawUserInfo() == null;
            return valid ? uri : null;
        } catch (URISyntaxException | IllegalArgumentException ignored) {
            return null;
        }
    }

    public static boolean isMainHost(String rawUrl) {
        if (!isTrustedHttps(rawUrl)) {
            return false;
        }
        try {
            return "maestro.pemaratech.com.br".equalsIgnoreCase(new URI(rawUrl).getHost());
        } catch (URISyntaxException ignored) {
            return false;
        }
    }
}
