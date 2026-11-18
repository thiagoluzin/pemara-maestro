package com.pemaratech.maestrostudio;

public final class WebAudioPermissionPolicy {
    static final String AUDIO_CAPTURE_RESOURCE = "android.webkit.resource.AUDIO_CAPTURE";

    private WebAudioPermissionPolicy() {}

    public static boolean canGrant(String origin, String[] resources) {
        if (!TrustedUrlPolicy.isMainHost(origin) || resources == null || resources.length != 1) {
            return false;
        }
        return AUDIO_CAPTURE_RESOURCE.equals(resources[0]);
    }
}
