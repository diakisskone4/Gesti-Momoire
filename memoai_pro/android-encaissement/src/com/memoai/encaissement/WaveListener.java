package com.memoai.encaissement;

import android.app.Notification;
import android.os.Bundle;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

/** Notifications « argent reçu » de l'application Wave. Celles des autres applications ne sont jamais lues. */
public class WaveListener extends NotificationListenerService {
    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        if (sbn == null || !Filter.WAVE_PACKAGE.equals(sbn.getPackageName())) return;
        Notification notification = sbn.getNotification();
        Bundle extras = notification == null ? null : notification.extras;
        if (extras == null) return;
        CharSequence title = extras.getCharSequence(Notification.EXTRA_TITLE);
        CharSequence big = extras.getCharSequence(Notification.EXTRA_BIG_TEXT);
        CharSequence text = big != null ? big : extras.getCharSequence(Notification.EXTRA_TEXT);
        String content = ((title == null ? "" : title + ". ") + (text == null ? "" : text)).trim();

        Store store = new Store(this);
        if (store.token().isEmpty() || !Filter.isPayment(content)) return;
        store.add("wave", content, sbn.getPostTime());
        UploadJob.schedule(this);
    }
}
