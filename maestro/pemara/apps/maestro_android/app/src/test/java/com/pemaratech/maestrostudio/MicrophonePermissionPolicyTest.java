package com.pemaratech.maestrostudio;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public final class MicrophonePermissionPolicyTest {
    @Test
    public void grantedPermissionCanCompleteTheWebRequest() {
        assertEquals(
                MicrophonePermissionPolicy.Action.GRANT_WEB_REQUEST,
                MicrophonePermissionPolicy.decide(true, true, false)
        );
    }

    @Test
    public void firstUseRequestsAndroidPermissionInContext() {
        assertEquals(
                MicrophonePermissionPolicy.Action.REQUEST_ANDROID_PERMISSION,
                MicrophonePermissionPolicy.decide(false, false, false)
        );
    }

    @Test
    public void softDenialGetsAnAccessibleExplanationAndRetry() {
        assertEquals(
                MicrophonePermissionPolicy.Action.EXPLAIN_AND_RETRY,
                MicrophonePermissionPolicy.decide(false, true, true)
        );
    }

    @Test
    public void permanentDenialGoesToAppSettings() {
        assertEquals(
                MicrophonePermissionPolicy.Action.OPEN_APP_SETTINGS,
                MicrophonePermissionPolicy.decide(false, true, false)
        );
    }
}
