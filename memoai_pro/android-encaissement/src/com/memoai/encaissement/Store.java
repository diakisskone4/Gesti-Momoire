package com.memoai.encaissement;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** Réglages et file d'attente, dans le stockage privé de l'application (exclu des sauvegardes). */
final class Store {
    static final int MAX_QUEUE = 500;
    private static final Object LOCK = new Object();

    private final SharedPreferences prefs;

    Store(Context context) {
        prefs = context.getApplicationContext().getSharedPreferences("encaissement", Context.MODE_PRIVATE);
    }

    String token() { return prefs.getString("token", ""); }
    void setToken(String token) { prefs.edit().putString("token", token).remove("status").apply(); }

    String senders(String operator) {
        String fallback = "orange".equals(operator) ? "OrangeMoney" : "moov".equals(operator) ? "MoovMoney, Moov" : "Wave";
        return prefs.getString("senders_" + operator, fallback);
    }
    void setSenders(String operator, String names) { prefs.edit().putString("senders_" + operator, names).apply(); }

    String status() { return prefs.getString("status", ""); }
    void setStatus(String status) { prefs.edit().putString("status", status).apply(); }

    private JSONArray read() {
        try {
            return new JSONArray(prefs.getString("queue", "[]"));
        } catch (JSONException e) {
            return new JSONArray();
        }
    }

    int size() {
        synchronized (LOCK) { return read().length(); }
    }

    void add(String operator, String text, long receivedAt) {
        synchronized (LOCK) {
            JSONArray queue = read();
            if (queue.length() >= MAX_QUEUE) queue.remove(0);
            try {
                queue.put(new JSONObject().put("operator", operator).put("text", text).put("received_at", receivedAt));
            } catch (JSONException e) {
                return;
            }
            // commit() : le message doit être sur le disque avant la fin du récepteur.
            prefs.edit().putString("queue", queue.toString()).commit();
        }
    }

    JSONArray peek(int max) {
        synchronized (LOCK) {
            JSONArray queue = read();
            JSONArray first = new JSONArray();
            for (int i = 0; i < Math.min(max, queue.length()); i++) first.put(queue.opt(i));
            return first;
        }
    }

    /** Retire les messages que le serveur a bien reçus (les nouveaux, ajoutés à la fin, sont conservés). */
    void drop(JSONArray sent) {
        synchronized (LOCK) {
            JSONArray queue = read();
            for (int i = 0; i < sent.length() && queue.length() > 0; i++) {
                if (!String.valueOf(queue.opt(0)).equals(String.valueOf(sent.opt(i)))) break;
                queue.remove(0);
            }
            prefs.edit().putString("queue", queue.toString()).commit();
        }
    }
}
