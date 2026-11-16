import { useState } from 'react';
import { Download, RefreshCw, Share, SquarePlus, WifiOff, X } from 'lucide-react';

import { applyUpdate, installApp, usePwa } from './pwa';
import '../styles/pwa.css';

const DISMISS_KEY = 'memoai_install_dismissed';
const DISMISS_DAYS = 14;

function wasDismissedRecently(): boolean {
  try {
    const at = Number(localStorage.getItem(DISMISS_KEY));
    return !!at && Date.now() - at < DISMISS_DAYS * 86_400_000;
  } catch { return false; }
}

/** Instructions d'installation sur iPhone / iPad (Safari n'a pas de bouton « Installer »). */
export function IosInstallSheet({ onClose }: { onClose: () => void }) {
  return (
    <div className="pwa-sheet-overlay" onMouseDown={e => e.target === e.currentTarget && onClose()}>
      <div className="pwa-sheet" role="dialog" aria-modal="true" aria-labelledby="ios-install-title">
        <button type="button" className="pwa-icon-btn pwa-sheet-close" onClick={onClose} aria-label="Fermer"><X size={18} /></button>
        <img src="/icons/apple-touch-icon.png" alt="" width={56} height={56} className="pwa-sheet-logo" />
        <h2 id="ios-install-title">Installer MemoAI sur votre iPhone / iPad</h2>
        <ol className="pwa-steps">
          <li><span className="pwa-step-icon"><Share size={18} /></span>
            Dans Safari, touchez <strong>Partager</strong> (en bas de l'écran sur iPhone, en haut sur iPad).</li>
          <li><span className="pwa-step-icon"><SquarePlus size={18} /></span>
            Choisissez <strong>Sur l'écran d'accueil</strong>.</li>
          <li><span className="pwa-step-icon pwa-step-num">3</span>
            Touchez <strong>Ajouter</strong> : MemoAI s'ouvre ensuite comme une application.</li>
        </ol>
        <button type="button" className="btn-primary pwa-sheet-ok" onClick={onClose}>J'ai compris</button>
      </div>
    </div>
  );
}

/** Bouton « Installer l'application » (barre latérale, profil…). Invisible si l'installation est impossible. */
export function InstallButton({ className = '' }: { className?: string }) {
  const { canInstall, iosInstallable } = usePwa();
  const [showIos, setShowIos] = useState(false);
  if (!canInstall && !iosInstallable) return null;
  return (
    <>
      <button type="button" className={className}
              onClick={() => (canInstall ? void installApp() : setShowIos(true))}>
        <Download size={16} /> Installer l'application
      </button>
      {showIos && <IosInstallSheet onClose={() => setShowIos(false)} />}
    </>
  );
}

/** Bandeaux globaux : hors ligne, nouvelle version, proposition d'installation. */
export default function PwaPrompts() {
  const { canInstall, iosInstallable, updateAvailable, offline } = usePwa();
  const [dismissed, setDismissed] = useState(wasDismissedRecently);
  const [showIos, setShowIos] = useState(false);

  const dismiss = () => {
    setDismissed(true);
    try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch { /* ignore */ }
  };

  const showInstall = (canInstall || iosInstallable) && !dismissed && !updateAvailable;

  return (
    <>
      {offline && (
        <div className="pwa-offline" role="status">
          <WifiOff size={15} /> Vous êtes hors ligne — les modifications seront possibles au retour de la connexion.
        </div>
      )}

      {updateAvailable && (
        <div className="pwa-banner" role="status">
          <span className="pwa-banner-icon"><RefreshCw size={18} /></span>
          <div className="pwa-banner-text">
            <strong>Nouvelle version disponible</strong>
            <span>Mettez à jour pour profiter des dernières améliorations.</span>
          </div>
          <button type="button" className="btn-primary" onClick={applyUpdate}>Mettre à jour</button>
        </div>
      )}

      {showInstall && (
        <div className="pwa-banner" role="region" aria-label="Installer l'application">
          <img src="/icons/icon-96x96.png" alt="" width={40} height={40} className="pwa-banner-logo" />
          <div className="pwa-banner-text">
            <strong>Installez MemoAI</strong>
            <span>Accès direct depuis votre écran d'accueil, en plein écran, même hors ligne.</span>
          </div>
          <button type="button" className="btn-primary"
                  onClick={() => (canInstall ? void installApp() : setShowIos(true))}>
            Installer
          </button>
          <button type="button" className="pwa-icon-btn" onClick={dismiss} aria-label="Plus tard"><X size={18} /></button>
        </div>
      )}

      {showIos && <IosInstallSheet onClose={() => { setShowIos(false); dismiss(); }} />}
    </>
  );
}
