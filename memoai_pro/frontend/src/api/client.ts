/**
 * Client HTTP de l'API Django.
 * - ajoute le jeton JWT à chaque requête ;
 * - en cas de 401, renouvelle le jeton une seule fois (requêtes simultanées
 *   partagent le même renouvellement) puis rejoue la requête ;
 * - si le renouvellement échoue, la session est terminée.
 */
export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

const ACCESS_KEY = 'memoai_access';
const REFRESH_KEY = 'memoai_refresh';
const PUBLIC_PATHS = ['/users/login/', '/users/register/', '/users/refresh/', '/users/password-reset/'];

function storageGet(key: string): string | null {
  try { return localStorage.getItem(key); } catch { return null; }
}
function storageSet(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch { /* stockage indisponible : session limitée à l'onglet */ }
}

export const tokens = {
  access: () => storageGet(ACCESS_KEY),
  refresh: () => storageGet(REFRESH_KEY),
  save(access: string, refresh?: string) {
    storageSet(ACCESS_KEY, access);
    if (refresh) storageSet(REFRESH_KEY, refresh);
  },
  clear() {
    storageSet(ACCESS_KEY, null);
    storageSet(REFRESH_KEY, null);
  },
};

export class ApiError extends Error {
  constructor(public status: number, public data: unknown, message: string) {
    super(message);
  }
}

let sessionExpiredHandler: () => void = () => undefined;
export function onSessionExpired(handler: () => void): void {
  sessionExpiredHandler = handler;
}

let refreshing: Promise<string> | null = null;

function refreshAccess(): Promise<string> {
  const refresh = tokens.refresh();
  if (!refresh) return Promise.reject(new ApiError(401, null, 'Aucune session à renouveler'));
  if (!refreshing) {
    refreshing = fetch(`${API_URL}/users/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
      .then(async res => {
        if (!res.ok) throw new ApiError(res.status, null, 'Session expirée');
        const data = (await res.json()) as { access: string; refresh?: string };
        tokens.save(data.access, data.refresh);
        return data.access;
      })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

type Params = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  params?: Params;
  /** Renvoie la Response brute (téléchargement de fichiers). */
  raw?: boolean;
}

function buildUrl(path: string, params?: Params): string {
  const url = new URL(API_URL + path);
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  });
  return url.toString();
}

async function parseBody(res: Response): Promise<unknown> {
  if (res.status === 204) return null;
  const type = res.headers.get('Content-Type') ?? '';
  if (type.includes('application/json')) return res.json();
  return res.text();
}

export async function request<T = unknown>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params, raw } = options;
  const isPublic = PUBLIC_PATHS.some(p => path.startsWith(p));

  const send = (token: string | null) => {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (token && !isPublic) headers.Authorization = `Bearer ${token}`;
    return fetch(buildUrl(path, params), {
      method, headers, body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  let res: Response;
  try {
    res = await send(tokens.access());
    if (res.status === 401 && !isPublic && tokens.refresh()) {
      let fresh: string;
      try {
        fresh = await refreshAccess();
      } catch (err) {
        tokens.clear();
        sessionExpiredHandler();
        throw err;
      }
      res = await send(fresh);
    }
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, null, 'Serveur injoignable. Vérifiez que le backend Django est démarré.');
  }

  if (!res.ok) {
    const data = await parseBody(res).catch(() => null);
    throw new ApiError(res.status, data, errorMessage(data, `Erreur ${res.status}`));
  }
  if (raw) return res as unknown as T;
  return (await parseBody(res)) as T;
}

const FIELD_LABELS: Record<string, string> = {
  email: 'Email', first_name: 'Prénom', last_name: 'Nom', password: 'Mot de passe', password2: 'Confirmation',
  university: 'Université', level: 'Niveau', academic_title: 'Grade', admin_code: 'Code administrateur',
  phone: 'Téléphone', title: 'Titre', theme: 'Thème', supervisor: 'Encadreur', co_supervisor: 'Co-encadreur',
  jury: 'Jury', comment: 'Commentaire', faculty: 'Faculté', department: 'Département',
  field_of_study: "Domaine d'étude", academic_year: 'Année académique', desired_pages: 'Pages souhaitées',
};

/** Transforme une réponse d'erreur DRF en phrase lisible. */
export function errorMessage(data: unknown, fallback = 'Une erreur est survenue.'): string {
  if (!data) return fallback;
  if (typeof data === 'string') return data.startsWith('<') ? fallback : data;
  if (typeof data === 'object') {
    const obj = data as Record<string, unknown>;
    if (typeof obj.error === 'string') return obj.error;
    if (typeof obj.detail === 'string') return obj.detail;
    const parts = Object.entries(obj).map(([key, value]) => {
      const msg = Array.isArray(value) ? value.join(' ') : typeof value === 'object' ? errorMessage(value, '') : String(value);
      const label = key === 'non_field_errors' ? '' : FIELD_LABELS[key] ?? key;
      return label ? `${label} : ${msg}` : msg;
    });
    return parts.filter(Boolean).join(' · ') || fallback;
  }
  return fallback;
}

/** Message d'une erreur quelconque (ApiError ou autre). */
export function describeError(err: unknown, fallback?: string): string {
  if (err instanceof ApiError) return err.status === 0 ? err.message : errorMessage(err.data, fallback ?? err.message);
  return fallback ?? 'Une erreur est survenue.';
}
