# MemoAI Pro

Plateforme d'aide à la rédaction de mémoires : backend **Django REST** + frontend **React (Vite, TypeScript)**.

## Backend (Django)

```bash
cd memoai_pro
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver     # http://127.0.0.1:8000  (doc API : /swagger/)
```

La configuration est lue dans `.env` (jamais versionné) : `SECRET_KEY`, `DB_*`, `OPENAI_API_KEY`
(clé OpenRouter), `AI_MODEL`, `ADMIN_REGISTRATION_CODE`, `FRONTEND_URL`, `REDIS_URL`...

- `REDIS_URL` vide (développement) : les tâches Celery s'exécutent directement et les notifications
  temps réel passent en mémoire. En production, renseigner `REDIS_URL` et lancer un worker Celery.
- Tests : `python manage.py test`

## Frontend (React)

```bash
cd memoai_pro/frontend
npm install
npm run dev        # http://localhost:5173
npm test           # tests Vitest
npm run build      # build de production dans dist/
```

L'URL du backend se règle avec `VITE_API_URL` (voir `.env.example`, défaut `http://127.0.0.1:8000`).

## Espaces

| Rôle | Connexion | Accueil |
|---|---|---|
| Étudiant | `/login` | `/dashboard` |
| Encadreur / co-encadreur | `/pro/login/encadreur`, `/pro/login/co-encadreur` | `/supervision` |
| Jury | `/pro/login/jury` | `/jury` |
| Administrateur | `/pro/login/admin` (inscription avec `ADMIN_REGISTRATION_CODE`) | `/admin` |

## Modèles de mémoire payants (SasPay)

Six modèles (Licence, Master sciences & techniques, gestion, sciences sociales, droit, thèse de doctorat),
chacun avec sa page de garde (6 styles) et un plan commenté. Prix : 5 000 FCFA par modèle (`MODELE_PRICE`,
modifiable ensuite dans l'admin Django).

- Catalogue : `/modeles` (frontend) — API `/modeles/`.
- Paiement : checkout hébergé SasPay (`SASPAY_SECRET_KEY`, `SASPAY_API_URL`). Le paiement n'est validé
  qu'après vérification côté serveur (statut de session + transaction : statut, devise, montant).
- Webhook (optionnel, recommandé en production) : dans le tableau de bord SasPay, créez un webhook vers
  `https://<votre-domaine>/modeles/webhook/saspay/`, abonnez-le à `transaction.success` / `transaction.failed`
  et copiez le secret de signature dans `SASPAY_WEBHOOK_SECRET`.
- Sandbox : `SASPAY_API_URL=https://sandbox-api.saspay.me/api/v1` avec une clé `sk_test_...`.
- Le catalogue se met à jour depuis `modeles/catalog.py` : `python manage.py sync_modeles`.
