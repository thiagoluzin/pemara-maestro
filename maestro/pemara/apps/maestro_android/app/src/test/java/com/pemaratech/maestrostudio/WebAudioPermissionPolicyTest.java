package com.pemaratech.maestrostudio;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class WebAudioPermissionPolicyTest {
    @Test
    public void grantsOnlyAudioCaptureToTheMainMaestroOrigin() {
        assertTrue(WebAudioPermissionPolicy.canGrant(
                "https://maestro.pemaratech.com.br/",
                new String[]{WebAudioPermissionPolicy.AUDIO_CAPTURE_RESOURCE}
        ));
    }

    @Test
    public void rejectsOtherOriginsAndMixedResourceRequests() {
        assertFalse(WebAudioPermissionPolicy.canGrant(
                "https://maestro.pemaratech.com.br.evil.example/",
                new String[]{WebAudioPermissionPolicy.AUDIO_CAPTURE_RESOURCE}
        ));
        assertFalse(WebAudioPermissionPolicy.canGrant(
                "https://comfy.pemaratech.com.br/",
                new String[]{WebAudioPermissionPolicy.AUDIO_CAPTURE_RESOURCE}
        ));
        assertFalse(WebAudioPermissionPolicy.canGrant(
                "https://maestro.pemaratech.com.br/",
                new String[]{
                        WebAudioPermissionPolicy.AUDIO_CAPTURE_RESOURCE,
                        "android.webkit.resource.VIDEO_CAPTURE"
                }
        ));
        assertFalse(WebAudioPermissionPolicy.canGrant(
                "https://maestro.pemaratech.com.br/",
                new String[]{"android.webkit.resource.VIDEO_CAPTURE"}
        ));
    }
}
