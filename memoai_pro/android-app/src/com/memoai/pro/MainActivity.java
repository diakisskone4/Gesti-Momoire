package com.memoai.pro;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ContentValues;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;

/**
 * Application Android de MemoAI : l'application web (PWA) en plein écran, avec
 * - le bouton retour du téléphone qui revient à l'écran précédent ;
 * - le choix de fichiers / photos (insertion d'images dans les mémoires) ;
 * - l'enregistrement des mémoires exportés (Word, PDF, HTML) dans « Téléchargements / MemoAI » ;
 * - un écran « Pas de connexion » avec un bouton Réessayer.
 * Le contenu se met à jour automatiquement à chaque déploiement du site.
 */
public class MainActivity extends Activity {
    static final String HOST = "memoai-app-one.vercel.app";
    static final String HOME = "https://" + HOST + "/";
    private static final String OFFLINE_PAGE = "file:///android_asset/offline.html";
    private static final int FILE_REQUEST = 41;
    private static final int BRAND = Color.rgb(9, 47, 44);

    private WebView web;
    private FrameLayout root;
    private ValueCallback<Uri[]> fileCallback;
    private String lastUrl = HOME;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        root = new FrameLayout(this);
        root.setBackgroundColor(BRAND);
        web = new WebView(this);
        root.addView(web, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(root);
        applySystemBarInsets();

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setTextZoom(100);
        s.setSupportZoom(false);
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setUserAgentString(s.getUserAgentString() + " MemoAIAndroid/1.0");
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true);

        web.addJavascriptInterface(new Bridge(), "MemoAIAndroid");
        web.setWebViewClient(new Client());
        web.setWebChromeClient(new Chrome());
        web.setDownloadListener((url, userAgent, disposition, mimeType, length) -> openExternally(Uri.parse(url)));

        if (Build.VERSION.SDK_INT >= 33) {
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(0, this::goBack);
        }

