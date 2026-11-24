package com.memoai.encaissement;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/** Écran unique : association du téléphone, autorisations, état de la connexion. */
public class MainActivity extends Activity {
    private static final String[] OPERATORS = {"orange", "moov", "wave"};
    private static final String[] LABELS = {"Orange Money", "Moov Money", "Wave"};

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final EditText[] senders = new EditText[3];
    private Store store;
    private TextView state;
    private EditText tokenField;

    private final Runnable refresh = new Runnable() {
        @Override
        public void run() {
            showState();
            handler.postDelayed(this, 3000);
        }
    };

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        store = new Store(this);
        buildScreen();
        if (saved == null) handleLink(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        handleLink(intent);
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.post(refresh);
        if (!store.token().isEmpty()) connect();
    }

    @Override
    protected void onPause() {
        super.onPause();
        handler.removeCallbacks(refresh);
    }

    // ------------------------------------------------------------ association

    /** Lien « Associer ce téléphone ». Toujours confirmé : un site ne doit pas pouvoir changer l'association. */
    private void handleLink(Intent intent) {
        Uri link = intent == null ? null : intent.getData();
        if (link == null || !"memoai-encaissement".equals(link.getScheme())) return;
        String token = link.getQueryParameter("jeton");
        if (token == null || token.length() < 20) return;
        new AlertDialog.Builder(this)
                .setTitle("Associer ce téléphone ?")
                .setMessage("Acceptez seulement si vous venez de toucher « Associer ce téléphone » dans votre espace administrateur MemoAI.")
                .setPositiveButton("Associer", (d, w) -> pair(token))
                .setNegativeButton("Annuler", null)
                .show();
    }

    private void pair(String token) {
        store.setToken(token.trim());
        tokenField.setText("");
        connect();
        requestSms();
    }

    private void connect() {
        UploadJob.schedulePeriodic(this);
        Context app = getApplicationContext();
        new Thread(() -> UploadJob.flush(app)).start();
    }

    // ------------------------------------------------------------ autorisations

    private boolean smsAllowed() {
        return checkSelfPermission(Manifest.permission.RECEIVE_SMS) == PackageManager.PERMISSION_GRANTED;
    }

    private boolean notificationsAllowed() {
        String enabled = Settings.Secure.getString(getContentResolver(), "enabled_notification_listeners");
        return enabled != null && enabled.contains(getPackageName() + "/");
    }

    private void requestSms() {
        if (!smsAllowed()) requestPermissions(new String[]{Manifest.permission.RECEIVE_SMS}, 1);
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(code, permissions, results);
        if (!smsAllowed() && !shouldShowRequestPermissionRationale(Manifest.permission.RECEIVE_SMS)) {
            new AlertDialog.Builder(this)
                    .setTitle("Autorisation bloquée par Android")
                    .setMessage("Dans la fiche de l'application : touchez ⋮ en haut à droite, puis « Autoriser les paramètres restreints ». Ouvrez ensuite « Autorisations » et acceptez les SMS.")
                    .setPositiveButton("Ouvrir la fiche", (d, w) -> startActivity(new Intent(
                            Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", getPackageName(), null))))
                    .setNegativeButton("Plus tard", null)
                    .show();
        }
    }

    // ------------------------------------------------------------ écran

    private void showState() {
        String status = store.status();
        state.setText((store.token().isEmpty() ? "⚪ Téléphone non associé" : "🟢 Téléphone associé")
                + "\n" + (smsAllowed() ? "🟢" : "🔴") + " Lecture des SMS Orange Money, Moov Money, Wave"
                + "\n" + (notificationsAllowed() ? "🟢" : "🔴") + " Lecture des notifications Wave"
                + "\nMessages en attente d'envoi : " + store.size()
                + (status.isEmpty() ? "" : "\n" + status));
    }

    private void buildScreen() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(20);
        page.setPadding(pad, pad, pad, pad);

        text(page, "MemoAI Encaissement", 22, true);
        text(page, "Installez cette application sur le téléphone qui reçoit l'argent. Seuls les messages « argent reçu » "
                + "d'Orange Money, Moov Money et Wave sont envoyés à MemoAI. Vos autres messages restent sur ce téléphone.", 14, false);
        state = text(page, "", 15, false);
        state.setBackgroundColor(Color.parseColor("#E6F2F0"));
        state.setPadding(dp(14), dp(14), dp(14), dp(14));

        text(page, "1. Associer le téléphone", 17, true);
        text(page, "Espace administrateur MemoAI → Téléphones d'encaissement → Associer un téléphone.", 14, false);
        tokenField = field(page, "Coller le code ici", "");
        button(page, "Associer", v -> {
            String token = tokenField.getText().toString().trim();
            if (token.length() < 20) tokenField.setError("Code incomplet");
            else pair(token);
        });

        text(page, "2. Autoriser la lecture", 17, true);
        button(page, "Autoriser les SMS", v -> requestSms());
        button(page, "Autoriser les notifications Wave", v ->
                startActivity(new Intent("android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS")));
        button(page, "Ne pas mettre en veille l'application", v ->
                startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)));

        text(page, "3. Noms des expéditeurs", 17, true);
        text(page, "Nom affiché en haut des SMS de chaque opérateur. Séparez plusieurs noms par une virgule.", 14, false);
        for (int i = 0; i < OPERATORS.length; i++) {
            text(page, LABELS[i], 14, true);
            senders[i] = field(page, "Expéditeur", store.senders(OPERATORS[i]));
        }
        button(page, "Enregistrer les noms", v -> {
            for (int i = 0; i < OPERATORS.length; i++) store.setSenders(OPERATORS[i], senders[i].getText().toString());
            ((Button) v).setText("Noms enregistrés ✓");
        });

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(Color.WHITE);
        scroll.addView(page);
        scroll.setOnApplyWindowInsetsListener((view, insets) -> {  // barres système (affichage bord à bord)
            view.setPadding(0, insets.getSystemWindowInsetTop(), 0, insets.getSystemWindowInsetBottom());
            return insets;
        });
        setContentView(scroll);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private TextView text(LinearLayout page, String value, int size, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(Color.parseColor("#1F2937"));
        if (bold) view.setTypeface(view.getTypeface(), android.graphics.Typeface.BOLD);
        add(page, view, bold ? 18 : 8);
        return view;
    }

    private EditText field(LinearLayout page, String hint, String value) {
        EditText view = new EditText(this);
        view.setHint(hint);
        view.setText(value);
        view.setSingleLine(true);
        view.setTextColor(Color.parseColor("#1F2937"));
        view.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        add(page, view, 6);
        return view;
    }

    private void button(LinearLayout page, String label, View.OnClickListener action) {
        Button view = new Button(this);
        view.setText(label);
        view.setAllCaps(false);
        view.setOnClickListener(action);
        add(page, view, 6);
    }

    private void add(LinearLayout page, View view, int top) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.topMargin = dp(top);
        page.addView(view, params);
    }
}
