/**
 * Application installable (PWA) : enregistrement du service worker, installation
 * (Android / PC via beforeinstallprompt, iPhone / iPad via instructions Safari),
 * mises à jour et état hors ligne. Petit magasin observable, lu par usePwa().
 */
import { useSyncExternalStore } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export interface PwaState {
  /** Android / Chrome / Edge : l'installation native est possible. */
  canInstall: boolean;
  /** iPhone / iPad dans Safari : l'installation passe par « Sur l'écran d'accueil ». */
  iosInstallable: boolean;
  /** L'application tourne déjà en mode installé. */
  standalone: boolean;
  updateAvailable: boolean;
  offline: boolean;
}

const nav = typeof navigator !== 'undefined' ? navigator : undefined;
const isIOS = !!nav && (/iphone|ipad|ipod/i.test(nav.userAgent)
  // iPadOS se présente comme un Mac : on le reconnaît à l'écran tactile.
  || (nav.platform === 'MacIntel' && nav.maxTouchPoints > 1));

function detectStandalone(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia?.('(display-mode: standalone)').matches
    || (nav as Navigator & { standalone?: boolean } | undefined)?.standalone === true;
}

let deferredPrompt: BeforeInstallPromptEvent | null = null;
let waitingWorker: ServiceWorker | null = null;
let state: PwaState = {
  canInstall: false,
  iosInstallable: isIOS && !detectStandalone(),
  standalone: detectStandalone(),
  updateAvailable: false,
  offline: !!nav && nav.onLine === false,
};
const listeners = new Set<() => void>();

function setState(patch: Partial<PwaState>) {
  state = { ...state, ...patch };
  listeners.forEach(l => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function usePwa(): PwaState {
  return useSyncExternalStore(subscribe, () => state, () => state);
}

/** Ouvre la fenêtre d'installation native. Renvoie true si l'utilisateur accepte. */
export async function installApp(): Promise<boolean> {
  if (!deferredPrompt) return false;
  const prompt = deferredPrompt;
  deferredPrompt = null;
  setState({ canInstall: false });
  await prompt.prompt();
  const { outcome } = await prompt.userChoice;
  return outcome === 'accepted';
}

/** Active la nouvelle version : le service worker en attente prend la main, puis la page se recharge. */
export function applyUpdate(): void {
  if (waitingWorker) waitingWorker.postMessage('SKIP_WAITING');
  else window.location.reload();
}

function trackWaiting(registration: ServiceWorkerRegistration) {
  const markWaiting = (worker: ServiceWorker | null) => {
    // Une première installation n'est pas une mise à jour : seulement si une version contrôle déjà la page.
    if (worker && navigator.serviceWorker.controller) {
      waitingWorker = worker;
      setState({ updateAvailable: true });
    }
  };
  markWaiting(registration.waiting);
  registration.addEventListener('updatefound', () => {
    const installing = registration.installing;
    installing?.addEventListener('statechange', () => {
      if (installing.state === 'installed') markWaiting(installing);
    });
  });
}

export function initPwa(): void {
  if (typeof window === 'undefined') return;

  window.addEventListener('beforeinstallprompt', e => {
    e.preventDefault(); // on affiche notre propre bouton « Installer »
    deferredPrompt = e as BeforeInstallPromptEvent;
    setState({ canInstall: true });
  });
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    setState({ canInstall: false, iosInstallable: false, standalone: true });
  });
  window.addEventListener('online', () => setState({ offline: false }));
  window.addEventListener('offline', () => setState({ offline: true }));

  // En développement, pas de service worker : il interférerait avec le rechargement à chaud de Vite.
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return;

  let reloading = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloading || !waitingWorker) return;
    reloading = true;
    window.location.reload();
  });

  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' })
      .then(registration => {
        trackWaiting(registration);
        // Vérifie les nouvelles versions toutes les heures et au retour sur l'application.
        const check = () => registration.update().catch(() => undefined);
        setInterval(check, 60 * 60 * 1000);
        document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && check());
      })
      .catch(err => console.warn('Service worker non enregistré :', err));
  });
}