        if (savedInstanceState != null) {
            web.restoreState(savedInstanceState);
        } else {
            web.loadUrl(startUrl(getIntent()));
        }
    }

    /** Lien https://memoai-app-one.vercel.app/... ouvert depuis un email, sinon l'accueil. */
    private String startUrl(Intent intent) {
        Uri data = intent == null ? null : intent.getData();
        if (data != null && "https".equals(data.getScheme()) && HOST.equals(data.getHost())) {
            return data.toString();
        }
        return HOME;
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        if (intent != null && intent.getData() != null) {
            web.loadUrl(startUrl(intent));
        }
    }

    /** Barres système (heure, batterie, navigation) : le contenu de l'application ne passe pas dessous. */
    @SuppressWarnings("deprecation")
    private void applySystemBarInsets() {
        // Affichage bord à bord sur toutes les versions : les marges sont gérées ci-dessous.
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
        } else {
            root.setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                controller.setSystemBarsAppearance(0, WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                        | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);
            }
        }
        root.setOnApplyWindowInsetsListener((View v, WindowInsets insets) -> {
            int top, bottom, left, right;
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars()
                        | WindowInsets.Type.displayCutout());
                android.graphics.Insets ime = insets.getInsets(WindowInsets.Type.ime());
                top = bars.top;
                left = bars.left;
                right = bars.right;
                bottom = Math.max(bars.bottom, ime.bottom);  // le clavier ne cache pas la zone de saisie
            } else {
                top = insets.getSystemWindowInsetTop();
                left = insets.getSystemWindowInsetLeft();
                right = insets.getSystemWindowInsetRight();
                bottom = insets.getSystemWindowInsetBottom();
            }
            v.setPadding(left, top, right, bottom);
            return insets;
        });
    }

    private void goBack() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            finish();
        }
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {  // Android 12 et antérieurs
        goBack();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        web.saveState(outState);
    }

    @Override
    protected void onPause() {
        super.onPause();
        CookieManager.getInstance().flush();
    }

    private void openExternally(Uri uri) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, uri));
        } catch (ActivityNotFoundException e) {
            Toast.makeText(this, "Aucune application ne peut ouvrir ce lien.", Toast.LENGTH_SHORT).show();
        }
    }

    // ------------------------------------------------------------------ navigation

    private class Client extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            String scheme = uri.getScheme() == null ? "" : uri.getScheme();
            if (scheme.equals("http") || scheme.equals("https")) {
                return false;  // reste dans l'application (y compris la page de paiement)
            }
            openExternally(uri);  // mailto:, tel:, whatsapp:, intent:...
            return true;
        }

        @Override
        public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
            if (url != null && url.startsWith("https://")) {
                lastUrl = url;
            }
        }

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
            if (request.isForMainFrame()) {
                view.loadUrl(OFFLINE_PAGE);
            }
        }
    }

    // ------------------------------------------------------------------ choix de fichiers (images)

    private class Chrome extends WebChromeClient {
        @Override
        public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
            if (fileCallback != null) {
                fileCallback.onReceiveValue(null);
            }
            fileCallback = callback;
            try {
                startActivityForResult(params.createIntent(), FILE_REQUEST);
            } catch (ActivityNotFoundException e) {
                fileCallback = null;
                return false;
            }
            return true;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_REQUEST && fileCallback != null) {
            fileCallback.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data));
            fileCallback = null;
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    // ------------------------------------------------------------------ pont JavaScript

    private class Bridge {
        /** Enregistre un mémoire exporté (base64) dans Téléchargements/MemoAI puis propose de l'ouvrir. */
        @JavascriptInterface
        public void saveFile(String base64, String filename, String mimeType) {
            runOnUiThread(() -> {
                String current = web.getUrl();
                if (current == null || !HOST.equals(Uri.parse(current).getHost())) {
                    return;  // seule l'application MemoAI peut enregistrer des fichiers
                }
                try {
                    byte[] bytes = Base64.decode(base64, Base64.DEFAULT);
                    Uri saved = write(safeName(filename), mimeType, bytes);
                    Toast.makeText(MainActivity.this, "Enregistré dans Téléchargements/MemoAI",
                            Toast.LENGTH_LONG).show();
                    if (saved != null) {
                        Intent open = new Intent(Intent.ACTION_VIEW);
                        open.setDataAndType(saved, mimeType);
                        open.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        try {
                            startActivity(Intent.createChooser(open, "Ouvrir le mémoire"));
                        } catch (ActivityNotFoundException ignored) {
                            // pas d'application pour ce type : le fichier reste dans Téléchargements
                        }
                    }
                } catch (Exception e) {
                    Toast.makeText(MainActivity.this, "Enregistrement impossible : " + e.getMessage(),
                            Toast.LENGTH_LONG).show();
                }
            });
        }

        /** Bouton « Réessayer » de l'écran hors connexion. */
        @JavascriptInterface
        public void retry() {
            runOnUiThread(() -> web.loadUrl(lastUrl));
        }
    }

    private static String safeName(String name) {
        String cleaned = name == null ? "" : name.replaceAll("[\\\\/:*?\"<>|]", "_").trim();
        return cleaned.isEmpty() ? "memoire" : cleaned;
    }

    private Uri write(String filename, String mimeType, byte[] bytes) throws Exception {
        if (Build.VERSION.SDK_INT >= 29) {
            ContentValues values = new ContentValues();
            values.put(MediaStore.MediaColumns.DISPLAY_NAME, filename);
            values.put(MediaStore.MediaColumns.MIME_TYPE, mimeType);
            values.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/MemoAI");
            Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
            if (uri == null) {
                throw new IllegalStateException("stockage indisponible");
            }
            try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                out.write(bytes);
            }
            return uri;
        }
        // Android 9 et antérieurs : dossier Téléchargements propre à l'application (sans permission).
        File dir = new File(getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "MemoAI");
        if (!dir.exists() && !dir.mkdirs()) {
            throw new IllegalStateException("dossier inaccessible");
        }
        try (FileOutputStream out = new FileOutputStream(new File(dir, filename))) {
            out.write(bytes);
        }
        return null;
    }
}
