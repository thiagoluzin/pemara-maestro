package com.pemaratech.maestrostudio;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class WebAppRefreshPolicyTest {
    @Test
    public void appUpdateAlwaysRejectsTheOldWebViewState() {
        assertFalse(WebAppRefreshPolicy.shouldRestoreSavedState(true, 1_000L, 1_001L));
    }

    @Test
    public void recentSameBuildStateCanBeRestored() {
        long now = 1_000_000L;
        assertTrue(WebAppRefreshPolicy.shouldRestoreSavedState(
                false,
                now - WebAppRefreshPolicy.MAX_STALE_AGE_MS + 1L,
                now
        ));
    }

    @Test
    public void staleOrInvalidSavedStateMustReloadFromTheServer() {
        long now = 1_000_000L;
        assertFalse(WebAppRefreshPolicy.shouldRestoreSavedState(
                false,
                now - WebAppRefreshPolicy.MAX_STALE_AGE_MS,
                now
        ));
        assertFalse(WebAppRefreshPolicy.shouldRestoreSavedState(false, 0L, now));
        assertFalse(WebAppRefreshPolicy.shouldRestoreSavedState(false, now + 1L, now));
    }

    @Test
    public void returningAfterFiveMinutesReloadsTheWebApp() {
        long backgroundedAt = 10_000L;
        assertFalse(WebAppRefreshPolicy.shouldReloadAfterBackground(
                backgroundedAt,
                backgroundedAt + WebAppRefreshPolicy.MAX_STALE_AGE_MS - 1L
        ));
        assertTrue(WebAppRefreshPolicy.shouldReloadAfterBackground(
                backgroundedAt,
                backgroundedAt + WebAppRefreshPolicy.MAX_STALE_AGE_MS
        ));
    }
}
