import { Link } from 'react-router-dom';

import { STAFF_ROLES, loginPath, registerPath } from '../../lib/roles';
import AuthShell, { AuthTabs, SpaceLink, STAFF_FEATURES } from './AuthShell';

/** /pro et /pro/register : choix du profil pour l'espace enseignants & administration. */
export default function StaffPortalPage({ mode }: { mode: 'login' | 'register' }) {
  return (
    <AuthShell
      home="/pro"
      pill="Enseignants & administration"
      title="Accompagnez vos étudiants"
      highlight="jusqu'à la soutenance."
      text="Un espace dédié aux encadreurs, co-encadreurs, membres du jury et administrateurs de MemoAI Pro."
      features={STAFF_FEATURES}
      wide
    >
      <AuthTabs loginUrl="/pro" registerUrl="/pro/register" active={mode} />

      <span className="eyebrow">Espace enseignants & administration</span>
      <h2>{mode === 'login' ? 'Quel est votre profil ?' : 'Créer un compte professionnel'}</h2>
      <p className="sub">Choisissez votre rôle pour {mode === 'login' ? 'accéder à votre espace' : 'créer votre compte'}.</p>

      <div className="roles">
        {STAFF_ROLES.map(r => (
          <Link key={r.code} className="role-card" to={mode === 'login' ? loginPath(r) : registerPath(r)}>
            <span className="icon" aria-hidden="true">{r.icon}</span>
            <strong>{r.label} <span aria-hidden="true">→</span></strong>
            <small>{r.description}</small>
          </Link>
        ))}
      </div>

      <div className="divider">Vous êtes étudiant ?</div>
      <SpaceLink student to={mode === 'login' ? '/login' : '/register'}
                 subtitle={mode === 'login' ? 'Connectez-vous pour rédiger votre mémoire' : 'Créez votre compte étudiant gratuitement'} />
    </AuthShell>
  );
}
