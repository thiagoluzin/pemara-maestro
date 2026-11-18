package com.pemaratech.maestrostudio;

public final class MicrophonePermissionPolicy {
    public enum Action {
        GRANT_WEB_REQUEST,
        REQUEST_ANDROID_PERMISSION,
        EXPLAIN_AND_RETRY,
        OPEN_APP_SETTINGS
    }

    private MicrophonePermissionPolicy() {}

    public static Action decide(
            boolean permissionGranted,
            boolean requestedBefore,
            boolean shouldShowRationale
    ) {
        if (permissionGranted) {
            return Action.GRANT_WEB_REQUEST;
        }
        if (!requestedBefore) {
            return Action.REQUEST_ANDROID_PERMISSION;
        }
        if (shouldShowRationale) {
            return Action.EXPLAIN_AND_RETRY;
        }
        return Action.OPEN_APP_SETTINGS;
    }
}
