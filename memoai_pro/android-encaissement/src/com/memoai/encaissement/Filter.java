package com.memoai.encaissement;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Décide quels messages quittent le téléphone : uniquement « argent reçu », uniquement des opérateurs.
 * Tout le reste (SMS personnels, codes secrets, codes de validation) est ignoré et jamais envoyé.
 */
final class Filter {
    static final String WAVE_PACKAGE = "com.wave.personal";

    private static final Pattern RECEIVED = Pattern.compile("\\b(recue?|credite|received)\\b");
    private static final Pattern AMOUNT = Pattern.compile("\\d ?(f|fcfa|f cfa|cfa|xof)\\b|\\b(fcfa|xof) ?\\d");
    // « Ne partagez jamais votre code secret » est permis ; « votre code est 1234 » ne sort jamais du téléphone.
    private static final Pattern SECRET = Pattern.compile("\\b(code(?! (de |du )?(la )?(transaction|transfert|reference))"
            + "|otp|pin|mot de passe)( [a-z]+){0,3} ?(:|=|est|is) ?\\d{3,}");
    private static final Pattern PHONE = Pattern.compile("\\+?[\\d ]{6,}");

    private Filter() { }

    private static String plain(String text) {
        return Normalizer.normalize(text == null ? "" : text, Normalizer.Form.NFKD)
                .replaceAll("\\p{M}", "").replaceAll("[\\s\\u00A0\\u202F]+", " ").trim().toLowerCase(Locale.ROOT);
    }

    static String compact(String text) {
        return plain(text).replaceAll("[^a-z0-9]", "");
    }

    /** Vrai si l'un des noms (séparés par des virgules) est contenu dans l'expéditeur. */
    private static boolean matches(String sender, String names) {
        for (String name : names.split(",")) {
            String wanted = compact(name);
            if (!wanted.isEmpty() && sender.contains(wanted)) return true;
        }
        return false;
    }

    /** Opérateur d'un SMS, ou null. Un numéro de téléphone ordinaire n'est jamais un opérateur. */
    static String operator(String sender, String orange, String moov, String wave) {
        if (sender == null || PHONE.matcher(sender.trim()).matches()) return null;
        String name = compact(sender);
        if (matches(name, orange)) return "orange";
        if (matches(name, moov)) return "moov";
        if (matches(name, wave)) return "wave";
        return null;
    }

    /** Vrai si le message annonce de l'argent reçu et ne contient aucun code confidentiel. */
    static boolean isPayment(String text) {
        String value = plain(text);
        return RECEIVED.matcher(value).find() && AMOUNT.matcher(value).find() && !SECRET.matcher(value).find();
    }
}
