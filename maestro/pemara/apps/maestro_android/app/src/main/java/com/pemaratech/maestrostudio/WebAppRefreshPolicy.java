package com.pemaratech.maestrostudio;

final class WebAppRefreshPolicy {
    static final long MAX_STALE_AGE_MS = 5L * 60L * 1000L;

    private WebAppRefreshPolicy() {}

    static boolean shouldRestoreSavedState(boolean appBuildChanged, long savedAt, long now) {
        return !appBuildChanged
                && savedAt > 0L
                && now >= savedAt
                && now - savedAt < MAX_STALE_AGE_MS;
    }

    static boolean shouldReloadAfterBackground(long backgroundedAt, long now) {
        return backgroundedAt > 0L
                && now >= backgroundedAt
                && now - backgroundedAt >= MAX_STALE_AGE_MS;
    }
}
