package com.memoai.encaissement;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.provider.Telephony;
import android.telephony.SmsMessage;

/** SMS « argent reçu » d'Orange Money, Moov Money ou Wave. */
public class SmsReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (!Telephony.Sms.Intents.SMS_RECEIVED_ACTION.equals(intent.getAction())) return;
        SmsMessage[] parts = Telephony.Sms.Intents.getMessagesFromIntent(intent);
        if (parts == null || parts.length == 0 || parts[0] == null) return;

        StringBuilder text = new StringBuilder();  // un long SMS arrive en plusieurs morceaux
        for (SmsMessage part : parts) {
            if (part != null && part.getDisplayMessageBody() != null) text.append(part.getDisplayMessageBody());
        }
        Store store = new Store(context);
        String operator = Filter.operator(parts[0].getDisplayOriginatingAddress(),
                store.senders("orange"), store.senders("moov"), store.senders("wave"));
        if (operator == null || store.token().isEmpty() || !Filter.isPayment(text.toString())) return;
        store.add(operator, text.toString(), System.currentTimeMillis());
        UploadJob.schedule(context);
    }
}
