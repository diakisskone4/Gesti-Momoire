import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import Logo from '../../components/Logo';
import '../../styles/auth.css';

export const STUDENT_FEATURES = [
  "Un plan complet généré par l'IA à partir de votre seul thème",
  'Éditeur, bibliographie et assistant IA réunis au même endroit',
  'Relecture et validation en ligne par votre encadreur',
  'Rédaction et sauvegarde gratuites, export final à la demande',
];

export const STAFF_FEATURES = [
  'Tous les mémoires que vous encadrez ou évaluez au même endroit',
  'Lecture des chapitres, commentaires et décision en un clic',
  'Notifications à chaque soumission de vos étudiants',
  'Administration des comptes et suivi de la plateforme',
];

interface Props {
  pill: string;
  title: string;
  highlight: string;
  text: string;
  features: string[];
  quote?: string;
  wide?: boolean;
  home: string;
  children: ReactNode;
}

/** Cadre commun des pages de connexion / inscription : panneau visuel + zone formulaire. */
export default function AuthShell({ pill, title, highlight, text, features, quote, wide, home, children }: Props) {
  return (
    <div className="scope-auth">
      <div className="auth-page">
        <aside className="visual">
          <div className="visual-inner">
            <Link className="brand" to={home}>
              <Logo size={38} className="brand-mark" />
              <span className="brand-name">MemoAI <b>Pro</b></span>
            </Link>
            <div className="visual-body">
              <span className="pill">✦ {pill}</span>
              <h1>{title}<br /><em>{highlight}</em></h1>
              <p className="lead">{text}</p>
              <ul className="features">
                {features.map(f => (
                  <li key={f}><span className="check" aria-hidden="true">✓</span><span>{f}</span></li>
                ))}
              </ul>
            </div>
            {quote && <figure className="quote"><blockquote>“{quote}”</blockquote></figure>}
          </div>
        </aside>

        <main className="form-side">
          <Link className="mobile-brand" to={home}>
            <Logo size={38} className="brand-mark" />
            <span className="brand-name">MemoAI <b>Pro</b></span>
          </Link>
          <div className={`form-box${wide ? ' wide' : ''}`}>{children}</div>
        </main>
      </div>
    </div>
  );
}

export function AuthTabs({ loginUrl, registerUrl, active }: { loginUrl: string; registerUrl: string; active: 'login' | 'register' }) {
  return (
    <nav className="tabs" aria-label="Connexion ou inscription">
      <Link to={loginUrl} className={active === 'login' ? 'active' : ''} aria-current={active === 'login' ? 'page' : undefined}>Connexion</Link>
      <Link to={registerUrl} className={active === 'register' ? 'active' : ''} aria-current={active === 'register' ? 'page' : undefined}>Inscription</Link>
    </nav>
  );
}

export function SpaceLink({ student, to, subtitle }: { student: boolean; to: string; subtitle: string }) {
  return (
    <Link className="space-link" to={to}>
      <span className="icon" aria-hidden="true">{student ? '🎓' : '🧑‍🏫'}</span>
      <span>
        <strong>{student ? 'Espace étudiant' : 'Espace enseignants & administration'}</strong>
        <small>{subtitle}</small>
      </span>
      <span className="go" aria-hidden="true">→</span>
    </Link>
  );
}
