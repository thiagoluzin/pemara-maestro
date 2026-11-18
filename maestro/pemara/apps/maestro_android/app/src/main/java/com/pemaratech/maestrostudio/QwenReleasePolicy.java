package com.pemaratech.maestrostudio;

import java.util.Locale;

final class QwenReleasePolicy {
    enum Decision {
        ACTIVE,
        RELEASE_ALLOWED,
        ALREADY_FREE,
        RELEASE_IN_PROGRESS,
        WAITING_CONFIRMATION,
        BLOCKED
    }

    private QwenReleasePolicy() {
    }

    static Decision decide(String state, boolean canRelease) {
        String normalized = state == null
                ? ""
                : state.trim().toLowerCase(Locale.ROOT);
        if ("active".equals(normalized)) {
            return Decision.ACTIVE;
        }
        if ("unloaded".equals(normalized)) {
            return Decision.ALREADY_FREE;
        }
        if ("stopping".equals(normalized)) {
            return Decision.RELEASE_IN_PROGRESS;
        }
        if ("loaded_idle".equals(normalized)) {
            return canRelease
                    ? Decision.RELEASE_ALLOWED
                    : Decision.WAITING_CONFIRMATION;
        }
        return Decision.BLOCKED;
    }
}
