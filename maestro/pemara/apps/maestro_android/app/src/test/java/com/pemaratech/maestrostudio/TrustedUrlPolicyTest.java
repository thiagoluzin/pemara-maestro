package com.pemaratech.maestrostudio;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class TrustedUrlPolicyTest {
    @Test
    public void acceptsOnlyKnownHttpsHosts() {
        assertTrue(TrustedUrlPolicy.isTrustedHttps("https://maestro.pemaratech.com.br/"));
        assertTrue(TrustedUrlPolicy.isTrustedHttps("https://sprunki.pemaratech.com.br/login/handoff?code=x"));
        assertTrue(TrustedUrlPolicy.isTrustedHttps("https://comfy.pemaratech.com.br:443/"));
        assertTrue(TrustedUrlPolicy.isTrustedHttps("https://pc-geral-thiago-1.tail14cf8c.ts.net/"));
        assertTrue(TrustedUrlPolicy.isTrustedHttps("https://pc-geral-thiago-1.tail14cf8c.ts.net:8443/"));
        assertTrue(TrustedUrlPolicy.isTrustedHttps("https://pc-geral-thiago-1.tail14cf8c.ts.net:10000/"));
    }

    @Test
    public void rejectsCleartextLookalikesAndUnexpectedPorts() {
        assertFalse(TrustedUrlPolicy.isTrustedHttps("http://maestro.pemaratech.com.br/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("https://maestro.pemaratech.com.br.evil.example/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("https://evil.example/?next=maestro.pemaratech.com.br"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("https://maestro.pemaratech.com.br:8443/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("https://user@maestro.pemaratech.com.br/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("http://pc-geral-thiago-1.tail14cf8c.ts.net/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("https://pc-geral-thiago-1.tail14cf8c.ts.net:4096/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("https://pc-geral-thiago-1.tail14cf8c.ts.net:10443/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("https://pc-geral-thiago-1.tail14cf8c.ts.net.evil.example/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("https://opencode@pc-geral-thiago-1.tail14cf8c.ts.net/"));
        assertFalse(TrustedUrlPolicy.isTrustedHttps("javascript:alert(1)"));
    }

    @Test
    public void identifiesOnlyThePrivateOpenCodeEndpoint() {
        assertTrue(TrustedUrlPolicy.isOpenCodeUrl("https://pc-geral-thiago-1.tail14cf8c.ts.net/"));
        assertTrue(TrustedUrlPolicy.isOpenCodeUrl("https://pc-geral-thiago-1.tail14cf8c.ts.net:443/session/123"));
        assertFalse(TrustedUrlPolicy.isOpenCodeUrl("https://pc-geral-thiago-1.tail14cf8c.ts.net:10000/"));
        assertFalse(TrustedUrlPolicy.isOpenCodeUrl("https://maestro.pemaratech.com.br/"));
        assertFalse(TrustedUrlPolicy.isOpenCodeUrl("https://pc-geral-thiago-1.tail14cf8c.ts.net.evil.example/"));
    }

    @Test
    public void distinguishesTheMainStudioHost() {
        assertTrue(TrustedUrlPolicy.isMainHost("https://maestro.pemaratech.com.br/api/studio"));
        assertFalse(TrustedUrlPolicy.isMainHost("https://comfy.pemaratech.com.br/"));
    }
}
