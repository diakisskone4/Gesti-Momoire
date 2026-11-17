import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import Logo from '../../components/Logo';
import type { RoleCode } from '../../lib/roles';
import '../../styles/auth.css';

interface SpaceCopy {
  pill: string;
  title: string;
  highlight: string;
  text: string;
  features: string[];
  quote?: string;
}

/**
 * Présentation de chaque espace. Chaque rôle a sa propre page de connexion et
 * d'inscription : aucune ne mentionne ni ne renvoie vers l'espace d'un autre rôle.
 */
export const SPACE_COPY: Record<RoleCode, SpaceCopy> = {
  STUDENT: {
    pill: 'Espace étudiant',
    title: 'Construisez un mémoire',
    highlight: 'plus intelligent.',
    text: "Organisez vos idées, rédigez vos chapitres et laissez l'IA vous aider, de la première idée jusqu'à la version finale.",
    features: [
      "Un plan complet généré par l'IA à partir de votre seul thème",
      'Éditeur, bibliographie et assistant IA réunis au même endroit',
      'Relecture et validation en ligne par votre encadreur',
      'Rédaction et sauvegarde gratuites, export final à la demande',
    ],
    quote: "Votre assistant académique, de la première idée jusqu'à la version finale.",
  },
  SUPERVISOR: {
    pill: 'Espace encadreur',
    title: 'Accompagnez vos étudiants',
    highlight: "jusqu'à la soutenance.",
    text: "Suivez l'avancement des mémoires que vous encadrez, relisez les chapitres et validez le travail de vos étudiants.",
    features: [
      'Tous les mémoires que vous encadrez au même endroit',
      'Lecture des chapitres et commentaires en ligne',
      'Validation ou demande de corrections en un clic',
      'Notification à chaque soumission de vos étudiants',
    ],
  },
  CO_SUPERVISOR: {
    pill: 'Espace co-encadreur',
    title: 'Co-encadrez en toute',
    highlight: 'simplicité.',
    text: "Suivez les mémoires qui vous sont confiés avec les mêmes outils que l'encadreur principal.",
    features: [
      'Les mémoires que vous co-encadrez au même endroit',
      'Lecture des chapitres et commentaires en ligne',
      "Avis et validation aux côtés de l'encadreur",
      'Notification à chaque soumission',
    ],
  },
  JURY: {
    pill: 'Espace jury',
    title: 'Évaluez les mémoires',
    highlight: 'en toute sérénité.',
    text: 'Consultez les mémoires finalisés qui vous sont soumis et rendez votre avis avant la soutenance.',
    features: [
      'Les mémoires à évaluer réunis au même endroit',
      'Lecture du document complet et de sa bibliographie',
      'Commentaires et décision en ligne',
      'Notification dès qu’un mémoire vous est attribué',
    ],
  },
  ADMIN: {
    pill: 'Administration',
    title: 'Pilotez la plateforme',
    highlight: 'MemoAI Pro.',
    text: "Gérez les comptes, les rôles et les modèles de mémoire, et suivez l'activité de la plateforme.",
    features: [
      'Gestion des utilisateurs et des rôles',
      'Suivi des mémoires et des paiements',
      'Catalogue des modèles de mémoire',
      "Statistiques d'activité",
    ],
  },
};

interface Props {
  role: RoleCode;
  /** Page vers laquelle renvoie le logo (la connexion du même espace). */
  home: string;
  wide?: boolean;
  /** Remplace le titre de présentation (ex. inscription étudiante). */
  title?: string;
  highlight?: string;
  quote?: string;
  children: ReactNode;
}

/** Cadre commun des pages de connexion / inscription : panneau visuel + zone formulaire. */
export default function AuthShell({ role, home, wide, title, highlight, quote, children }: Props) {
  const copy = SPACE_COPY[role];
  const shownQuote = quote ?? copy.quote;
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
              <span className="pill">✦ {copy.pill}</span>
              <h1>{title ?? copy.title}<br /><em>{highlight ?? copy.highlight}</em></h1>
              <p className="lead">{copy.text}</p>
              <ul className="features">
                {copy.features.map(f => (
                  <li key={f}><span className="check" aria-hidden="true">✓</span><span>{f}</span></li>
                ))}
              </ul>
            </div>
            {shownQuote && <figure className="quote"><blockquote>“{shownQuote}”</blockquote></figure>}
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

/** Rappel discret de l'espace courant (sans lien vers les autres espaces). */
export function SpaceBadge({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="role-chip">
      <span className="icon" aria-hidden="true">{icon}</span>
      <span><strong>{label}</strong><small>Espace réservé</small></span>
    </div>
  );
}
