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

## Modèles de mémoire payants

Six modèles (Licence, Master sciences & techniques, gestion, sciences sociales, droit, thèse de doctorat),
chacun avec sa page de garde (6 styles) et un plan commenté. Prix : 5 000 FCFA par modèle (`MODELE_PRICE`,
modifiable ensuite dans l'admin Django).

- Catalogue : `/modeles` (frontend) — API `/modeles/`.
- **Paiement par l'API de MemoAI** (`modeles/mobile_money.py`), active dès que `PAYMENT_NUMBER` est défini :
  le client envoie l'argent à ce numéro (Orange Money, Moov Money ou Wave), puis déclare son numéro et la référence.
  Numéro différent pour un opérateur : `PAYMENT_NUMBER_ORANGE`, `PAYMENT_NUMBER_MOOV`, `PAYMENT_NUMBER_WAVE`.
  `PAYMENT_HOLDER` (facultatif) : nom du bénéficiaire affiché au client. `PAYMENT_NOTIFY_EMAILS` (facultatif) :
  destinataires des alertes (par défaut, tous les administrateurs).
  - Confirmation automatique : application Android `android-encaissement/` sur le téléphone qui reçoit l'argent
    (`bash android-app/build.sh ../android-encaissement Encaissement`), associée depuis `/admin`. Opérateur, montant,
    référence, date et numéro doivent concorder ; une transaction ne paie qu'un seul achat.
  - Sinon, confirmation manuelle par un administrateur dans `/admin`.
- Sans `PAYMENT_NUMBER`, paiement par page hébergée Jɛmɛnipay (`JEMENI_PUBLIC_KEY`, `JEMENI_SECRET_KEY`, `JEMENI_TOKEN`). Le paiement n'est
  validé qu'après vérification côté serveur (état de la transaction et montant).
- Webhook (recommandé en production) : enregistrez `https://<votre-domaine>/modeles/webhook/jemeni/` pour
  `payment.success` / `payment.failed` et copiez le secret (affiché une seule fois) dans `JEMENI_WEBHOOK_SECRET`.
- Production : clés `pk_live_…` uniquement. Les clés `pk_test_…` (paiements simulés, numéro 98745632) ne fonctionnent
  qu'en développement (`JEMENI_ALLOW_SANDBOX`), et un achat simulé ne débloque jamais un modèle en production.
- Le catalogue se met à jour depuis `modeles/catalog.py` : `python manage.py sync_modeles`.
