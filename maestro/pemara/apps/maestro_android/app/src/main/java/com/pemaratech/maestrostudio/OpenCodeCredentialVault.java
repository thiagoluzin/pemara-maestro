package com.pemaratech.maestrostudio;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class OpenCodeCredentialVault {
    private static final String ANDROID_KEY_STORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "maestro_opencode_password_v1";
    private static final String PREFERENCES = "maestro_private_credentials";
    private static final String CIPHERTEXT = "opencode_password_ciphertext";
    private static final String IV = "opencode_password_iv";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";

    private final SharedPreferences preferences;

    OpenCodeCredentialVault(Context context) {
        preferences = context.getApplicationContext()
                .getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE);
    }

    boolean savePassword(String password) {
        if (password == null || password.isEmpty()) {
            return false;
        }
        try {
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey());
            byte[] encrypted = cipher.doFinal(password.getBytes(StandardCharsets.UTF_8));
            preferences.edit()
                    .putString(CIPHERTEXT, Base64.encodeToString(encrypted, Base64.NO_WRAP))
                    .putString(IV, Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP))
                    .apply();
            return true;
        } catch (GeneralSecurityException | IOException ignored) {
            clear();
            return false;
        }
    }

    String loadPassword() {
        String encryptedValue = preferences.getString(CIPHERTEXT, null);
        String ivValue = preferences.getString(IV, null);
        if (encryptedValue == null || ivValue == null) {
            return null;
        }
        try {
            byte[] encrypted = Base64.decode(encryptedValue, Base64.NO_WRAP);
            byte[] iv = Base64.decode(ivValue, Base64.NO_WRAP);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), new GCMParameterSpec(128, iv));
            byte[] decrypted = cipher.doFinal(encrypted);
            try {
                return new String(decrypted, StandardCharsets.UTF_8);
            } finally {
                java.util.Arrays.fill(decrypted, (byte) 0);
            }
        } catch (GeneralSecurityException | IOException | IllegalArgumentException ignored) {
            clear();
            return null;
        }
    }

    void clear() {
        preferences.edit().remove(CIPHERTEXT).remove(IV).apply();
    }

    private SecretKey getOrCreateKey() throws GeneralSecurityException, IOException {
        KeyStore keyStore = KeyStore.getInstance(ANDROID_KEY_STORE);
        keyStore.load(null);
        SecretKey existing = (SecretKey) keyStore.getKey(KEY_ALIAS, null);
        if (existing != null) {
            return existing;
        }

        KeyGenerator generator = KeyGenerator.getInstance(
                KeyProperties.KEY_ALGORITHM_AES,
                ANDROID_KEY_STORE
        );
        generator.init(new KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT
        )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .build());
        return generator.generateKey();
    }
}
