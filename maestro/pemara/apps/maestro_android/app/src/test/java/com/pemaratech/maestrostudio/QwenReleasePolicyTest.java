package com.pemaratech.maestrostudio;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public final class QwenReleasePolicyTest {
    @Test
    public void activeQwenIsNeverReleasable() {
        assertEquals(
                QwenReleasePolicy.Decision.ACTIVE,
                QwenReleasePolicy.decide("active", true)
        );
    }

    @Test
    public void loadedIdleNeedsExplicitServerConfirmation() {
        assertEquals(
                QwenReleasePolicy.Decision.WAITING_CONFIRMATION,
                QwenReleasePolicy.decide("loaded_idle", false)
        );
        assertEquals(
                QwenReleasePolicy.Decision.RELEASE_ALLOWED,
                QwenReleasePolicy.decide("loaded_idle", true)
        );
    }

    @Test
    public void unknownAndStoppingRemainBlocked() {
        assertEquals(
                QwenReleasePolicy.Decision.BLOCKED,
                QwenReleasePolicy.decide("unknown", false)
        );
        assertEquals(
                QwenReleasePolicy.Decision.RELEASE_IN_PROGRESS,
                QwenReleasePolicy.decide("stopping", false)
        );
    }

    @Test
    public void unloadedMeansComfyUiCanOpenWithoutStop() {
        assertEquals(
                QwenReleasePolicy.Decision.ALREADY_FREE,
                QwenReleasePolicy.decide("unloaded", false)
        );
    }
}
