package com.memoai.encaissement;

import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.DateFormat;
import java.util.Date;

/** Envoie la file d'attente au serveur dès que le réseau est disponible, et signale la présence du téléphone. */
public class UploadJob extends JobService {
    private static final String ENDPOINT = "https://memoai-backend.vercel.app/modeles/paiement/messages/";
    private static final int JOB_NOW = 1, JOB_PERIODIC = 2, BATCH = 20;
    private static final Object SENDING = new Object();

    static void schedule(Context context) {
        JobScheduler jobs = (JobScheduler) context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        jobs.schedule(job(context, JOB_NOW).setBackoffCriteria(30_000, JobInfo.BACKOFF_POLICY_EXPONENTIAL).build());
    }

    static void schedulePeriodic(Context context) {
        JobScheduler jobs = (JobScheduler) context.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        if (jobs.getPendingJob(JOB_PERIODIC) == null) {
            jobs.schedule(job(context, JOB_PERIODIC).setPeriodic(15 * 60_000L).build());
        }
    }

    private static JobInfo.Builder job(Context context, int id) {
        return new JobInfo.Builder(id, new ComponentName(context, UploadJob.class))
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPersisted(true);
    }

    @Override
    public boolean onStartJob(JobParameters params) {
        new Thread(() -> {
            boolean retry = !flush(this);
            jobFinished(params, retry && params.getJobId() == JOB_NOW);
        }).start();
        return true;
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        return true;
    }

    /** Vrai si tout est envoyé, ou s'il est inutile de réessayer (téléphone non associé ou retiré). */
    static boolean flush(Context context) {
        synchronized (SENDING) {
            Store store = new Store(context);
            String token = store.token();
            if (token.isEmpty()) return true;
            while (true) {
                JSONArray batch = store.peek(BATCH);
                int code;
                try {
                    code = post(token, batch);
                } catch (Exception e) {
                    store.setStatus("Pas de connexion au serveur : nouvel essai automatique.");
                    return false;
                }
                if (code == 401) {
                    store.setStatus("Téléphone non autorisé : associez-le de nouveau depuis l'espace administrateur.");
                    return true;  // la file est conservée jusqu'à la prochaine association
                }
                if (code == 400) {  // lot refusé : le garder bloquerait tous les suivants
                    store.drop(batch);
                } else if (code != 200) {
                    store.setStatus("Le serveur a répondu " + code + " : nouvel essai automatique.");
                    return false;
                } else {
                    store.drop(batch);
                    store.setStatus("Connecté. Dernier échange : "
                            + DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(new Date()));
                }
                if (store.size() == 0) return true;
            }
        }
    }

    private static int post(String token, JSONArray messages) throws Exception {
        byte[] body = new JSONObject().put("messages", messages).toString().getBytes(StandardCharsets.UTF_8);
        HttpURLConnection connection = (HttpURLConnection) new URL(ENDPOINT).openConnection();
        try {
            connection.setConnectTimeout(20_000);
            connection.setReadTimeout(60_000);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setFixedLengthStreamingMode(body.length);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("X-Device-Token", token);
            try (OutputStream out = connection.getOutputStream()) {
                out.write(body);
            }
            return connection.getResponseCode();
        } finally {
            connection.disconnect();
        }
    }
}
